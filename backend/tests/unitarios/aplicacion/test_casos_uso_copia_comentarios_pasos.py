"""Copia de los comentarios de los pasos en las subtareas que nacen de ellos."""

from datetime import UTC, datetime, timedelta, timezone

from gestor_tareas.aplicacion.comentario_paso.casos_uso import (
    AnadirComentarioPaso,
    EditarComentarioPaso,
    EliminarComentarioPaso,
)
from gestor_tareas.aplicacion.tarea.actualizar_tarea import ActualizarTarea
from gestor_tareas.aplicacion.tarea.crear_tarea import CrearTarea
from gestor_tareas.dominio.tarea.entidades import ComentarioInicial, Tarea
from tests.unitarios.aplicacion.dobles import (
    RepositorioComentariosPasoFalso,
    RepositorioEtiquetasFalso,
    RepositorioGruposEstadosFalso,
    RepositorioPersonasFalso,
    RepositorioTareasFalso,
    RepositorioWorkflowsFalso,
)

_FECHA_CREACION = datetime(2026, 11, 9, 10, 30, 0)
_ALTA_COMENTARIOS = datetime(2026, 11, 1, 8, 0, 0, tzinfo=UTC)
# 18:30:05.123456 en UTC+2: la copia se fecha a las 16:30:05 en UTC.
_AHORA = datetime(2026, 11, 10, 18, 30, 5, 123456, tzinfo=timezone(timedelta(hours=2)))
_AHORA_UTC = datetime(2026, 11, 10, 16, 30, 5, tzinfo=UTC)


class _Entorno:
    def __init__(self) -> None:
        self.tareas = RepositorioTareasFalso()
        self.workflows = RepositorioWorkflowsFalso(
            Ventas=["Contacto", "Cierre"], Compras=["Pedido"]
        )
        self.comentarios = RepositorioComentariosPasoFalso(self.workflows)
        self._repos = (
            self.tareas,
            RepositorioEtiquetasFalso(),
            RepositorioPersonasFalso(),
        )
        self._grupos = RepositorioGruposEstadosFalso()

    def comentar(self, workflow: str, paso: str, *textos: str) -> None:
        anadir = AnadirComentarioPaso(self.comentarios, reloj=lambda: _ALTA_COMENTARIOS)
        for texto in textos:
            anadir.ejecutar(
                self.workflows.id_de(workflow), self.workflows.paso(workflow, paso).id, texto
            )

    def crear(self, workflow: str | None) -> Tarea:
        return CrearTarea(
            *self._repos, self.workflows, self._grupos, reloj=lambda: _AHORA
        ).ejecutar(
            nombre="Venta",
            descripcion="d",
            fecha_creacion=_FECHA_CREACION,
            workflow_id=self.workflows.id_de(workflow) if workflow else None,
        )

    def editar(self, tarea: Tarea, workflow: str | None) -> Tarea:
        return ActualizarTarea(
            *self._repos, self._grupos, self.workflows, reloj=lambda: _AHORA
        ).ejecutar(
            tarea.id,
            nombre="Venta",
            descripcion="d",
            fecha_creacion=_FECHA_CREACION,
            workflow_id=self.workflows.id_de(workflow) if workflow else None,
        )

    def copiados(self, tarea: Tarea) -> dict[str, list[ComentarioInicial]]:
        return {s.nombre: self.tareas.comentarios_iniciales[s.id] for s in tarea.subtareas}


def _copias(*textos: str) -> list[ComentarioInicial]:
    return [ComentarioInicial(texto=t, creado=_AHORA_UTC) for t in textos]


def test_crear_con_workflow_copia_los_comentarios_de_cada_paso_en_orden_y_fechados_ahora() -> None:
    entorno = _Entorno()
    entorno.comentar("Ventas", "Contacto", "Uno", "Dos\nlíneas")
    entorno.comentar("Ventas", "Cierre", "Firmar")

    tarea = entorno.crear("Ventas")

    assert entorno.copiados(tarea) == {
        "Contacto": _copias("Uno", "Dos\nlíneas"),
        "Cierre": _copias("Firmar"),
    }
    assert [s.comentarios for s in tarea.subtareas] == [2, 1]


def test_crear_con_un_paso_sin_comentarios_crea_su_subtarea_sin_comentarios() -> None:
    entorno = _Entorno()
    entorno.comentar("Ventas", "Cierre", "Firmar")

    tarea = entorno.crear("Ventas")

    assert entorno.copiados(tarea) == {"Contacto": [], "Cierre": _copias("Firmar")}


def test_editar_para_dar_otro_workflow_copia_los_comentarios_de_sus_pasos() -> None:
    entorno = _Entorno()
    entorno.comentar("Ventas", "Contacto", "De ventas")
    entorno.comentar("Compras", "Pedido", "De compras")
    tarea = entorno.crear("Ventas")

    editada = entorno.editar(tarea, "Compras")

    assert entorno.copiados(editada) == {
        "Contacto": _copias("De ventas"),
        "Cierre": [],
        "Pedido": _copias("De compras"),
    }


def test_editar_con_el_mismo_workflow_o_sin_workflow_no_copia_comentarios() -> None:
    entorno = _Entorno()
    tarea = entorno.crear("Ventas")
    entorno.comentar("Ventas", "Contacto", "Nuevo")

    mismo = entorno.editar(tarea, "Ventas")
    sin_workflow = entorno.editar(tarea, None)

    assert entorno.copiados(mismo) == {"Contacto": [], "Cierre": []}
    assert entorno.copiados(sin_workflow) == {"Contacto": [], "Cierre": []}
    assert [s.comentarios for s in sin_workflow.subtareas] == [0, 0]


def test_cambiar_los_comentarios_del_paso_despues_no_cambia_las_copias() -> None:
    entorno = _Entorno()
    entorno.comentar("Ventas", "Contacto", "Uno", "Dos")
    tarea = entorno.crear("Ventas")
    id_workflow = entorno.workflows.id_de("Ventas")
    id_paso = entorno.workflows.paso("Ventas", "Contacto").id
    uno, dos = entorno.comentarios.listar_de_paso(id_workflow, id_paso)

    EditarComentarioPaso(entorno.comentarios).ejecutar(id_workflow, id_paso, uno.id, "Cambiado")
    EliminarComentarioPaso(entorno.comentarios).ejecutar(id_workflow, id_paso, dos.id)

    assert entorno.copiados(tarea)["Contacto"] == _copias("Uno", "Dos")
