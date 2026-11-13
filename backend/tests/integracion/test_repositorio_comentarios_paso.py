"""Comentarios de los pasos de los workflows, y su copia en las subtareas, sobre MySQL."""

from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from gestor_tareas.dominio.comentario.entidades import ComentarioPaso, ComentarioSubtarea
from gestor_tareas.dominio.tarea.entidades import ComentarioInicial, Subtarea, Tarea
from gestor_tareas.dominio.workflow.entidades import Workflow
from gestor_tareas.infraestructura.persistencia.modelos import (
    ComentarioPasoModelo,
    ComentarioSubtareaModelo,
)
from gestor_tareas.infraestructura.persistencia.repositorios.repositorio_comentarios_paso_sqlalchemy import (  # noqa: E501
    RepositorioComentariosPasoSqlAlchemy,
)
from gestor_tareas.infraestructura.persistencia.repositorios.repositorio_comentarios_subtarea_sqlalchemy import (  # noqa: E501
    RepositorioComentariosSubtareaSqlAlchemy,
)
from gestor_tareas.infraestructura.persistencia.repositorios.repositorio_tareas_sqlalchemy import (
    RepositorioTareasSqlAlchemy,
)
from gestor_tareas.infraestructura.persistencia.repositorios.repositorio_workflows_sqlalchemy import (  # noqa: E501
    RepositorioWorkflowsSqlAlchemy,
)

_FECHA = datetime(2026, 11, 10, 9, 0, 0)
_CREADO = datetime(2026, 11, 10, 16, 30, 5, tzinfo=UTC)
_COPIA = datetime(2026, 11, 12, 8, 0, 0, tzinfo=UTC)


def _workflow(sesion, nombre: str, *pasos: str) -> Workflow:
    repositorio = RepositorioWorkflowsSqlAlchemy(sesion)
    workflow = repositorio.crear(nombre)
    for paso in pasos:
        workflow = repositorio.anadir_paso(workflow.id, paso)
    return workflow


def _comentar(sesion, workflow: Workflow, indice: int, *textos: str, creado=_CREADO) -> list:
    repositorio = RepositorioComentariosPasoSqlAlchemy(sesion)
    paso = workflow.pasos[indice]
    return [
        repositorio.crear(
            ComentarioPaso(id_workflow=workflow.id, id_paso=paso.id, texto=t, creado=creado)
        )
        for t in textos
    ]


def _filas_paso(sesion) -> list[tuple]:
    sesion.rollback()
    m = ComentarioPasoModelo
    filas = [tuple(f) for f in sesion.execute(select(m.paso_id, m.texto).order_by(m.id))]
    sesion.rollback()
    return filas


def test_crear_y_listar_devuelve_los_comentarios_del_paso_en_orden_cronologico(sesion_bd) -> None:
    workflow = _workflow(sesion_bd, "Ventas", "Contacto", "Cierre")
    _comentar(sesion_bd, workflow, 0, "Tarde", creado=_CREADO + timedelta(hours=1))
    (temprano,) = _comentar(sesion_bd, workflow, 0, "Temprano")
    _comentar(sesion_bd, workflow, 1, "Otro paso")

    comentarios = RepositorioComentariosPasoSqlAlchemy(sesion_bd).listar_de_paso(
        workflow.id, workflow.pasos[0].id
    )

    assert [c.texto for c in comentarios] == ["Temprano", "Tarde"]
    assert comentarios[0] == temprano
    assert temprano == ComentarioPaso(
        id=temprano.id,
        id_workflow=workflow.id,
        id_paso=workflow.pasos[0].id,
        texto="Temprano",
        creado=_CREADO,
    )


def test_las_operaciones_con_un_paso_de_otro_workflow_no_hacen_nada(sesion_bd) -> None:
    ventas = _workflow(sesion_bd, "Ventas", "Contacto")
    compras = _workflow(sesion_bd, "Compras", "Pedido")
    (comentario,) = _comentar(sesion_bd, compras, 0, "Pedir")
    repositorio = RepositorioComentariosPasoSqlAlchemy(sesion_bd)
    id_paso = compras.pasos[0].id

    nuevo = ComentarioPaso(id_workflow=ventas.id, id_paso=id_paso, texto="x", creado=_CREADO)
    assert repositorio.crear(nuevo) is None
    assert repositorio.listar_de_paso(ventas.id, id_paso) is None
    assert repositorio.editar(ventas.id, id_paso, comentario.id, "x", _CREADO) is None
    assert repositorio.eliminar(ventas.id, id_paso, comentario.id) is False
    assert repositorio.existe_paso(ventas.id, id_paso) is False
    assert repositorio.existe_workflow(ventas.id) is True
    assert repositorio.existe_workflow(999999) is False
    assert _filas_paso(sesion_bd) == [(id_paso, "Pedir")]


def test_editar_y_eliminar_solo_tocan_el_comentario_del_paso(sesion_bd) -> None:
    workflow = _workflow(sesion_bd, "Ventas", "Contacto", "Cierre")
    uno, dos = _comentar(sesion_bd, workflow, 0, "Uno", "Dos")
    (otro,) = _comentar(sesion_bd, workflow, 1, "Otro")
    repositorio = RepositorioComentariosPasoSqlAlchemy(sesion_bd)
    id_workflow, id_paso = workflow.id, workflow.pasos[0].id
    editado_en = _CREADO + timedelta(days=1)

    # Un comentario de otro paso del mismo workflow no es del paso.
    assert repositorio.editar(id_workflow, id_paso, otro.id, "x", editado_en) is None
    editado = repositorio.editar(id_workflow, id_paso, uno.id, "Uno bis", editado_en)
    assert repositorio.eliminar(id_workflow, id_paso, dos.id) is True

    assert (editado.texto, editado.creado, editado.editado) == ("Uno bis", _CREADO, editado_en)
    assert repositorio.listar_de_paso(id_workflow, id_paso) == [editado]
    assert [(t) for _, t in _filas_paso(sesion_bd)] == ["Uno bis", "Otro"]


def test_el_workflow_expone_el_numero_de_comentarios_de_cada_paso(sesion_bd) -> None:
    workflow = _workflow(sesion_bd, "Ventas", "Contacto", "Cierre")
    _comentar(sesion_bd, workflow, 0, "Uno", "Dos")
    repositorio = RepositorioWorkflowsSqlAlchemy(sesion_bd)

    listado = next(w for w in repositorio.listar() if w.id == workflow.id)
    renombrado = repositorio.renombrar_paso(workflow.id, workflow.pasos[1].id, "Firma")

    assert [p.comentarios for p in listado.pasos] == [2, 0]
    assert [p.comentarios for p in renombrado.pasos] == [2, 0]
    assert all(p.comentarios_para_copiar == [] for p in listado.pasos)


def test_borrar_un_paso_o_su_workflow_borra_sus_comentarios(sesion_bd) -> None:
    ventas = _workflow(sesion_bd, "Ventas", "Contacto", "Cierre")
    compras = _workflow(sesion_bd, "Compras", "Pedido")
    _comentar(sesion_bd, ventas, 0, "Uno")
    _comentar(sesion_bd, ventas, 1, "Firmar")
    _comentar(sesion_bd, compras, 0, "Pedir")
    repositorio = RepositorioWorkflowsSqlAlchemy(sesion_bd)

    repositorio.eliminar_paso(ventas.id, ventas.pasos[0].id)
    assert [t for _, t in _filas_paso(sesion_bd)] == ["Firmar", "Pedir"]
    repositorio.eliminar(ventas.id)
    assert [t for _, t in _filas_paso(sesion_bd)] == ["Pedir"]


def test_leer_para_copiar_trae_los_textos_de_los_comentarios_de_cada_paso(sesion_bd) -> None:
    workflow = _workflow(sesion_bd, "Ventas", "Contacto", "Cierre", "Seguimiento")
    _comentar(sesion_bd, workflow, 0, "Dos", creado=_CREADO + timedelta(minutes=1))
    _comentar(sesion_bd, workflow, 0, "Uno")
    _comentar(sesion_bd, workflow, 2, "Llamar\nal mes")

    leido = RepositorioWorkflowsSqlAlchemy(sesion_bd).leer_para_copiar(workflow.id)
    sesion_bd.rollback()

    assert [p.comentarios_para_copiar for p in leido.pasos] == [
        ["Uno", "Dos"],
        [],
        ["Llamar\nal mes"],
    ]
    assert [p.comentarios for p in leido.pasos] == [2, 0, 1]


def _subtarea_con_comentarios(nombre: str, *textos: str) -> Subtarea:
    return Subtarea(
        nombre=nombre,
        comentarios_iniciales=[ComentarioInicial(texto=t, creado=_COPIA) for t in textos],
    )


def _comentarios_subtarea(sesion, tarea: Tarea, indice: int) -> list[ComentarioSubtarea]:
    return RepositorioComentariosSubtareaSqlAlchemy(sesion).listar_de_subtarea(
        tarea.id, tarea.subtareas[indice].id
    )


def test_crear_una_tarea_guarda_los_comentarios_iniciales_de_sus_subtareas_en_orden(
    sesion_bd,
) -> None:
    tareas = RepositorioTareasSqlAlchemy(sesion_bd)

    tarea = tareas.crear(
        Tarea(
            nombre="Venta",
            descripcion="d",
            fecha_creacion=_FECHA,
            subtareas=[
                _subtarea_con_comentarios("Contacto", "B", "A", "C"),
                _subtarea_con_comentarios("Cierre"),
            ],
        )
    )

    assert [s.comentarios for s in tarea.subtareas] == [3, 0]
    assert all(s.comentarios_iniciales == [] for s in tarea.subtareas)
    copiados = _comentarios_subtarea(sesion_bd, tarea, 0)
    assert [(c.texto, c.creado, c.editado) for c in copiados] == [
        ("B", _COPIA, None),
        ("A", _COPIA, None),
        ("C", _COPIA, None),
    ]
    assert _comentarios_subtarea(sesion_bd, tarea, 1) == []


def test_actualizar_una_tarea_guarda_los_comentarios_iniciales_de_las_subtareas_nuevas(
    sesion_bd,
) -> None:
    tareas = RepositorioTareasSqlAlchemy(sesion_bd)
    tarea = tareas.crear(
        Tarea(nombre="Venta", descripcion="d", fecha_creacion=_FECHA, subtareas=[Subtarea("A")])
    )

    editada = tareas.actualizar(tarea, [_subtarea_con_comentarios("Pedido", "Uno", "Dos")])

    assert [s.comentarios for s in editada.subtareas] == [0, 2]
    assert [c.texto for c in _comentarios_subtarea(sesion_bd, editada, 1)] == ["Uno", "Dos"]


def test_las_copias_y_los_comentarios_del_paso_son_independientes(sesion_bd) -> None:
    workflow = _workflow(sesion_bd, "Ventas", "Contacto")
    uno, dos = _comentar(sesion_bd, workflow, 0, "Uno", "Dos")
    leido = RepositorioWorkflowsSqlAlchemy(sesion_bd).leer_para_copiar(workflow.id)
    textos = leido.pasos[0].comentarios_para_copiar
    tarea = RepositorioTareasSqlAlchemy(sesion_bd).crear(
        Tarea(
            nombre="Venta",
            descripcion="d",
            fecha_creacion=_FECHA,
            subtareas=[_subtarea_con_comentarios("Contacto", *textos)],
        )
    )
    pasos = RepositorioComentariosPasoSqlAlchemy(sesion_bd)
    subtareas = RepositorioComentariosSubtareaSqlAlchemy(sesion_bd)
    id_workflow, id_paso = workflow.id, workflow.pasos[0].id
    id_subtarea = tarea.subtareas[0].id
    copia_uno, copia_dos = _comentarios_subtarea(sesion_bd, tarea, 0)

    # Cambiar el paso no cambia las copias.
    pasos.editar(id_workflow, id_paso, uno.id, "Uno en el paso", _COPIA)
    pasos.eliminar(id_workflow, id_paso, dos.id)
    assert _comentarios_subtarea(sesion_bd, tarea, 0) == [copia_uno, copia_dos]
    # Cambiar las copias no cambia el paso.
    subtareas.editar(tarea.id, id_subtarea, copia_uno.id, "Uno en la subtarea", _COPIA)
    subtareas.eliminar(tarea.id, id_subtarea, copia_dos.id)
    assert [c.texto for c in pasos.listar_de_paso(id_workflow, id_paso)] == ["Uno en el paso"]
    assert [c.texto for c in _comentarios_subtarea(sesion_bd, tarea, 0)] == ["Uno en la subtarea"]
    # Borrar el workflow no borra las copias.
    RepositorioWorkflowsSqlAlchemy(sesion_bd).eliminar(id_workflow)
    sesion_bd.rollback()
    assert sesion_bd.scalars(select(ComentarioSubtareaModelo.texto)).all() == ["Uno en la subtarea"]
    sesion_bd.rollback()
