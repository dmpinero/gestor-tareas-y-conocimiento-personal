"""Concurrencia de los subestados: eliminar un subestado mientras se guardan tareas
con él no falla con una clave ajena rota (500); cada tarea queda sin subestado o con
uno que existe (sonda del verificador, ahora test de regresión)."""

import threading
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from gestor_tareas.aplicacion.subestado.casos_uso import CrearSubestado, EliminarSubestado
from gestor_tareas.aplicacion.tarea.actualizar_tarea import ActualizarTarea
from gestor_tareas.aplicacion.tarea.crear_tarea import CrearTarea
from gestor_tareas.dominio.excepciones import EntidadNoEncontradaError
from gestor_tareas.infraestructura.persistencia.repositorios.repositorio_grupos_estados_sqlalchemy import (  # noqa: E501
    RepositorioGruposEstadosSqlAlchemy,
)
from gestor_tareas.infraestructura.persistencia.repositorios.repositorio_tareas_sqlalchemy import (
    RepositorioTareasSqlAlchemy,
)
from gestor_tareas.infraestructura.persistencia.repositorios.repositorio_workflows_sqlalchemy import (  # noqa: E501
    RepositorioWorkflowsSqlAlchemy,
)
from gestor_tareas.infraestructura.persistencia.repositorios.repositorios_catalogos_sqlalchemy import (  # noqa: E501
    RepositorioEtiquetasSqlAlchemy,
    RepositorioPersonasSqlAlchemy,
    RepositorioSubestadosSqlAlchemy,
)
from gestor_tareas.infraestructura.persistencia.sesion import FabricaSesiones

_FECHA = datetime(2026, 11, 11, 9, 0, 0)
_RONDAS = 10


def _peticion(operacion: Callable[[Session], object]) -> Callable[[], object]:
    def ejecutar() -> object:
        sesion = FabricaSesiones()
        try:
            return operacion(sesion)
        finally:
            sesion.close()

    return ejecutar


def _crear(sesion: Session, subestado: str | None = None):
    return CrearTarea(
        RepositorioTareasSqlAlchemy(sesion),
        RepositorioEtiquetasSqlAlchemy(sesion),
        RepositorioPersonasSqlAlchemy(sesion),
        RepositorioWorkflowsSqlAlchemy(sesion),
        RepositorioGruposEstadosSqlAlchemy(sesion),
        repositorio_subestados=RepositorioSubestadosSqlAlchemy(sesion),
    ).ejecutar(nombre="T", descripcion="d", fecha_creacion=_FECHA, subestado=subestado)


def _editar(sesion: Session, id_tarea: int, subestado: str):
    return ActualizarTarea(
        RepositorioTareasSqlAlchemy(sesion),
        RepositorioEtiquetasSqlAlchemy(sesion),
        RepositorioPersonasSqlAlchemy(sesion),
        RepositorioGruposEstadosSqlAlchemy(sesion),
        RepositorioWorkflowsSqlAlchemy(sesion),
        repositorio_subestados=RepositorioSubestadosSqlAlchemy(sesion),
    ).ejecutar(id_tarea, nombre="T", descripcion="d", fecha_creacion=_FECHA, subestado=subestado)


def _a_la_vez(operaciones: list[Callable[[], object]]) -> list[object]:
    """Lanza las operaciones en paralelo; devuelve None si acaba bien o "404"."""
    barrera = threading.Barrier(len(operaciones))

    def tras_la_barrera(operacion: Callable[[], object]) -> object:
        barrera.wait()
        try:
            operacion()
            return None
        except EntidadNoEncontradaError:
            return "404"

    with ThreadPoolExecutor(max_workers=len(operaciones)) as ejecutor:
        futuros = [ejecutor.submit(tras_la_barrera, op) for op in operaciones]
        return [futuro.result() for futuro in futuros]


def _huerfanas() -> int:
    sesion = FabricaSesiones()
    try:
        return sesion.execute(
            text(
                "SELECT COUNT(*) FROM tareas t LEFT JOIN subestados s ON s.id = t.subestado_id "
                "WHERE t.subestado_id IS NOT NULL AND s.id IS NULL"
            )
        ).scalar_one()
    finally:
        sesion.close()


def _eliminar(id_subestado: int) -> Callable[[], object]:
    return _peticion(
        lambda s: EliminarSubestado(RepositorioSubestadosSqlAlchemy(s)).ejecutar(id_subestado)
    )


def _crear_subestado(nombre: str):
    return _peticion(
        lambda s: CrearSubestado(RepositorioSubestadosSqlAlchemy(s)).ejecutar(nombre)
    )()


@pytest.mark.usefixtures("sesion_bd")
@pytest.mark.parametrize("ronda", range(_RONDAS))
def test_eliminar_un_subestado_mientras_se_asigna_a_tareas_no_falla(ronda) -> None:
    tareas = [_peticion(_crear)().id for _ in range(4)]
    subestado = _crear_subestado("Bloqueado")

    resultados = _a_la_vez(
        [
            _eliminar(subestado.id),
            *[_peticion(lambda s, t=t: _editar(s, t, "Bloqueado")) for t in tareas],
        ]
    )

    assert set(resultados) <= {None, "404"}
    assert _huerfanas() == 0


@pytest.mark.usefixtures("sesion_bd")
@pytest.mark.parametrize("ronda", range(_RONDAS))
def test_eliminar_un_subestado_mientras_se_crean_tareas_con_el_no_falla(ronda) -> None:
    subestado = _crear_subestado("Bloqueado")

    resultados = _a_la_vez(
        [
            _eliminar(subestado.id),
            *[_peticion(lambda s: _crear(s, "Bloqueado")) for _ in range(4)],
        ]
    )

    assert set(resultados) <= {None, "404"}
    assert _huerfanas() == 0
