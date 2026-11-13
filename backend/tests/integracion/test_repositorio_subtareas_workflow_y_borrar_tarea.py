"""Alta de tareas con subtareas (las de su workflow) y borrado de tareas sobre MySQL."""

from datetime import UTC, datetime

from sqlalchemy import func, select

from gestor_tareas.dominio.comentario.entidades import Comentario, ComentarioSubtarea
from gestor_tareas.dominio.tarea.entidades import Oportunidad, Subtarea, Tarea, TipoTarea
from gestor_tareas.infraestructura.persistencia import modelos
from gestor_tareas.infraestructura.persistencia.repositorios.repositorio_comentarios_sqlalchemy import (  # noqa: E501
    RepositorioComentariosSqlAlchemy,
)
from gestor_tareas.infraestructura.persistencia.repositorios.repositorio_comentarios_subtarea_sqlalchemy import (  # noqa: E501
    RepositorioComentariosSubtareaSqlAlchemy,
)
from gestor_tareas.infraestructura.persistencia.repositorios.repositorio_tareas_sqlalchemy import (
    RepositorioTareasSqlAlchemy,
)
from gestor_tareas.infraestructura.persistencia.repositorios.repositorios_catalogos_sqlalchemy import (  # noqa: E501
    RepositorioEtiquetasSqlAlchemy,
    RepositorioPersonasSqlAlchemy,
)

_FECHA_CREACION = datetime(2026, 11, 10, 9, 0, 0)
_CREADO = datetime(2026, 11, 10, 9, 30, 0, tzinfo=UTC)


def _oportunidad(*subtareas: str, nombre: str = "Venta") -> Tarea:
    return Tarea(
        nombre=nombre,
        descripcion="d",
        fecha_creacion=_FECHA_CREACION,
        tipo=TipoTarea.OPORTUNIDAD,
        oportunidad=Oportunidad(codigo="OP-1"),
        subtareas=[Subtarea(nombre=s) for s in subtareas],
    )


def _filas_subtareas(sesion, id_tarea: int) -> list[tuple]:
    sesion.rollback()  # Lectura nueva, sin la instantánea de una transacción anterior.
    m = modelos.SubtareaModelo
    filas = sesion.execute(
        select(m.nombre, m.persona_id, m.prioridad, m.resuelta)
        .where(m.tarea_id == id_tarea)
        .order_by(m.id)
    ).all()
    return [tuple(f) for f in filas]


def _sin_id(tarea: Tarea) -> list[tuple]:
    return [(s.nombre, s.asignado, s.prioridad, s.resuelta, s.comentarios) for s in tarea.subtareas]


def _filas_de_tarea(sesion, id_tarea: int) -> dict[str, int]:
    """Número de filas de la tarea en cada tabla que depende de ella."""
    sesion.rollback()
    ids_subtareas = select(modelos.SubtareaModelo.id).where(
        modelos.SubtareaModelo.tarea_id == id_tarea
    )
    consultas = {
        "tareas": select(func.count()).where(modelos.TareaModelo.id == id_tarea),
        "oportunidades": select(func.count()).where(modelos.OportunidadModelo.tarea_id == id_tarea),
        "tarea_etiquetas": select(func.count()).where(
            modelos.tarea_etiquetas.c.tarea_id == id_tarea
        ),
        "tarea_personas": select(func.count()).where(modelos.tarea_personas.c.tarea_id == id_tarea),
        "subtareas": select(func.count()).where(modelos.SubtareaModelo.tarea_id == id_tarea),
        "comentarios": select(func.count()).where(modelos.ComentarioModelo.tarea_id == id_tarea),
        "comentarios_subtarea": select(func.count()).where(
            modelos.ComentarioSubtareaModelo.subtarea_id.in_(ids_subtareas)
        ),
    }
    filas = {tabla: sesion.scalar(consulta) for tabla, consulta in consultas.items()}
    sesion.rollback()
    return filas


def _catalogos(sesion) -> tuple[list[str], list[str]]:
    sesion.rollback()
    etiquetas = sesion.scalars(select(modelos.EtiquetaModelo.nombre)).all()
    personas = sesion.scalars(select(modelos.PersonaModelo.nombre)).all()
    sesion.rollback()
    return sorted(etiquetas), sorted(personas)


def _tarea_completa(sesion, nombre: str) -> Tarea:
    """Oportunidad con etiqueta, persona, subtareas, comentarios y comentarios de
    subtareas, para comprobar que el borrado se lleva todo."""
    RepositorioEtiquetasSqlAlchemy(sesion).obtener_o_crear(["Clientes"])
    RepositorioPersonasSqlAlchemy(sesion).obtener_o_crear(["Ana"])
    tarea = _oportunidad("Llamar", "Cerrar", nombre=nombre)
    tarea.etiquetas = ["Clientes"]
    tarea.asignados = ["Ana"]
    creada = RepositorioTareasSqlAlchemy(sesion).crear(tarea)
    RepositorioComentariosSqlAlchemy(sesion).crear(
        Comentario(id_tarea=creada.id, texto="De la tarea", creado=_CREADO)
    )
    for subtarea in creada.subtareas:
        RepositorioComentariosSubtareaSqlAlchemy(sesion).crear(
            ComentarioSubtarea(
                id_tarea=creada.id, id_subtarea=subtarea.id, texto="De la subtarea", creado=_CREADO
            )
        )
    return creada


def test_crear_guarda_las_subtareas_en_su_orden_y_les_asigna_id(sesion_bd) -> None:
    repositorio = RepositorioTareasSqlAlchemy(sesion_bd)

    creada = repositorio.crear(_oportunidad("Contactar", "Proponer", "Cerrar"))

    esperadas = [
        ("Contactar", None, None, False, 0),
        ("Proponer", None, None, False, 0),
        ("Cerrar", None, None, False, 0),
    ]
    assert _sin_id(creada) == esperadas
    ids = [s.id for s in creada.subtareas]
    assert None not in ids
    assert ids == sorted(ids)
    assert _filas_subtareas(sesion_bd, creada.id) == [
        ("Contactar", None, None, False),
        ("Proponer", None, None, False),
        ("Cerrar", None, None, False),
    ]
    assert _sin_id(repositorio.obtener_por_id(creada.id)) == esperadas


def test_crear_guarda_la_persona_la_prioridad_y_el_estado_de_las_subtareas(sesion_bd) -> None:
    (persona,) = RepositorioPersonasSqlAlchemy(sesion_bd).obtener_o_crear(["Ana"])
    tarea = _oportunidad()
    tarea.subtareas = [Subtarea(nombre="Llamar", asignado="Ana", prioridad=2, resuelta=True)]

    creada = RepositorioTareasSqlAlchemy(sesion_bd).crear(tarea)

    assert _sin_id(creada) == [("Llamar", "Ana", 2, True, 0)]
    assert _filas_subtareas(sesion_bd, creada.id) == [("Llamar", persona.id, 2, True)]


def test_actualizar_una_oportunidad_para_quitarle_el_tipo_conserva_sus_subtareas(
    sesion_bd,
) -> None:
    repositorio = RepositorioTareasSqlAlchemy(sesion_bd)
    creada = repositorio.crear(_oportunidad("Contactar", "Proponer"))
    creada.tipo = None
    creada.oportunidad = None

    editada = repositorio.actualizar(creada)

    assert editada.tipo is None
    assert [s.nombre for s in editada.subtareas] == ["Contactar", "Proponer"]
    assert _filas_subtareas(sesion_bd, creada.id) == [
        ("Contactar", None, None, False),
        ("Proponer", None, None, False),
    ]


def test_las_subtareas_devuelven_su_numero_de_comentarios(sesion_bd) -> None:
    repositorio = RepositorioTareasSqlAlchemy(sesion_bd)
    creada = repositorio.crear(_oportunidad("Contactar", "Proponer"))
    comentarios = RepositorioComentariosSubtareaSqlAlchemy(sesion_bd)
    for texto in ("Uno", "Dos"):
        comentarios.crear(
            ComentarioSubtarea(
                id_tarea=creada.id,
                id_subtarea=creada.subtareas[1].id,
                texto=texto,
                creado=_CREADO,
            )
        )

    assert [s.comentarios for s in repositorio.obtener_por_id(creada.id).subtareas] == [0, 2]
    assert [s.comentarios for s in repositorio.listar()[0].subtareas] == [0, 2]


def test_eliminar_borra_la_tarea_y_todo_lo_suyo_y_conserva_lo_demas(sesion_bd) -> None:
    borrada = _tarea_completa(sesion_bd, "Venta")
    conservada = _tarea_completa(sesion_bd, "Otra venta")
    antes = _filas_de_tarea(sesion_bd, borrada.id)
    assert all(n > 0 for n in antes.values())
    repositorio = RepositorioTareasSqlAlchemy(sesion_bd)

    assert repositorio.eliminar(borrada.id) is True

    assert not sesion_bd.in_transaction()
    assert set(_filas_de_tarea(sesion_bd, borrada.id).values()) == {0}
    assert _filas_de_tarea(sesion_bd, conservada.id) == antes
    assert repositorio.obtener_por_id(borrada.id) is None
    assert [t.id for t in repositorio.listar()] == [conservada.id]
    assert _catalogos(sesion_bd) == (["Clientes"], ["Ana"])


def test_eliminar_devuelve_false_si_la_tarea_no_existe(sesion_bd) -> None:
    conservada = _tarea_completa(sesion_bd, "Venta")
    antes = _filas_de_tarea(sesion_bd, conservada.id)

    assert RepositorioTareasSqlAlchemy(sesion_bd).eliminar(999_999) is False

    assert not sesion_bd.in_transaction()
    assert _filas_de_tarea(sesion_bd, conservada.id) == antes
