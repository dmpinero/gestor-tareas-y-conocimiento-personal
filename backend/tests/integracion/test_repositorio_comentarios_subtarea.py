"""Comentarios de las subtareas sobre MySQL."""

from datetime import UTC, datetime, timedelta, timezone

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from gestor_tareas.dominio.comentario.entidades import ComentarioSubtarea
from gestor_tareas.dominio.tarea.entidades import Subtarea, Tarea
from gestor_tareas.infraestructura.persistencia.modelos import ComentarioSubtareaModelo
from gestor_tareas.infraestructura.persistencia.repositorios.repositorio_comentarios_subtarea_sqlalchemy import (  # noqa: E501
    RepositorioComentariosSubtareaSqlAlchemy,
)
from gestor_tareas.infraestructura.persistencia.repositorios.repositorio_tareas_sqlalchemy import (
    RepositorioTareasSqlAlchemy,
)

_FECHA = datetime(2026, 11, 10, 9, 0, 0)
_CREADO = datetime(2026, 11, 10, 16, 30, 5, tzinfo=UTC)


def _tarea_con_subtareas(sesion, nombre: str, *subtareas: str) -> Tarea:
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
    m = ComentarioSubtareaModelo
    filas = sesion.execute(select(m.subtarea_id, m.texto, m.creado, m.editado).order_by(m.id))
    resultado = [tuple(f) for f in filas]
    sesion.rollback()
    return resultado


def _comentario(tarea: Tarea, indice: int, texto: str, creado=_CREADO) -> ComentarioSubtarea:
    return ComentarioSubtarea(
        id_tarea=tarea.id, id_subtarea=tarea.subtareas[indice].id, texto=texto, creado=creado
    )


@pytest.fixture
def repositorio(sesion_bd) -> RepositorioComentariosSubtareaSqlAlchemy:
    return RepositorioComentariosSubtareaSqlAlchemy(sesion_bd)


def test_crear_guarda_el_comentario_en_utc_sin_zona_y_lo_devuelve_con_id(
    sesion_bd, repositorio
) -> None:
    tarea = _tarea_con_subtareas(sesion_bd, "Mudanza", "Cajas")
    # Mismo instante en otra zona horaria: se guarda en UTC.
    creado = _CREADO.astimezone(timezone(timedelta(hours=2)))

    guardado = repositorio.crear(_comentario(tarea, 0, "Pedir\ncajas", creado))

    assert guardado.id is not None
    assert (guardado.id_tarea, guardado.id_subtarea) == (tarea.id, tarea.subtareas[0].id)
    assert (guardado.texto, guardado.creado, guardado.editado) == ("Pedir\ncajas", _CREADO, None)
    assert not sesion_bd.in_transaction()
    assert _filas(sesion_bd) == [
        (tarea.subtareas[0].id, "Pedir\ncajas", _CREADO.replace(tzinfo=None), None)
    ]


def test_crear_devuelve_none_si_la_tarea_no_tiene_la_subtarea(sesion_bd, repositorio) -> None:
    tarea = _tarea_con_subtareas(sesion_bd, "Mudanza", "Cajas")
    otra = _tarea_con_subtareas(sesion_bd, "Viaje", "Billetes")

    de_otra = ComentarioSubtarea(
        id_tarea=tarea.id, id_subtarea=otra.subtareas[0].id, texto="x", creado=_CREADO
    )
    inexistente = ComentarioSubtarea(
        id_tarea=tarea.id, id_subtarea=999_999, texto="x", creado=_CREADO
    )
    assert repositorio.crear(de_otra) is None
    assert repositorio.crear(inexistente) is None
    assert not sesion_bd.in_transaction()
    assert _filas(sesion_bd) == []


def test_listar_devuelve_los_de_la_subtarea_en_orden_cronologico(sesion_bd, repositorio) -> None:
    tarea = _tarea_con_subtareas(sesion_bd, "Mudanza", "Cajas", "Camión")
    repositorio.crear(_comentario(tarea, 0, "Tarde", _CREADO + timedelta(minutes=5)))
    repositorio.crear(_comentario(tarea, 0, "Pronto"))
    repositorio.crear(_comentario(tarea, 0, "Pronto también"))
    repositorio.crear(_comentario(tarea, 1, "De otra subtarea"))

    comentarios = repositorio.listar_de_subtarea(tarea.id, tarea.subtareas[0].id)

    assert [c.texto for c in comentarios] == ["Pronto", "Pronto también", "Tarde"]
    assert all(c.creado.tzinfo is UTC for c in comentarios)
    assert repositorio.listar_de_subtarea(tarea.id, 999_999) is None
    assert repositorio.listar_de_subtarea(999_999, tarea.subtareas[0].id) is None
    assert not sesion_bd.in_transaction()


def test_existe_tarea_y_existe_subtarea(sesion_bd, repositorio) -> None:
    tarea = _tarea_con_subtareas(sesion_bd, "Mudanza", "Cajas")
    otra = _tarea_con_subtareas(sesion_bd, "Viaje", "Billetes")

    assert repositorio.existe_tarea(tarea.id) is True
    assert repositorio.existe_tarea(999_999) is False
    assert repositorio.existe_subtarea(tarea.id, tarea.subtareas[0].id) is True
    assert repositorio.existe_subtarea(tarea.id, otra.subtareas[0].id) is False
    assert not sesion_bd.in_transaction()


def test_editar_cambia_el_texto_y_guarda_editado(sesion_bd, repositorio) -> None:
    tarea = _tarea_con_subtareas(sesion_bd, "Mudanza", "Cajas")
    guardado = repositorio.crear(_comentario(tarea, 0, "Uno"))
    otro = repositorio.crear(_comentario(tarea, 0, "Dos"))
    editado = _CREADO + timedelta(hours=1)

    resultado = repositorio.editar(tarea.id, tarea.subtareas[0].id, guardado.id, "Uno bis", editado)

    assert (resultado.id, resultado.texto, resultado.creado, resultado.editado) == (
        guardado.id,
        "Uno bis",
        _CREADO,
        editado,
    )
    assert not sesion_bd.in_transaction()
    id_subtarea = tarea.subtareas[0].id
    naive = _CREADO.replace(tzinfo=None)
    assert _filas(sesion_bd) == [
        (id_subtarea, "Uno bis", naive, editado.replace(tzinfo=None)),
        (id_subtarea, "Dos", naive, None),
    ]
    assert otro.editado is None


def test_editar_y_eliminar_devuelven_vacio_si_no_es_de_esa_subtarea(sesion_bd, repositorio) -> None:
    tarea = _tarea_con_subtareas(sesion_bd, "Mudanza", "Cajas", "Camión")
    otra = _tarea_con_subtareas(sesion_bd, "Viaje", "Billetes")
    de_camion = repositorio.crear(_comentario(tarea, 1, "Alquilar"))
    de_otra = repositorio.crear(_comentario(otra, 0, "Comprar"))
    antes = _filas(sesion_bd)
    cajas, billetes = tarea.subtareas[0].id, otra.subtareas[0].id

    casos = [
        (tarea.id, cajas, de_camion.id),  # Comentario de otra subtarea.
        (tarea.id, billetes, de_otra.id),  # Subtarea de otra tarea.
        (999_999, billetes, de_otra.id),  # Tarea que no existe.
        (tarea.id, cajas, 999_999),  # Comentario que no existe.
    ]
    for id_tarea, id_subtarea, id_comentario in casos:
        assert repositorio.editar(id_tarea, id_subtarea, id_comentario, "x", _CREADO) is None
        assert repositorio.eliminar(id_tarea, id_subtarea, id_comentario) is False
        assert not sesion_bd.in_transaction()

    assert _filas(sesion_bd) == antes


def test_eliminar_borra_solo_ese_comentario(sesion_bd, repositorio) -> None:
    tarea = _tarea_con_subtareas(sesion_bd, "Mudanza", "Cajas")
    uno = repositorio.crear(_comentario(tarea, 0, "Uno"))
    repositorio.crear(_comentario(tarea, 0, "Dos"))

    assert repositorio.eliminar(tarea.id, tarea.subtareas[0].id, uno.id) is True

    assert not sesion_bd.in_transaction()
    assert [f[1] for f in _filas(sesion_bd)] == ["Dos"]


def test_borrar_la_subtarea_borra_sus_comentarios(sesion_bd, repositorio) -> None:
    tarea = _tarea_con_subtareas(sesion_bd, "Mudanza", "Cajas", "Camión")
    repositorio.crear(_comentario(tarea, 0, "De cajas"))
    repositorio.crear(_comentario(tarea, 1, "De camión"))

    RepositorioTareasSqlAlchemy(sesion_bd).eliminar_subtarea(tarea.id, tarea.subtareas[0].id)

    assert [f[1] for f in _filas(sesion_bd)] == ["De camión"]


def test_la_base_de_datos_exige_que_la_subtarea_exista(sesion_bd) -> None:
    sesion_bd.add(ComentarioSubtareaModelo(subtarea_id=999_999, texto="x", creado=_FECHA))
    with pytest.raises(IntegrityError):
        sesion_bd.commit()
    sesion_bd.rollback()
