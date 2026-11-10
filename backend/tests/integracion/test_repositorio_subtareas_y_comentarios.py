"""Subtareas y comentarios de las tareas sobre MySQL."""

from datetime import UTC, datetime, timedelta, timezone

import pytest
from sqlalchemy import delete, select
from sqlalchemy.exc import DBAPIError, IntegrityError

from gestor_tareas.dominio.comentario.entidades import Comentario
from gestor_tareas.dominio.tarea.entidades import Oportunidad, Subtarea, Tarea, TipoTarea
from gestor_tareas.infraestructura.persistencia.modelos import (
    ComentarioModelo,
    PersonaModelo,
    SubtareaModelo,
    TareaModelo,
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


def _tarea(nombre: str = "Mudanza", **datos) -> Tarea:
    return Tarea(nombre=nombre, descripcion="d", fecha_creacion=_FECHA, **datos)


def _filas_subtareas(sesion, id_tarea: int) -> list[tuple]:
    sesion.rollback()  # Lectura nueva, sin la instantánea de una transacción anterior.
    m = SubtareaModelo
    filas = sesion.execute(
        select(m.nombre, m.persona_id, m.prioridad, m.resuelta)
        .where(m.tarea_id == id_tarea)
        .order_by(m.id)
    ).all()
    return [tuple(f) for f in filas]


def _filas_comentarios(sesion, id_tarea: int) -> list[tuple]:
    sesion.rollback()
    m = ComentarioModelo
    filas = sesion.execute(
        select(m.texto, m.creado).where(m.tarea_id == id_tarea).order_by(m.id)
    ).all()
    return [tuple(f) for f in filas]


def _personas(sesion) -> list[tuple[int, str]]:
    sesion.rollback()
    filas = sesion.execute(
        select(PersonaModelo.id, PersonaModelo.nombre).order_by(PersonaModelo.id)
    )
    return [tuple(f) for f in filas]


def test_anadir_subtarea_la_guarda_pendiente_con_su_persona(sesion_bd) -> None:
    repositorio = RepositorioTareasSqlAlchemy(sesion_bd)
    (ana,) = RepositorioPersonasSqlAlchemy(sesion_bd).obtener_o_crear(["Ana"])
    id_tarea = repositorio.crear(_tarea()).id

    tarea = repositorio.anadir_subtarea(
        id_tarea, Subtarea(nombre="Camión", asignado="Ana", prioridad=2)
    )
    tarea = repositorio.anadir_subtarea(id_tarea, Subtarea(nombre="Cajas", resuelta=True))

    assert [(s.nombre, s.asignado, s.prioridad, s.resuelta) for s in tarea.subtareas] == [
        ("Camión", "Ana", 2, False),
        ("Cajas", None, None, False),
    ]
    assert tarea.subtareas[0].id < tarea.subtareas[1].id
    assert _filas_subtareas(sesion_bd, id_tarea) == [
        ("Camión", ana.id, 2, False),
        ("Cajas", None, None, False),
    ]
    assert repositorio.obtener_por_id(id_tarea).subtareas == tarea.subtareas
    assert repositorio.listar()[0].subtareas == tarea.subtareas


def test_anadir_subtarea_a_una_tarea_que_no_existe_deshace_el_alta_de_la_persona(
    sesion_bd,
) -> None:
    RepositorioPersonasSqlAlchemy(sesion_bd).obtener_o_crear(["Luis"])

    resultado = RepositorioTareasSqlAlchemy(sesion_bd).anadir_subtarea(
        999_999, Subtarea(nombre="Embalar", asignado="Luis")
    )

    assert resultado is None
    assert not sesion_bd.in_transaction()
    assert _personas(sesion_bd) == []


def test_cambiar_resuelta_subtarea_solo_cambia_esa_subtarea(sesion_bd) -> None:
    repositorio = RepositorioTareasSqlAlchemy(sesion_bd)
    id_tarea = repositorio.crear(_tarea()).id
    repositorio.anadir_subtarea(id_tarea, Subtarea(nombre="Embalar"))
    ids = [
        s.id for s in repositorio.anadir_subtarea(id_tarea, Subtarea(nombre="Limpiar")).subtareas
    ]

    resuelta = repositorio.cambiar_resuelta_subtarea(id_tarea, ids[0], True)
    assert [s.resuelta for s in resuelta.subtareas] == [True, False]
    assert _filas_subtareas(sesion_bd, id_tarea) == [
        ("Embalar", None, None, True),
        ("Limpiar", None, None, False),
    ]

    reabierta = repositorio.cambiar_resuelta_subtarea(id_tarea, ids[0], False)
    assert [s.resuelta for s in reabierta.subtareas] == [False, False]
    assert _filas_subtareas(sesion_bd, id_tarea)[0] == ("Embalar", None, None, False)


def test_eliminar_subtarea_la_borra_aunque_la_tarea_ya_este_en_la_sesion(sesion_bd) -> None:
    repositorio = RepositorioTareasSqlAlchemy(sesion_bd)
    id_tarea = repositorio.crear(_tarea()).id
    repositorio.anadir_subtarea(id_tarea, Subtarea(nombre="Embalar"))
    ids = [
        s.id for s in repositorio.anadir_subtarea(id_tarea, Subtarea(nombre="Limpiar")).subtareas
    ]
    # La tarea queda en la sesión con sus dos subtareas cargadas (se guarda una
    # referencia: el mapa de identidades de la sesión solo guarda referencias débiles).
    cargada = sesion_bd.get(TareaModelo, id_tarea)
    assert len(cargada.subtareas) == 2

    tarea = repositorio.eliminar_subtarea(id_tarea, ids[0])

    assert [s.nombre for s in tarea.subtareas] == ["Limpiar"]
    assert [s.nombre for s in cargada.subtareas] == ["Limpiar"]
    assert _filas_subtareas(sesion_bd, id_tarea) == [("Limpiar", None, None, False)]


@pytest.mark.parametrize("operacion", ["cambiar", "eliminar"])
def test_operar_sobre_una_subtarea_ajena_o_inexistente_devuelve_none(sesion_bd, operacion) -> None:
    repositorio = RepositorioTareasSqlAlchemy(sesion_bd)
    id_tarea = repositorio.crear(_tarea()).id
    otra = repositorio.crear(_tarea("Viaje")).id
    ajena = repositorio.anadir_subtarea(otra, Subtarea(nombre="Reservar")).subtareas[0].id

    def operar(i: int, s: int):
        if operacion == "cambiar":
            return repositorio.cambiar_resuelta_subtarea(i, s, True)
        return repositorio.eliminar_subtarea(i, s)

    assert operar(id_tarea, ajena) is None
    assert operar(id_tarea, 999_999) is None
    assert operar(999_999, ajena) is None
    assert not sesion_bd.in_transaction()
    assert _filas_subtareas(sesion_bd, otra) == [("Reservar", None, None, False)]


def test_editar_la_tarea_o_cambiar_su_tipo_no_altera_sus_subtareas(sesion_bd) -> None:
    repositorio = RepositorioTareasSqlAlchemy(sesion_bd)
    id_tarea = repositorio.crear(_tarea()).id
    id_sub = repositorio.anadir_subtarea(id_tarea, Subtarea(nombre="Embalar")).subtareas[0].id
    repositorio.cambiar_resuelta_subtarea(id_tarea, id_sub, True)

    tarea = repositorio.obtener_por_id(id_tarea)
    tarea.tipo = TipoTarea.OPORTUNIDAD
    tarea.oportunidad = Oportunidad(codigo="OP")
    tarea.subtareas = []  # Se ignora.
    editada = repositorio.actualizar(tarea)
    editada.tipo, editada.oportunidad = None, None
    sin_tipo = repositorio.actualizar(editada)

    esperadas = [Subtarea(id=id_sub, nombre="Embalar", resuelta=True)]
    assert repositorio.obtener_por_id(id_tarea).subtareas == esperadas
    assert sin_tipo.subtareas == esperadas
    assert _filas_subtareas(sesion_bd, id_tarea) == [("Embalar", None, None, True)]


def test_la_base_de_datos_rechaza_una_prioridad_fuera_de_rango(sesion_bd) -> None:
    id_tarea = RepositorioTareasSqlAlchemy(sesion_bd).crear(_tarea()).id
    sesion_bd.add(SubtareaModelo(tarea_id=id_tarea, nombre="X", prioridad=6))
    # MySQL informa de la violación del CHECK como OperationalError (3819).
    with pytest.raises(DBAPIError, match="ck_subtareas_prioridad_rango"):
        sesion_bd.commit()
    sesion_bd.rollback()


def test_no_se_puede_borrar_una_persona_asignada_a_una_subtarea(sesion_bd) -> None:
    (ana,) = RepositorioPersonasSqlAlchemy(sesion_bd).obtener_o_crear(["Ana"])
    repositorio = RepositorioTareasSqlAlchemy(sesion_bd)
    id_tarea = repositorio.crear(_tarea()).id
    repositorio.anadir_subtarea(id_tarea, Subtarea(nombre="Embalar", asignado="Ana"))

    with pytest.raises(IntegrityError):
        sesion_bd.execute(delete(PersonaModelo).where(PersonaModelo.id == ana.id))
    sesion_bd.rollback()
    assert _personas(sesion_bd) == [(ana.id, "Ana")]


def test_crear_comentario_guarda_el_instante_en_utc(sesion_bd) -> None:
    id_tarea = RepositorioTareasSqlAlchemy(sesion_bd).crear(_tarea()).id
    repositorio = RepositorioComentariosSqlAlchemy(sesion_bd)
    madrid = timezone(timedelta(hours=1))

    comentario = repositorio.crear(
        Comentario(
            id_tarea=id_tarea,
            texto="Uno\nDos",
            creado=datetime(2026, 11, 10, 17, 30, 5, tzinfo=madrid),
        )
    )

    assert comentario.id is not None
    assert comentario.texto == "Uno\nDos"
    assert comentario.creado == datetime(2026, 11, 10, 16, 30, 5, tzinfo=UTC)
    assert comentario.creado.utcoffset() == timedelta(0)
    assert not sesion_bd.in_transaction()
    assert _filas_comentarios(sesion_bd, id_tarea) == [
        ("Uno\nDos", datetime(2026, 11, 10, 16, 30, 5))
    ]


def test_crear_comentario_en_una_tarea_que_no_existe_devuelve_none(sesion_bd) -> None:
    repositorio = RepositorioComentariosSqlAlchemy(sesion_bd)
    comentario = Comentario(id_tarea=999_999, texto="Hola", creado=datetime.now(UTC))

    assert repositorio.crear(comentario) is None
    assert not sesion_bd.in_transaction()
    assert repositorio.listar_de_tarea(999_999) is None
    assert sesion_bd.scalars(select(ComentarioModelo)).all() == []


def test_listar_comentarios_por_instante_y_orden_de_alta(sesion_bd) -> None:
    tareas = RepositorioTareasSqlAlchemy(sesion_bd)
    id_tarea = tareas.crear(_tarea()).id
    otra = tareas.crear(_tarea("Viaje")).id
    repositorio = RepositorioComentariosSqlAlchemy(sesion_bd)
    a_las = lambda h: datetime(2026, 11, 10, h, 0, tzinfo=UTC)  # noqa: E731
    for id_t, texto, hora in [
        (id_tarea, "Tercero", 12),
        (id_tarea, "Primero", 11),
        (otra, "De otra", 10),
        (id_tarea, "Segundo", 11),
    ]:
        repositorio.crear(Comentario(id_tarea=id_t, texto=texto, creado=a_las(hora)))

    listado = repositorio.listar_de_tarea(id_tarea)

    assert [(c.texto, c.creado) for c in listado] == [
        ("Primero", a_las(11)),
        ("Segundo", a_las(11)),
        ("Tercero", a_las(12)),
    ]
    assert all(c.id_tarea == id_tarea for c in listado)
    assert [c.texto for c in repositorio.listar_de_tarea(otra)] == ["De otra"]
    sesion_bd.rollback()


def test_borrar_la_tarea_borra_sus_subtareas_y_comentarios_en_cascada(sesion_bd) -> None:
    tareas = RepositorioTareasSqlAlchemy(sesion_bd)
    comentarios = RepositorioComentariosSqlAlchemy(sesion_bd)
    borrada = tareas.crear(_tarea()).id
    conservada = tareas.crear(_tarea("Viaje")).id
    for id_tarea in (borrada, conservada):
        tareas.anadir_subtarea(id_tarea, Subtarea(nombre="Sub"))
        comentarios.crear(
            Comentario(id_tarea=id_tarea, texto="C", creado=datetime(2026, 1, 1, tzinfo=UTC))
        )

    sesion_bd.execute(delete(TareaModelo).where(TareaModelo.id == borrada))
    sesion_bd.commit()

    assert _filas_subtareas(sesion_bd, borrada) == []
    assert _filas_comentarios(sesion_bd, borrada) == []
    assert _filas_subtareas(sesion_bd, conservada) == [("Sub", None, None, False)]
    assert _filas_comentarios(sesion_bd, conservada) == [("C", datetime(2026, 1, 1))]
