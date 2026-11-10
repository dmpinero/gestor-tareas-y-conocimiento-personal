"""Pasos de las tareas de tipo oportunidad sobre MySQL."""

from datetime import datetime

from sqlalchemy import delete, select

from gestor_tareas.dominio.tarea.entidades import Oportunidad, PasoOportunidad, Tarea, TipoTarea
from gestor_tareas.infraestructura.persistencia.modelos import PasoOportunidadModelo, TareaModelo
from gestor_tareas.infraestructura.persistencia.repositorios.repositorio_tareas_sqlalchemy import (
    RepositorioTareasSqlAlchemy,
)
from gestor_tareas.infraestructura.persistencia.repositorios.repositorio_workflow_oportunidades_sqlalchemy import (  # noqa: E501
    RepositorioWorkflowOportunidadesSqlAlchemy,
)

_FECHA_CREACION = datetime(2026, 11, 10, 9, 0, 0)


def _oportunidad(*pasos: str) -> Tarea:
    return Tarea(
        nombre="Venta",
        descripcion="d",
        fecha_creacion=_FECHA_CREACION,
        tipo=TipoTarea.OPORTUNIDAD,
        oportunidad=Oportunidad(codigo="OP-1"),
        pasos_oportunidad=[
            PasoOportunidad(numero=i, nombre=nombre) for i, nombre in enumerate(pasos, start=1)
        ],
    )


def _filas_pasos(sesion, id_tarea: int) -> list[tuple[int, str, bool]]:
    sesion.rollback()  # Lectura nueva, sin la instantánea de una transacción anterior.
    modelo = PasoOportunidadModelo
    filas = sesion.execute(
        select(modelo.numero, modelo.nombre, modelo.hecho)
        .where(modelo.tarea_id == id_tarea)
        .order_by(modelo.numero)
    ).all()
    return [tuple(f) for f in filas]


def _sin_id(tarea: Tarea) -> list[tuple[int, str, bool]]:
    return [(p.numero, p.nombre, p.hecho) for p in tarea.pasos_oportunidad]


def test_crear_guarda_los_pasos_de_la_oportunidad_y_les_asigna_id(sesion_bd) -> None:
    repositorio = RepositorioTareasSqlAlchemy(sesion_bd)

    creada = repositorio.crear(_oportunidad("Contactar", "Proponer", "Cerrar"))

    esperados = [(1, "Contactar", False), (2, "Proponer", False), (3, "Cerrar", False)]
    assert _sin_id(creada) == esperados
    assert len({p.id for p in creada.pasos_oportunidad} - {None}) == 3
    assert _filas_pasos(sesion_bd, creada.id) == esperados


def test_obtener_y_listar_devuelven_los_pasos_ordenados_por_numero(sesion_bd) -> None:
    repositorio = RepositorioTareasSqlAlchemy(sesion_bd)
    creada = repositorio.crear(_oportunidad("Contactar", "Proponer"))
    sin_tipo = repositorio.crear(Tarea(nombre="T", descripcion="d", fecha_creacion=_FECHA_CREACION))
    sesion_bd.expunge_all()

    assert _sin_id(repositorio.obtener_por_id(creada.id)) == [
        (1, "Contactar", False),
        (2, "Proponer", False),
    ]
    listadas = {t.id: t for t in repositorio.listar()}
    assert [p.nombre for p in listadas[creada.id].pasos_oportunidad] == ["Contactar", "Proponer"]
    assert listadas[sin_tipo.id].pasos_oportunidad == []


def test_actualizar_una_oportunidad_que_sigue_siendolo_conserva_sus_pasos(sesion_bd) -> None:
    repositorio = RepositorioTareasSqlAlchemy(sesion_bd)
    creada = repositorio.crear(_oportunidad("Contactar", "Proponer"))
    ids = [p.id for p in creada.pasos_oportunidad]
    repositorio.cambiar_hecho_paso(creada.id, ids[0], True)

    tarea = repositorio.obtener_por_id(creada.id)
    tarea.nombre = "Editada"
    tarea.pasos_oportunidad = []  # Se ignora: los pasos no se editan con la tarea.
    actualizada = repositorio.actualizar(tarea)

    assert [p.id for p in actualizada.pasos_oportunidad] == ids
    assert _filas_pasos(sesion_bd, creada.id) == [(1, "Contactar", True), (2, "Proponer", False)]


def test_actualizar_una_oportunidad_para_quitarle_el_tipo_borra_sus_pasos(sesion_bd) -> None:
    repositorio = RepositorioTareasSqlAlchemy(sesion_bd)
    creada = repositorio.crear(_oportunidad("Contactar", "Proponer"))

    tarea = repositorio.obtener_por_id(creada.id)
    tarea.tipo = None
    tarea.oportunidad = None
    actualizada = repositorio.actualizar(tarea)

    assert actualizada.pasos_oportunidad == []
    assert _filas_pasos(sesion_bd, creada.id) == []


def test_actualizar_una_tarea_para_hacerla_oportunidad_no_le_crea_pasos(sesion_bd) -> None:
    repositorio = RepositorioTareasSqlAlchemy(sesion_bd)
    creada = repositorio.crear(Tarea(nombre="T", descripcion="d", fecha_creacion=_FECHA_CREACION))

    tarea = repositorio.obtener_por_id(creada.id)
    tarea.tipo = TipoTarea.OPORTUNIDAD
    tarea.oportunidad = Oportunidad(codigo="OP-1")
    tarea.pasos_oportunidad = [PasoOportunidad(numero=1, nombre="Ignorado")]
    actualizada = repositorio.actualizar(tarea)

    assert actualizada.pasos_oportunidad == []
    assert _filas_pasos(sesion_bd, creada.id) == []


def test_cambiar_hecho_paso_guarda_hecho_y_pendiente_solo_en_ese_paso(sesion_bd) -> None:
    repositorio = RepositorioTareasSqlAlchemy(sesion_bd)
    creada = repositorio.crear(_oportunidad("Contactar", "Proponer"))
    segundo = creada.pasos_oportunidad[1].id

    hecho = repositorio.cambiar_hecho_paso(creada.id, segundo, True)

    assert _sin_id(hecho) == [(1, "Contactar", False), (2, "Proponer", True)]
    assert (hecho.nombre, hecho.completada) == ("Venta", False)
    assert _filas_pasos(sesion_bd, creada.id) == [(1, "Contactar", False), (2, "Proponer", True)]

    pendiente = repositorio.cambiar_hecho_paso(creada.id, segundo, False)

    assert [p.hecho for p in pendiente.pasos_oportunidad] == [False, False]
    assert _filas_pasos(sesion_bd, creada.id) == [(1, "Contactar", False), (2, "Proponer", False)]


def test_cambiar_hecho_paso_devuelve_none_si_la_tarea_no_tiene_ese_paso(sesion_bd) -> None:
    repositorio = RepositorioTareasSqlAlchemy(sesion_bd)
    una = repositorio.crear(_oportunidad("Contactar"))
    otra = repositorio.crear(_oportunidad("Proponer"))
    paso_de_otra = otra.pasos_oportunidad[0].id

    assert repositorio.cambiar_hecho_paso(una.id, paso_de_otra, True) is None
    assert repositorio.cambiar_hecho_paso(una.id, 999_999, True) is None
    assert repositorio.cambiar_hecho_paso(999_999, paso_de_otra, True) is None
    assert not sesion_bd.in_transaction()
    assert _filas_pasos(sesion_bd, otra.id) == [(1, "Proponer", False)]


def test_borrar_la_tarea_borra_sus_pasos_en_cascada(sesion_bd) -> None:
    repositorio = RepositorioTareasSqlAlchemy(sesion_bd)
    borrada = repositorio.crear(_oportunidad("Contactar", "Proponer"))
    conservada = repositorio.crear(_oportunidad("Cerrar"))

    sesion_bd.execute(delete(TareaModelo).where(TareaModelo.id == borrada.id))
    sesion_bd.commit()

    assert _filas_pasos(sesion_bd, borrada.id) == []
    assert _filas_pasos(sesion_bd, conservada.id) == [(1, "Cerrar", False)]


def test_leer_pasos_para_copiar_devuelve_el_workflow_por_numero(sesion_bd) -> None:
    workflow = RepositorioWorkflowOportunidadesSqlAlchemy(sesion_bd)
    ids = [workflow.anadir_paso(n).id for n in ("Contactar", "Proponer", "Cerrar")]
    workflow.reordenar_pasos([ids[2], ids[0], ids[1]])

    pasos = workflow.leer_pasos_para_copiar()

    assert [(p.numero, p.nombre) for p in pasos] == [
        (1, "Cerrar"),
        (2, "Contactar"),
        (3, "Proponer"),
    ]
    sesion_bd.rollback()
