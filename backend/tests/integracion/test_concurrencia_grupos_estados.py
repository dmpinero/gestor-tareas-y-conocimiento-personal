"""Operaciones simultáneas sobre los grupos de estados y los estados de las tareas.

Cada hilo simula una petición: su propia sesión y su propia transacción, con los
casos de uso y los repositorios reales sobre MySQL. Una barrera hace que todos
empiecen a la vez. Solo se admiten las respuestas de dominio que una petición puede
recibir legítimamente si otra se le adelanta (404, 409 o 422); cualquier otra
excepción (un interbloqueo que agota los reintentos, una clave ajena violada...)
haría fallar el test. Tras cada ronda, las posiciones de los estados siguen siendo
1..n y toda tarea está sin grupo ni estado o en un estado de su grupo.
"""

import random
import threading
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from gestor_tareas.aplicacion.grupo_estados.casos_uso import (
    AnadirEstado,
    CrearGrupoEstados,
    EliminarEstado,
    EliminarGrupoEstados,
    ListarGruposEstados,
    RenombrarEstado,
    ReordenarEstados,
)
from gestor_tareas.aplicacion.tarea.actualizar_tarea import ActualizarTarea
from gestor_tareas.aplicacion.tarea.cambiar_estado import CambiarEstadoTarea
from gestor_tareas.aplicacion.tarea.crear_tarea import CrearTarea
from gestor_tareas.aplicacion.tarea.eliminar_tarea import EliminarTarea
from gestor_tareas.dominio.excepciones import (
    AsignacionDeEstadoInvalidaError,
    EntidadConDependenciasError,
    EntidadNoEncontradaError,
    NombreDuplicadoError,
    OrdenDeEstadosInvalidoError,
)
from gestor_tareas.dominio.grupo_estados.entidades import GrupoEstados
from gestor_tareas.infraestructura.persistencia.repositorios.repositorio_grupos_estados_sqlalchemy import (  # noqa: E501
    RepositorioGruposEstadosSqlAlchemy,
)
from gestor_tareas.infraestructura.persistencia.repositorios.repositorio_tareas_sqlalchemy import (
    RepositorioTareasSqlAlchemy,
)
from gestor_tareas.infraestructura.persistencia.repositorios.repositorio_workflow_oportunidades_sqlalchemy import (  # noqa: E501
    RepositorioWorkflowOportunidadesSqlAlchemy,
)
from gestor_tareas.infraestructura.persistencia.repositorios.repositorios_catalogos_sqlalchemy import (  # noqa: E501
    RepositorioEtiquetasSqlAlchemy,
    RepositorioPersonasSqlAlchemy,
)
from gestor_tareas.infraestructura.persistencia.sesion import FabricaSesiones

_RONDAS = 4
_FECHA = datetime(2026, 11, 11, 9, 0, 0)

# Lo que una petición puede recibir si otra simultánea se le adelanta.
_RESPUESTAS_ADMITIDAS = {
    EntidadNoEncontradaError: "404",
    NombreDuplicadoError: "409",
    EntidadConDependenciasError: "409",
    OrdenDeEstadosInvalidoError: "422",
    AsignacionDeEstadoInvalidaError: "422",
}


def _peticion(operacion: Callable[[Session], object]) -> Callable[[], object]:
    """Una petición: su propia sesión; los errores de dominio admitidos son su código."""

    def ejecutar() -> object:
        sesion = FabricaSesiones()
        try:
            return operacion(sesion)
        except tuple(_RESPUESTAS_ADMITIDAS) as error:
            return _RESPUESTAS_ADMITIDAS[type(error)]
        finally:
            sesion.close()

    return ejecutar


def _grupos(sesion: Session) -> RepositorioGruposEstadosSqlAlchemy:
    return RepositorioGruposEstadosSqlAlchemy(sesion)


def _a_la_vez(operaciones: list[Callable[[], object]]) -> list[object]:
    """Lanza todas las operaciones en paralelo; si alguna falla, el test falla."""
    barrera = threading.Barrier(len(operaciones))

    def tras_la_barrera(operacion: Callable[[], object]) -> object:
        barrera.wait()
        return operacion()

    with ThreadPoolExecutor(max_workers=len(operaciones)) as ejecutor:
        futuros = [ejecutor.submit(tras_la_barrera, op) for op in operaciones]
        return [futuro.result() for futuro in futuros]


def _filas(sql: str, **parametros) -> list[tuple]:
    sesion = FabricaSesiones()
    try:
        return [tuple(f) for f in sesion.execute(text(sql), parametros)]
    finally:
        sesion.close()


def _comprobar_invariantes() -> None:
    """Posiciones 1..n en cada grupo y cada tarea sin grupo o en un estado suyo."""
    por_grupo: dict[int, list[int]] = {}
    for grupo_id, posicion in _filas(
        "SELECT grupo_id, posicion FROM estados_grupo ORDER BY grupo_id, posicion"
    ):
        por_grupo.setdefault(grupo_id, []).append(posicion)
    for posiciones in por_grupo.values():
        assert posiciones == list(range(1, len(posiciones) + 1))
    incoherentes = _filas(
        "SELECT t.id FROM tareas t LEFT JOIN estados_grupo e ON e.id = t.estado_id "
        "WHERE (t.grupo_estados_id IS NULL) <> (t.estado_id IS NULL) "
        "OR (t.estado_id IS NOT NULL AND (e.id IS NULL OR e.grupo_id <> t.grupo_estados_id))"
    )
    assert incoherentes == []


def _crear_grupo(nombre: str, *estados: str) -> GrupoEstados:
    sesion = FabricaSesiones()
    try:
        grupo = CrearGrupoEstados(_grupos(sesion)).ejecutar(nombre)
        for estado in estados:
            grupo = AnadirEstado(_grupos(sesion)).ejecutar(grupo.id, estado)
        return grupo
    finally:
        sesion.close()


def _crear_tarea(sesion: Session, id_grupo: int | None) -> object:
    return CrearTarea(
        RepositorioTareasSqlAlchemy(sesion),
        RepositorioEtiquetasSqlAlchemy(sesion),
        RepositorioPersonasSqlAlchemy(sesion),
        RepositorioWorkflowOportunidadesSqlAlchemy(sesion),
        _grupos(sesion),
    ).ejecutar(nombre="T", descripcion="d", fecha_creacion=_FECHA, grupo_estados_id=id_grupo)


def _editar_tarea(sesion: Session, id_tarea: int, id_grupo: int | None) -> object:
    return ActualizarTarea(
        RepositorioTareasSqlAlchemy(sesion),
        RepositorioEtiquetasSqlAlchemy(sesion),
        RepositorioPersonasSqlAlchemy(sesion),
        _grupos(sesion),
    ).ejecutar(
        id_tarea, nombre="T", descripcion="d", fecha_creacion=_FECHA, grupo_estados_id=id_grupo
    )


def _mover(sesion: Session, id_tarea: int, id_estado: int) -> object:
    return CambiarEstadoTarea(RepositorioTareasSqlAlchemy(sesion), _grupos(sesion)).ejecutar(
        id_tarea, id_estado
    )


def _reordenar_barajado(semilla: int, id_grupo: int) -> Callable[[Session], object]:
    """Lee el orden actual y lo envía barajado, como haría el drag & drop."""

    def reordenar(sesion: Session) -> object:
        grupo = next(
            (g for g in ListarGruposEstados(_grupos(sesion)).ejecutar() if g.id == id_grupo), None
        )
        ids = [e.id for e in grupo.estados] if grupo else []
        random.Random(semilla).shuffle(ids)
        return ReordenarEstados(_grupos(sesion)).ejecutar(id_grupo, ids)

    return reordenar


@pytest.mark.usefixtures("sesion_bd")
def test_altas_simultaneas_de_estados_en_un_grupo_vacio_numeran_de_1_a_n() -> None:
    grupo = _crear_grupo("Vacío")

    resultados = _a_la_vez(
        [
            _peticion(lambda s, i=i: AnadirEstado(_grupos(s)).ejecutar(grupo.id, f"E{i}"))
            for i in range(8)
        ]
    )

    assert all(isinstance(r, GrupoEstados) for r in resultados)
    assert [p for (p,) in _filas("SELECT posicion FROM estados_grupo ORDER BY posicion")] == list(
        range(1, 9)
    )


@pytest.mark.usefixtures("sesion_bd")
def test_altas_simultaneas_del_mismo_nombre_guardan_uno_y_el_resto_es_409() -> None:
    grupo = _crear_grupo("G", "A")

    resultados = _a_la_vez(
        [_peticion(lambda s: AnadirEstado(_grupos(s)).ejecutar(grupo.id, "Repetido"))] * 6
        + [
            _peticion(lambda s, i=i: CrearGrupoEstados(_grupos(s)).ejecutar("Otro"))
            for i in range(4)
        ]
    )

    assert resultados.count("409") == 5 + 3
    assert _filas("SELECT COUNT(*) FROM estados_grupo WHERE nombre = 'Repetido'") == [(1,)]
    assert _filas("SELECT COUNT(*) FROM grupos_estados WHERE nombre = 'Otro'") == [(1,)]
    _comprobar_invariantes()


@pytest.mark.usefixtures("sesion_bd")
@pytest.mark.parametrize("ronda", range(_RONDAS))
def test_altas_bajas_cambios_de_nombre_y_reordenaciones_mantienen_las_posiciones(ronda) -> None:
    grupo = _crear_grupo("G", *(f"Inicial {i}" for i in range(6)))
    ids = [e.id for e in grupo.estados]
    a_eliminar = random.Random(ronda).sample(ids, 2)
    a_renombrar = next(i for i in ids if i not in a_eliminar)

    resultados = _a_la_vez(
        [
            *[
                _peticion(lambda s, i=i: AnadirEstado(_grupos(s)).ejecutar(grupo.id, f"Nuevo {i}"))
                for i in range(3)
            ],
            *[
                _peticion(lambda s, i=i: EliminarEstado(_grupos(s)).ejecutar(grupo.id, i, None))
                for i in a_eliminar
            ],
            # El mismo estado dos veces a la vez: una de las dos es un 404.
            _peticion(lambda s: EliminarEstado(_grupos(s)).ejecutar(grupo.id, a_eliminar[0], None)),
            _peticion(
                lambda s: RenombrarEstado(_grupos(s)).ejecutar(grupo.id, a_renombrar, "Renombrado")
            ),
            *[_peticion(_reordenar_barajado(ronda * 10 + i, grupo.id)) for i in range(3)],
        ]
    )

    assert resultados.count("404") == 1
    assert all(isinstance(r, GrupoEstados) or r in ("404", "422") for r in resultados)
    finales = _filas("SELECT id, nombre FROM estados_grupo ORDER BY posicion")
    assert len(finales) == 6 + 3 - 2
    assert not {i for i, _ in finales} & set(a_eliminar)
    assert (a_renombrar, "Renombrado") in finales
    _comprobar_invariantes()


@pytest.mark.usefixtures("sesion_bd")
@pytest.mark.parametrize("ronda", range(_RONDAS))
def test_mover_tareas_mientras_se_elimina_su_estado_no_deja_tareas_en_un_estado_borrado(
    ronda,
) -> None:
    grupo = _crear_grupo("Desarrollo", "Pendiente", "En curso", "Revisión", "Hecha")
    pendiente, en_curso, revision, hecha = (e.id for e in grupo.estados)
    tareas = [
        _peticion(lambda s: _crear_tarea(s, grupo.id))().id  # en "Pendiente"
        for _ in range(6)
    ]
    azar = random.Random(ronda)
    destinos = [azar.choice([en_curso, revision, hecha, pendiente]) for _ in tareas]

    resultados = _a_la_vez(
        [
            # Tareas que se mueven (también al estado que se elimina).
            *[
                _peticion(lambda s, t=t, d=d: _mover(s, t, d))
                for t, d in zip(tareas, destinos, strict=True)
            ],
            # Se elimina "Revisión" moviendo sus tareas a "Hecha" y "Pendiente" sin destino.
            _peticion(lambda s: EliminarEstado(_grupos(s)).ejecutar(grupo.id, revision, hecha)),
            _peticion(lambda s: EliminarEstado(_grupos(s)).ejecutar(grupo.id, pendiente, None)),
            # Altas, ediciones y borrados de tareas del grupo a la vez.
            _peticion(lambda s: _crear_tarea(s, grupo.id)),
            _peticion(lambda s: _editar_tarea(s, tareas[0], grupo.id)),
            _peticion(lambda s: _editar_tarea(s, tareas[1], None)),
            _peticion(lambda s: EliminarTarea(RepositorioTareasSqlAlchemy(s)).ejecutar(tareas[2])),
            _peticion(_reordenar_barajado(ronda, grupo.id)),
        ]
    )

    assert set(r for r in resultados if isinstance(r, str)) <= {"404", "409", "422"}
    # "Revisión" se elimina siempre: su destino es válido.
    assert _filas("SELECT id FROM estados_grupo WHERE id = :e", e=revision) == []
    assert _filas("SELECT COUNT(*) FROM tareas WHERE estado_id = :e", e=revision) == [(0,)]
    # "Pendiente" solo se elimina si no tenía tareas en ese momento (si no, 409).
    sigue_pendiente = _filas("SELECT id FROM estados_grupo WHERE id = :e", e=pendiente) != []
    assert sigue_pendiente == (resultados[7] == "409")
    _comprobar_invariantes()


@pytest.mark.usefixtures("sesion_bd")
@pytest.mark.parametrize("ronda", range(_RONDAS))
def test_eliminar_un_grupo_mientras_se_asigna_a_tareas_las_deja_coherentes(ronda) -> None:
    grupo = _crear_grupo("Desarrollo", "Pendiente", "Hecha")
    otro = _crear_grupo("Ventas", "Nueva", "Ganada")
    del_grupo = [_peticion(lambda s: _crear_tarea(s, grupo.id))().id for _ in range(4)]
    sin_grupo = [_peticion(lambda s: _crear_tarea(s, None))().id for _ in range(3)]
    hecha = grupo.estados[1].id
    azar = random.Random(ronda)
    nuevos_grupos = [azar.choice([grupo.id, otro.id]) for _ in sin_grupo]

    resultados = _a_la_vez(
        [
            _peticion(lambda s: EliminarGrupoEstados(_grupos(s)).ejecutar(grupo.id)),
            *[_peticion(lambda s, t=t: _mover(s, t, hecha)) for t in del_grupo[:2]],
            _peticion(lambda s: _editar_tarea(s, del_grupo[2], otro.id)),
            _peticion(lambda s: _editar_tarea(s, del_grupo[3], grupo.id)),
            *[
                _peticion(lambda s, t=t, g=g: _editar_tarea(s, t, g))
                for t, g in zip(sin_grupo, nuevos_grupos, strict=True)
            ],
            _peticion(lambda s: _crear_tarea(s, grupo.id)),
            _peticion(lambda s: AnadirEstado(_grupos(s)).ejecutar(grupo.id, "Nuevo")),
            _peticion(lambda s: EliminarEstado(_grupos(s)).ejecutar(grupo.id, hecha, None)),
        ]
    )

    assert resultados[0] is None  # El grupo se elimina siempre.
    assert set(r for r in resultados if isinstance(r, str)) <= {"404", "409", "422"}
    assert _filas("SELECT COUNT(*) FROM grupos_estados WHERE id = :g", g=grupo.id) == [(0,)]
    assert _filas("SELECT COUNT(*) FROM tareas WHERE grupo_estados_id = :g", g=grupo.id) == [(0,)]
    assert _filas("SELECT COUNT(*) FROM estados_grupo WHERE grupo_id = :g", g=grupo.id) == [(0,)]
    _comprobar_invariantes()
