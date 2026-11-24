"""Foco de trabajo sobre MySQL: una sola fila (id = 1) que se sustituye al fijar otro
foco y desaparece al borrar la tarea o la subtarea en foco."""

from datetime import UTC, datetime

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.exc import DBAPIError

from gestor_tareas.dominio.excepciones import EntidadNoEncontradaError
from gestor_tareas.dominio.foco.entidades import Foco
from gestor_tareas.dominio.tarea.entidades import Subtarea, Tarea
from gestor_tareas.infraestructura.persistencia.modelos import FocoTrabajoModelo
from gestor_tareas.infraestructura.persistencia.repositorios.repositorio_foco_sqlalchemy import (
    RepositorioFocoSqlAlchemy,
)
from gestor_tareas.infraestructura.persistencia.repositorios.repositorio_tareas_sqlalchemy import (
    RepositorioTareasSqlAlchemy,
)

_FECHA = datetime(2026, 11, 10, 9, 0, 0)
_DESDE = datetime(2026, 11, 24, 10, 30, 15, tzinfo=UTC)


def _crear(sesion, nombre: str = "Migración portal", *subtareas: str) -> Tarea:
    return RepositorioTareasSqlAlchemy(sesion).crear(
        Tarea(
            nombre=nombre,
            descripcion="d",
            fecha_creacion=_FECHA,
            subtareas=[Subtarea(nombre=s) for s in subtareas],
        )
    )


def _filas(sesion) -> list[tuple]:
    sesion.rollback()  # Lectura nueva, sin la instantánea de una transacción anterior.
    return [tuple(f) for f in sesion.execute(text("SELECT * FROM foco_trabajo")).all()]


def test_sin_foco_obtener_devuelve_none(sesion_bd) -> None:
    assert RepositorioFocoSqlAlchemy(sesion_bd).obtener() is None


def test_fijar_guarda_una_fila_con_id_1_y_confirma(sesion_bd) -> None:
    tarea = _crear(sesion_bd, "Migración portal", "Copiar")
    subtarea = tarea.subtareas[0]

    foco = RepositorioFocoSqlAlchemy(sesion_bd).fijar(tarea.id, subtarea.id, _DESDE)

    assert foco == Foco(
        tarea_id=tarea.id,
        tarea_nombre="Migración portal",
        subtarea_id=subtarea.id,
        subtarea_nombre="Copiar",
        desde=_DESDE,
    )
    # Instante en UTC sin zona en la columna.
    assert _filas(sesion_bd) == [(1, tarea.id, subtarea.id, datetime(2026, 11, 24, 10, 30, 15))]
    assert RepositorioFocoSqlAlchemy(sesion_bd).obtener() == foco


def test_fijar_otro_foco_sustituye_la_fila(sesion_bd) -> None:
    primera = _crear(sesion_bd, "Primera")
    segunda = _crear(sesion_bd, "Segunda")
    repositorio = RepositorioFocoSqlAlchemy(sesion_bd)
    repositorio.fijar(primera.id, None, _DESDE)

    despues = datetime(2026, 11, 24, 11, 0, 0, tzinfo=UTC)
    foco = repositorio.fijar(segunda.id, None, despues)

    assert foco.tarea_id == segunda.id and foco.desde == despues
    assert _filas(sesion_bd) == [(1, segunda.id, None, datetime(2026, 11, 24, 11, 0, 0))]


def test_fijar_una_tarea_que_ya_no_existe_lanza_no_encontrada_sin_dejar_fila(sesion_bd) -> None:
    tarea = _crear(sesion_bd)
    RepositorioTareasSqlAlchemy(sesion_bd).eliminar(tarea.id)

    with pytest.raises(EntidadNoEncontradaError, match=f"^No existe la tarea con id {tarea.id}$"):
        RepositorioFocoSqlAlchemy(sesion_bd).fijar(tarea.id, None, _DESDE)

    assert _filas(sesion_bd) == []


def test_fijar_una_subtarea_que_ya_no_existe_lanza_no_encontrada_y_conserva_el_foco(
    sesion_bd,
) -> None:
    tarea = _crear(sesion_bd, "Migración portal", "Copiar")
    repositorio = RepositorioFocoSqlAlchemy(sesion_bd)
    repositorio.fijar(tarea.id, None, _DESDE)

    with pytest.raises(
        EntidadNoEncontradaError,
        match=f"^No existe la subtarea con id 999999 en la tarea con id {tarea.id}$",
    ):
        repositorio.fijar(tarea.id, 999999, _DESDE)

    assert _filas(sesion_bd) == [(1, tarea.id, None, datetime(2026, 11, 24, 10, 30, 15))]


def test_quitar_borra_la_fila_y_se_puede_repetir(sesion_bd) -> None:
    tarea = _crear(sesion_bd)
    repositorio = RepositorioFocoSqlAlchemy(sesion_bd)
    repositorio.fijar(tarea.id, None, _DESDE)

    repositorio.quitar(_DESDE)
    repositorio.quitar(_DESDE)

    assert _filas(sesion_bd) == []
    assert repositorio.obtener() is None


def test_la_base_de_datos_solo_admite_la_fila_con_id_1(sesion_bd) -> None:
    tarea = _crear(sesion_bd)

    # MySQL informa de la violación del CHECK como OperationalError (3819).
    with pytest.raises(DBAPIError, match="ck_foco_trabajo_una_fila"):
        sesion_bd.execute(
            text("INSERT INTO foco_trabajo (id, tarea_id, desde) VALUES (2, :t, NOW())"),
            {"t": tarea.id},
        )
    sesion_bd.rollback()
    assert sesion_bd.scalar(select(func.count()).select_from(FocoTrabajoModelo)) == 0


def _historial(sesion) -> list[tuple]:
    sesion.rollback()  # Lectura nueva, sin la instantánea de una transacción anterior.
    return [
        tuple(f)
        for f in sesion.execute(
            text(
                "SELECT tarea_id, subtarea_id, tarea_nombre, subtarea_nombre, desde, hasta "
                "FROM historial_foco ORDER BY id"
            )
        ).all()
    ]


_DESPUES = datetime(2026, 11, 24, 11, 0, 0, tzinfo=UTC)


def test_fijar_cierra_el_periodo_en_curso_y_abre_otro_en_la_misma_confirmacion(
    sesion_bd,
) -> None:
    tarea = _crear(sesion_bd, "Migración portal", "Copiar")
    repositorio = RepositorioFocoSqlAlchemy(sesion_bd)
    repositorio.fijar(tarea.id, None, _DESDE)

    repositorio.fijar(tarea.id, tarea.subtareas[0].id, _DESPUES)

    inicio, fin = datetime(2026, 11, 24, 10, 30, 15), datetime(2026, 11, 24, 11, 0, 0)
    assert _historial(sesion_bd) == [
        (tarea.id, None, "Migración portal", None, inicio, fin),
        (tarea.id, tarea.subtareas[0].id, "Migración portal", "Copiar", fin, None),
    ]


def test_un_fijar_que_falla_no_toca_el_historial(sesion_bd) -> None:
    tarea = _crear(sesion_bd)
    repositorio = RepositorioFocoSqlAlchemy(sesion_bd)
    repositorio.fijar(tarea.id, None, _DESDE)
    antes = _historial(sesion_bd)

    with pytest.raises(EntidadNoEncontradaError):
        repositorio.fijar(tarea.id, 999999, _DESPUES)

    assert _historial(sesion_bd) == antes


def test_quitar_cierra_el_periodo_en_curso(sesion_bd) -> None:
    tarea = _crear(sesion_bd)
    repositorio = RepositorioFocoSqlAlchemy(sesion_bd)
    repositorio.fijar(tarea.id, None, _DESDE)

    repositorio.quitar(_DESPUES)

    assert [f[-1] for f in _historial(sesion_bd)] == [datetime(2026, 11, 24, 11, 0, 0)]


def test_cerrar_el_periodo_de_una_tarea_no_confirma(sesion_bd) -> None:
    tarea = _crear(sesion_bd)
    repositorio = RepositorioFocoSqlAlchemy(sesion_bd)
    repositorio.fijar(tarea.id, None, _DESDE)

    repositorio.cerrar_periodo_de_tarea(tarea.id, _DESPUES)
    sesion_bd.rollback()

    assert [f[-1] for f in _historial(sesion_bd)] == [None]


def test_cerrar_el_periodo_de_otra_tarea_o_subtarea_no_cambia_nada(sesion_bd) -> None:
    tarea = _crear(sesion_bd, "Migración portal", "Copiar")
    repositorio = RepositorioFocoSqlAlchemy(sesion_bd)
    repositorio.fijar(tarea.id, tarea.subtareas[0].id, _DESDE)

    repositorio.cerrar_periodo_de_tarea(tarea.id + 1, _DESPUES)
    repositorio.cerrar_periodo_de_subtarea(tarea.id, tarea.subtareas[0].id + 1, _DESPUES)
    repositorio.cerrar_periodo_de_subtarea(tarea.id + 1, tarea.subtareas[0].id, _DESPUES)
    sesion_bd.commit()

    assert [f[-1] for f in _historial(sesion_bd)] == [None]


def test_listar_el_historial_lee_los_instantes_en_utc(sesion_bd) -> None:
    tarea = _crear(sesion_bd)
    repositorio = RepositorioFocoSqlAlchemy(sesion_bd)
    repositorio.fijar(tarea.id, None, _DESDE)
    repositorio.quitar(_DESPUES)

    (periodo,) = repositorio.listar_historial(None, None)

    assert (periodo.desde, periodo.hasta) == (_DESDE, _DESPUES)
    assert repositorio.listar_historial(_DESPUES, None) == []
    assert repositorio.listar_historial(None, _DESDE) == []
    assert repositorio.listar_historial(_DESDE, _DESPUES) == [periodo]
