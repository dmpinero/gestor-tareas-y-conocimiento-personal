"""Altas, bajas y reordenaciones simultáneas de los pasos del workflow.

Cada hilo simula una petición: su propia sesión y su propia transacción, con el
caso de uso y el repositorio reales sobre MySQL. Una barrera hace que todos
empiecen a la vez. Tras cada ronda, los números deben seguir siendo 1..n, sin
huecos ni repetidos, y ninguna operación puede fallar.
"""

import random
import threading
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor

import pytest
from sqlalchemy import select, text

from gestor_tareas.aplicacion.workflow_oportunidades.anadir_paso import AnadirPaso
from gestor_tareas.aplicacion.workflow_oportunidades.eliminar_paso import EliminarPaso
from gestor_tareas.aplicacion.workflow_oportunidades.listar_pasos import ListarPasos
from gestor_tareas.aplicacion.workflow_oportunidades.reordenar_pasos import ReordenarPasos
from gestor_tareas.dominio.excepciones import (
    ConflictoDeConcurrenciaError,
    EntidadNoEncontradaError,
    OrdenDePasosInvalidoError,
)
from gestor_tareas.infraestructura.persistencia.modelos import PasoWorkflowOportunidadModelo
from gestor_tareas.infraestructura.persistencia.repositorios.repositorio_workflow_oportunidades_sqlalchemy import (  # noqa: E501
    RepositorioWorkflowOportunidadesSqlAlchemy,
)
from gestor_tareas.infraestructura.persistencia.sesion import FabricaSesiones

_HILOS = 8
_RONDAS = 5


def _en_sesion_propia[T](operacion: Callable[[RepositorioWorkflowOportunidadesSqlAlchemy], T]) -> T:
    sesion = FabricaSesiones()
    try:
        return operacion(RepositorioWorkflowOportunidadesSqlAlchemy(sesion))
    finally:
        sesion.close()


def _anadir(nombre: str) -> object:
    return _en_sesion_propia(lambda r: AnadirPaso(r).ejecutar(nombre))


def _eliminar(id_paso: int) -> object:
    def eliminar(repositorio) -> object:
        try:
            EliminarPaso(repositorio).ejecutar(id_paso)
        except EntidadNoEncontradaError:
            return "ya eliminado"  # Otro hilo lo borró antes: es un 404 válido.
        return None

    return _en_sesion_propia(eliminar)


def _reordenar(semilla: int) -> object:
    """Lee el orden actual y lo envía barajado, como haría el drag & drop.

    Si entre la lectura y el envío otro hilo añadió o borró un paso, el orden ya
    no es una permutación exacta y la API lo rechaza (422): es válido.
    """

    def reordenar(repositorio) -> object:
        ids = [p.id for p in ListarPasos(repositorio).ejecutar()]
        random.Random(semilla).shuffle(ids)
        try:
            return ReordenarPasos(repositorio).ejecutar(ids)
        except OrdenDePasosInvalidoError:
            return "orden desfasado"

    return _en_sesion_propia(reordenar)


def _a_la_vez(operaciones: list[Callable[[], object]]) -> list[object]:
    """Lanza todas las operaciones en paralelo; si alguna falla, el test falla."""
    barrera = threading.Barrier(len(operaciones))

    def tras_la_barrera(operacion: Callable[[], object]) -> object:
        barrera.wait()
        return operacion()

    with ThreadPoolExecutor(max_workers=len(operaciones)) as ejecutor:
        futuros = [ejecutor.submit(tras_la_barrera, op) for op in operaciones]
        return [futuro.result() for futuro in futuros]


def _numeros_e_ids() -> tuple[list[int], list[int]]:
    sesion = FabricaSesiones()
    try:
        modelo = PasoWorkflowOportunidadModelo
        filas = sesion.execute(select(modelo.numero, modelo.id).order_by(modelo.numero)).all()
        return [f.numero for f in filas], [f.id for f in filas]
    finally:
        sesion.close()


def _comprobar_numeracion_contigua() -> list[int]:
    numeros, ids = _numeros_e_ids()
    assert numeros == list(range(1, len(numeros) + 1))
    assert len(set(ids)) == len(ids)
    return ids


@pytest.mark.usefixtures("sesion_bd")
def test_altas_simultaneas_sin_pasos_previos_numeran_de_1_a_n() -> None:
    _a_la_vez([lambda i=i: _anadir(f"Paso {i}") for i in range(_HILOS)])

    assert len(_comprobar_numeracion_contigua()) == _HILOS


@pytest.mark.usefixtures("sesion_bd")
@pytest.mark.parametrize("ronda", range(_RONDAS))
def test_altas_bajas_y_reordenaciones_simultaneas_mantienen_la_numeracion(ronda) -> None:
    for i in range(_HILOS):
        _anadir(f"Inicial {i}")
    ids = _comprobar_numeracion_contigua()
    a_eliminar = random.Random(ronda).sample(ids, 3)

    operaciones: list[Callable[[], object]] = [
        lambda: _anadir("Nuevo A"),
        lambda: _anadir("Nuevo B"),
        lambda: _anadir("Nuevo C"),
        *[lambda i=i: _eliminar(i) for i in a_eliminar],
        lambda: _eliminar(a_eliminar[0]),  # El mismo paso dos veces a la vez.
        lambda: _reordenar(ronda),
        lambda: _reordenar(ronda + 100),
        lambda: _reordenar(ronda + 200),
    ]
    resultados = _a_la_vez(operaciones)

    finales = _comprobar_numeracion_contigua()
    assert len(finales) == _HILOS + 3 - 3
    assert not set(a_eliminar) & set(finales)
    assert resultados.count("ya eliminado") == 1


@pytest.mark.usefixtures("sesion_bd")
def test_reordenaciones_simultaneas_completas_dejan_uno_de_los_ordenes_enviados() -> None:
    for i in range(_HILOS):
        _anadir(f"Paso {i}")
    ids = _comprobar_numeracion_contigua()
    ordenes = []
    for semilla in range(_HILOS):
        orden = list(ids)
        random.Random(semilla).shuffle(orden)
        ordenes.append(orden)

    _a_la_vez(
        [lambda o=o: _en_sesion_propia(lambda r: ReordenarPasos(r).ejecutar(o)) for o in ordenes]
    )

    assert _comprobar_numeracion_contigua() in ordenes


def test_si_el_bloqueo_del_workflow_no_llega_a_tiempo_es_un_conflicto_sin_cambios(
    sesion_bd, monkeypatch
) -> None:
    """Otra conexión retiene el bloqueo con nombre: el alta no espera indefinidamente,
    se traduce en conflicto (reintentable), no guarda nada y libera la sesión."""
    from gestor_tareas.infraestructura.persistencia.repositorios import (
        repositorio_workflow_oportunidades_sqlalchemy as modulo,
    )

    _anadir("Existente")
    monkeypatch.setattr(modulo, "_ESPERA_BLOQUEO_SEGUNDOS", 0)
    otra = FabricaSesiones()
    try:
        otra.execute(
            text("SELECT GET_LOCK(:nombre, 0)"), {"nombre": modulo.NOMBRE_BLOQUEO_WORKFLOW}
        )
        sesion = FabricaSesiones()
        try:
            repositorio = RepositorioWorkflowOportunidadesSqlAlchemy(sesion)
            with pytest.raises(ConflictoDeConcurrenciaError):
                repositorio.anadir_paso("Nuevo")
            assert not sesion.in_transaction()
        finally:
            sesion.close()
    finally:
        otra.execute(text("DO RELEASE_LOCK(:nombre)"), {"nombre": modulo.NOMBRE_BLOQUEO_WORKFLOW})
        otra.close()

    assert _numeros_e_ids()[0] == [1]
    # Liberado el bloqueo, el alta vuelve a funcionar.
    assert _anadir("Nuevo").numero == 2
