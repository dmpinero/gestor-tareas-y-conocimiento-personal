"""Edición y borrado de subtareas y comentarios sobre MySQL."""

from datetime import UTC, datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from gestor_tareas.dominio.comentario.entidades import Comentario
from gestor_tareas.dominio.tarea.entidades import Subtarea, Tarea
from gestor_tareas.infraestructura.persistencia.modelos import (
    ComentarioModelo,
    PersonaModelo,
    SubtareaModelo,
)
from gestor_tareas.infraestructura.persistencia.repositorios.repositorio_comentarios_sqlalchemy import (  # noqa: E501
    RepositorioComentariosSqlAlchemy,
)
from gestor_tareas.infraestructura.persistencia.repositorios.repositorio_tareas_sqlalchemy import (
    RepositorioTareasSqlAlchemy,
)
from gestor_tareas.infraestructura.persistencia.repositorios.repositorios_catalogos_sqlalchemy import (  # noqa: E501
    RepositorioPersonasSqlAlchemy,
)

_FECHA = datetime(2026, 11, 10, 9, 0, 0)
_ALTA = datetime(2026, 11, 10, 8, 0, 0, tzinfo=UTC)


def _tarea(nombre: str = "Mudanza") -> Tarea:
    return Tarea(nombre=nombre, descripcion="d", fecha_creacion=_FECHA)


def _filas_subtareas(sesion, id_tarea: int) -> list[tuple]:
    sesion.rollback()  # Lectura nueva, sin la instantánea de una transacción anterior.
    m = SubtareaModelo
    filas = sesion.execute(
        select(m.id, m.nombre, m.persona_id, m.prioridad, m.resuelta)
        .where(m.tarea_id == id_tarea)
        .order_by(m.id)
    ).all()
    return [tuple(f) for f in filas]


def _filas_comentarios(sesion, id_tarea: int) -> list[tuple]:
    sesion.rollback()
    m = ComentarioModelo
    filas = sesion.execute(
        select(m.id, m.texto, m.creado, m.editado).where(m.tarea_id == id_tarea).order_by(m.id)
    ).all()
    return [tuple(f) for f in filas]


def _personas(sesion) -> list[str]:
    sesion.rollback()
    return list(sesion.scalars(select(PersonaModelo.nombre).order_by(PersonaModelo.id)))


def test_editar_subtarea_sustituye_sus_datos_y_conserva_el_estado(sesion_bd) -> None:
    repositorio = RepositorioTareasSqlAlchemy(sesion_bd)
    ana, luis = RepositorioPersonasSqlAlchemy(sesion_bd).obtener_o_crear(["Ana", "Luis"])
    id_tarea = repositorio.crear(_tarea()).id
    repositorio.anadir_subtarea(id_tarea, Subtarea(nombre="Embalar", asignado="Ana", prioridad=2))
    ids = [
        s.id for s in repositorio.anadir_subtarea(id_tarea, Subtarea(nombre="Limpiar")).subtareas
    ]
    repositorio.cambiar_resuelta_subtarea(id_tarea, ids[0], True)
    RepositorioPersonasSqlAlchemy(sesion_bd).obtener_o_crear(["Luis"])

    tarea = repositorio.editar_subtarea(
        id_tarea,
        # Se ignora ``resuelta``: el estado solo lo cambia ``cambiar_resuelta_subtarea``.
        Subtarea(id=ids[0], nombre="Embalar libros", asignado="Luis", prioridad=5, resuelta=False),
    )

    assert [(s.id, s.nombre, s.asignado, s.prioridad, s.resuelta) for s in tarea.subtareas] == [
        (ids[0], "Embalar libros", "Luis", 5, True),
        (ids[1], "Limpiar", None, None, False),
    ]
    assert _filas_subtareas(sesion_bd, id_tarea) == [
        (ids[0], "Embalar libros", luis.id, 5, True),
        (ids[1], "Limpiar", None, None, False),
    ]
    assert repositorio.obtener_por_id(id_tarea).subtareas == tarea.subtareas
    assert _personas(sesion_bd) == ["Ana", "Luis"]
    assert ana.id != luis.id


def test_editar_subtarea_sin_persona_ni_prioridad_las_vacia(sesion_bd) -> None:
    repositorio = RepositorioTareasSqlAlchemy(sesion_bd)
    RepositorioPersonasSqlAlchemy(sesion_bd).obtener_o_crear(["Ana"])
    id_tarea = repositorio.crear(_tarea()).id
    id_sub = (
        repositorio.anadir_subtarea(
            id_tarea, Subtarea(nombre="Embalar", asignado="Ana", prioridad=2)
        )
        .subtareas[0]
        .id
    )

    tarea = repositorio.editar_subtarea(id_tarea, Subtarea(id=id_sub, nombre="Embalar"))

    assert tarea.subtareas == [Subtarea(id=id_sub, nombre="Embalar")]
    assert _filas_subtareas(sesion_bd, id_tarea) == [(id_sub, "Embalar", None, None, False)]
    # La persona sigue en el catálogo aunque ya no esté asignada.
    assert _personas(sesion_bd) == ["Ana"]


def test_editar_subtarea_ajena_o_inexistente_devuelve_none_y_deshace_el_alta_de_la_persona(
    sesion_bd,
) -> None:
    repositorio = RepositorioTareasSqlAlchemy(sesion_bd)
    id_tarea = repositorio.crear(_tarea()).id
    otra = repositorio.crear(_tarea("Viaje")).id
    ajena = repositorio.anadir_subtarea(otra, Subtarea(nombre="Reservar")).subtareas[0].id

    for i, s in [(id_tarea, ajena), (id_tarea, 999_999), (999_999, ajena)]:
        RepositorioPersonasSqlAlchemy(sesion_bd).obtener_o_crear(["Luis"])
        resultado = repositorio.editar_subtarea(i, Subtarea(id=s, nombre="X", asignado="Luis"))
        assert resultado is None
        assert not sesion_bd.in_transaction()

    assert _filas_subtareas(sesion_bd, otra) == [(ajena, "Reservar", None, None, False)]
    assert _filas_subtareas(sesion_bd, id_tarea) == []
    assert _personas(sesion_bd) == []


def _con_comentario(sesion_bd) -> tuple[RepositorioComentariosSqlAlchemy, int, int]:
    id_tarea = RepositorioTareasSqlAlchemy(sesion_bd).crear(_tarea()).id
    repositorio = RepositorioComentariosSqlAlchemy(sesion_bd)
    comentario = repositorio.crear(Comentario(id_tarea=id_tarea, texto="Llamar", creado=_ALTA))
    return repositorio, id_tarea, comentario.id


def test_un_comentario_nuevo_no_esta_editado(sesion_bd) -> None:
    repositorio, id_tarea, id_comentario = _con_comentario(sesion_bd)

    assert repositorio.listar_de_tarea(id_tarea)[0].editado is None
    assert _filas_comentarios(sesion_bd, id_tarea) == [
        (id_comentario, "Llamar", datetime(2026, 11, 10, 8, 0, 0), None)
    ]


def test_editar_comentario_cambia_el_texto_y_guarda_editado_en_utc(sesion_bd) -> None:
    repositorio, id_tarea, id_comentario = _con_comentario(sesion_bd)
    madrid = timezone(timedelta(hours=1))

    comentario = repositorio.editar(
        id_tarea, id_comentario, "Uno\nDos", datetime(2026, 11, 10, 17, 30, 5, tzinfo=madrid)
    )

    assert comentario == Comentario(
        id=id_comentario,
        id_tarea=id_tarea,
        texto="Uno\nDos",
        creado=_ALTA,
        editado=datetime(2026, 11, 10, 16, 30, 5, tzinfo=UTC),
    )
    assert comentario.editado.utcoffset() == timedelta(0)
    assert not sesion_bd.in_transaction()
    assert _filas_comentarios(sesion_bd, id_tarea) == [
        (
            id_comentario,
            "Uno\nDos",
            datetime(2026, 11, 10, 8, 0, 0),
            datetime(2026, 11, 10, 16, 30, 5),
        )
    ]
    assert repositorio.listar_de_tarea(id_tarea) == [comentario]


def test_eliminar_comentario_lo_borra(sesion_bd) -> None:
    repositorio, id_tarea, id_comentario = _con_comentario(sesion_bd)
    otro = repositorio.crear(Comentario(id_tarea=id_tarea, texto="Otro", creado=_ALTA))

    assert repositorio.eliminar(id_tarea, id_comentario) is True

    assert not sesion_bd.in_transaction()
    assert _filas_comentarios(sesion_bd, id_tarea) == [
        (otro.id, "Otro", datetime(2026, 11, 10, 8, 0, 0), None)
    ]


@pytest.mark.parametrize("operacion", ["editar", "eliminar"])
def test_operar_sobre_un_comentario_ajeno_o_inexistente_no_cambia_nada(
    sesion_bd, operacion
) -> None:
    repositorio, id_tarea, id_comentario = _con_comentario(sesion_bd)
    otra = RepositorioTareasSqlAlchemy(sesion_bd).crear(_tarea("Viaje")).id
    antes = _filas_comentarios(sesion_bd, id_tarea)

    def operar(i: int, c: int):
        if operacion == "editar":
            return repositorio.editar(i, c, "Otro", datetime.now(UTC))
        return repositorio.eliminar(i, c)

    fallido = None if operacion == "editar" else False
    assert operar(otra, id_comentario) is fallido
    assert operar(id_tarea, 999_999) is fallido
    assert operar(999_999, id_comentario) is fallido
    assert not sesion_bd.in_transaction()
    assert _filas_comentarios(sesion_bd, id_tarea) == antes
    assert repositorio.existe_tarea(id_tarea) is True
    assert repositorio.existe_tarea(999_999) is False
    sesion_bd.rollback()
