from datetime import datetime

import pytest

from gestor_tareas.aplicacion.tarea.actualizar_tarea import ActualizarTarea
from gestor_tareas.aplicacion.tarea.crear_tarea import CrearTarea
from gestor_tareas.aplicacion.tarea.eliminar_tarea import EliminarTarea
from gestor_tareas.aplicacion.tarea.listar_tareas import ListarTareas
from gestor_tareas.aplicacion.tarea.marcar_completada import MarcarCompletada
from gestor_tareas.aplicacion.tarea.marcar_subtarea_resuelta import MarcarSubtareaResuelta
from gestor_tareas.dominio.excepciones import (
    AsignacionDeWorkflowInvalidaError,
    EntidadNoEncontradaError,
)
from gestor_tareas.dominio.tarea.entidades import (
    Oportunidad,
    ReferenciaWorkflow,
    Subtarea,
    Tarea,
    TipoTarea,
)
from tests.unitarios.aplicacion.dobles import (
    RepositorioEtiquetasFalso,
    RepositorioGruposEstadosFalso,
    RepositorioPersonasFalso,
    RepositorioTareasFalso,
    RepositorioWorkflowsFalso,
)

_FECHA_CREACION = datetime(2026, 11, 9, 10, 30, 0)
_FECHA_VENCIMIENTO = datetime(2026, 11, 20, 18, 0, 0)


class _Repositorios:
    def __init__(
        self,
        etiquetas: tuple[str, ...] = (),
        personas: tuple[str, ...] = (),
        workflows: dict[str, list[str]] | None = None,
        grupos: dict[str, list[str]] | None = None,
    ) -> None:
        self.tareas = RepositorioTareasFalso()
        self.etiquetas = RepositorioEtiquetasFalso(*etiquetas)
        self.personas = RepositorioPersonasFalso(*personas)
        self.workflows = RepositorioWorkflowsFalso(**(workflows or {}))
        self.grupos = RepositorioGruposEstadosFalso(**(grupos or {}))

    def crear(self) -> CrearTarea:
        return CrearTarea(self.tareas, self.etiquetas, self.personas, self.workflows, self.grupos)

    def actualizar(self) -> ActualizarTarea:
        return ActualizarTarea(
            self.tareas, self.etiquetas, self.personas, self.grupos, self.workflows
        )

    def marcar_completada(self) -> MarcarCompletada:
        return MarcarCompletada(self.tareas)

    def eliminar(self) -> EliminarTarea:
        return EliminarTarea(self.tareas)

    def resolver_subtarea(self) -> MarcarSubtareaResuelta:
        return MarcarSubtareaResuelta(self.tareas)


def test_crear_tarea_la_guarda_y_le_asigna_id() -> None:
    repos = _Repositorios()

    tarea = repos.crear().ejecutar(
        nombre="Preparar informe",
        prioridad=2,
        descripcion="Informe trimestral",
        fecha_creacion=_FECHA_CREACION,
    )

    assert tarea == Tarea(
        id=1,
        nombre="Preparar informe",
        prioridad=2,
        descripcion="Informe trimestral",
        fecha_creacion=_FECHA_CREACION,
        fecha_vencimiento=None,
        etiquetas=[],
        asignados=[],
    )
    assert repos.tareas.listar() == [tarea]
    assert repos.etiquetas.listar() == []
    assert repos.personas.listar() == []


def test_crear_tarea_sin_prioridad_la_guarda_con_prioridad_nula() -> None:
    repos = _Repositorios()

    tarea = repos.crear().ejecutar(
        nombre="Leer", prioridad=None, descripcion="Un libro", fecha_creacion=_FECHA_CREACION
    )

    assert tarea.prioridad is None
    assert repos.tareas.listar() == [tarea]


def test_crear_tarea_guarda_la_fecha_de_vencimiento() -> None:
    repos = _Repositorios()

    tarea = repos.crear().ejecutar(
        nombre="Leer",
        descripcion="Un libro",
        fecha_creacion=_FECHA_CREACION,
        fecha_vencimiento=_FECHA_VENCIMIENTO,
    )

    assert tarea.fecha_vencimiento == _FECHA_VENCIMIENTO
    assert repos.tareas.listar()[0].fecha_vencimiento == _FECHA_VENCIMIENTO


def test_crear_tarea_da_de_alta_etiquetas_y_personas_nuevas_ordenadas() -> None:
    repos = _Repositorios()

    tarea = repos.crear().ejecutar(
        nombre="Leer",
        descripcion="Un libro",
        fecha_creacion=_FECHA_CREACION,
        etiquetas=["urgente", "Casa", "bajo"],
        asignados=["Lucía", "ana"],
    )

    assert tarea.etiquetas == ["bajo", "Casa", "urgente"]
    assert tarea.asignados == ["ana", "Lucía"]
    assert [e.nombre for e in repos.etiquetas.listar()] == ["bajo", "Casa", "urgente"]
    assert [p.nombre for p in repos.personas.listar()] == ["ana", "Lucía"]


def test_crear_tarea_ignora_duplicados_sin_distinguir_mayusculas_y_conserva_la_primera() -> None:
    repos = _Repositorios()

    tarea = repos.crear().ejecutar(
        nombre="Leer",
        descripcion="Un libro",
        fecha_creacion=_FECHA_CREACION,
        etiquetas=["Urgente", "URGENTE", "urgente"],
        asignados=["Ana", "ana"],
    )

    assert tarea.etiquetas == ["Urgente"]
    assert tarea.asignados == ["Ana"]
    assert [e.nombre for e in repos.etiquetas.listar()] == ["Urgente"]
    assert [p.nombre for p in repos.personas.listar()] == ["Ana"]


def test_crear_tarea_reutiliza_el_catalogo_conservando_la_grafia_guardada() -> None:
    repos = _Repositorios(etiquetas=("Urgente",), personas=("Ana López",))

    tarea = repos.crear().ejecutar(
        nombre="Leer",
        descripcion="Un libro",
        fecha_creacion=_FECHA_CREACION,
        etiquetas=["URGENTE"],
        asignados=["ana lópez"],
    )

    assert tarea.etiquetas == ["Urgente"]
    assert tarea.asignados == ["Ana López"]
    assert [(e.id, e.nombre) for e in repos.etiquetas.listar()] == [(1, "Urgente")]
    assert [(p.id, p.nombre) for p in repos.personas.listar()] == [(1, "Ana López")]


def test_listar_tareas_devuelve_las_tareas_creadas_en_orden() -> None:
    repos = _Repositorios()
    primera = repos.crear().ejecutar(
        nombre="Uno", prioridad=1, descripcion="Primera", fecha_creacion=_FECHA_CREACION
    )
    segunda = repos.crear().ejecutar(
        nombre="Dos", prioridad=None, descripcion="Segunda", fecha_creacion=_FECHA_CREACION
    )

    assert ListarTareas(repos.tareas).ejecutar() == [primera, segunda]


def test_listar_tareas_sin_tareas_devuelve_lista_vacia() -> None:
    assert ListarTareas(RepositorioTareasFalso()).ejecutar() == []


def test_actualizar_tarea_sustituye_todos_sus_datos() -> None:
    repos = _Repositorios()
    creada = repos.crear().ejecutar(
        nombre="Uno",
        prioridad=1,
        descripcion="Primera",
        fecha_creacion=_FECHA_CREACION,
        fecha_vencimiento=_FECHA_VENCIMIENTO,
        etiquetas=["casa", "urgente"],
        asignados=["Ana"],
    )
    nueva_fecha = datetime(2026, 12, 1, 8, 0, 0)

    actualizada = repos.actualizar().ejecutar(
        creada.id,
        nombre="Uno editada",
        prioridad=None,
        descripcion="Primera editada",
        fecha_creacion=nueva_fecha,
        fecha_vencimiento=None,
        etiquetas=["Trabajo", "CASA"],
        asignados=[],
    )

    esperada = Tarea(
        id=creada.id,
        nombre="Uno editada",
        prioridad=None,
        descripcion="Primera editada",
        fecha_creacion=nueva_fecha,
        fecha_vencimiento=None,
        etiquetas=["casa", "Trabajo"],
        asignados=[],
    )
    assert actualizada == esperada
    assert repos.tareas.listar() == [esperada]
    assert [e.nombre for e in repos.etiquetas.listar()] == ["casa", "Trabajo", "urgente"]


def test_actualizar_tarea_sin_etiquetas_ni_asignados_los_vacia() -> None:
    repos = _Repositorios()
    creada = repos.crear().ejecutar(
        nombre="Uno",
        descripcion="Primera",
        fecha_creacion=_FECHA_CREACION,
        etiquetas=["casa"],
        asignados=["Ana"],
    )

    actualizada = repos.actualizar().ejecutar(
        creada.id, nombre="Uno", descripcion="Primera", fecha_creacion=_FECHA_CREACION
    )

    assert (actualizada.etiquetas, actualizada.asignados) == ([], [])
    assert repos.tareas.listar()[0].etiquetas == []


def test_actualizar_tarea_inexistente_lanza_entidad_no_encontrada() -> None:
    repos = _Repositorios()

    with pytest.raises(EntidadNoEncontradaError):
        repos.actualizar().ejecutar(
            99,
            nombre="X",
            prioridad=None,
            descripcion="Y",
            fecha_creacion=_FECHA_CREACION,
            etiquetas=["nueva"],
        )
    assert repos.tareas.listar() == []
    # La tarea no existe: no se da de alta ninguna etiqueta.
    assert repos.etiquetas.listar() == []


def test_crear_tarea_sin_tipo_la_guarda_sin_tipo_ni_oportunidad() -> None:
    repos = _Repositorios()

    tarea = repos.crear().ejecutar(
        nombre="Uno", descripcion="Primera", fecha_creacion=_FECHA_CREACION
    )

    assert (tarea.tipo, tarea.oportunidad) == (None, None)
    assert repos.tareas.listar() == [tarea]


def test_crear_tarea_de_tipo_oportunidad_guarda_sus_datos() -> None:
    repos = _Repositorios()
    oportunidad = Oportunidad(codigo="OP-1", descripcion="Venta", observaciones=None)

    tarea = repos.crear().ejecutar(
        nombre="Uno",
        descripcion="Primera",
        fecha_creacion=_FECHA_CREACION,
        tipo=TipoTarea.OPORTUNIDAD,
        oportunidad=oportunidad,
    )

    assert (tarea.tipo, tarea.oportunidad) == (TipoTarea.OPORTUNIDAD, oportunidad)
    assert repos.tareas.listar() == [tarea]


def test_actualizar_tarea_sustituye_los_datos_de_la_oportunidad() -> None:
    repos = _Repositorios()
    creada = repos.crear().ejecutar(
        nombre="Uno",
        descripcion="Primera",
        fecha_creacion=_FECHA_CREACION,
        tipo=TipoTarea.OPORTUNIDAD,
        oportunidad=Oportunidad(codigo="OP-1", descripcion="Venta", observaciones="Notas"),
    )
    nueva = Oportunidad(codigo="OP-2", descripcion=None, observaciones="Otras notas")

    actualizada = repos.actualizar().ejecutar(
        creada.id,
        nombre="Uno",
        descripcion="Primera",
        fecha_creacion=_FECHA_CREACION,
        tipo=TipoTarea.OPORTUNIDAD,
        oportunidad=nueva,
    )

    assert (actualizada.tipo, actualizada.oportunidad) == (TipoTarea.OPORTUNIDAD, nueva)
    assert repos.tareas.listar()[0].oportunidad == nueva


def test_actualizar_tarea_sin_tipo_quita_la_oportunidad() -> None:
    repos = _Repositorios()
    creada = repos.crear().ejecutar(
        nombre="Uno",
        descripcion="Primera",
        fecha_creacion=_FECHA_CREACION,
        tipo=TipoTarea.OPORTUNIDAD,
        oportunidad=Oportunidad(codigo="OP-1"),
    )

    actualizada = repos.actualizar().ejecutar(
        creada.id, nombre="Uno", descripcion="Primera", fecha_creacion=_FECHA_CREACION
    )

    assert (actualizada.tipo, actualizada.oportunidad) == (None, None)
    assert repos.tareas.listar()[0].oportunidad is None


def test_crear_tarea_la_guarda_pendiente() -> None:
    repos = _Repositorios()

    tarea = repos.crear().ejecutar(
        nombre="Uno", descripcion="Primera", fecha_creacion=_FECHA_CREACION
    )

    assert tarea.completada is False
    assert repos.tareas.listar()[0].completada is False


def test_marcar_completada_cambia_el_estado_y_lo_guarda() -> None:
    repos = _Repositorios()
    creada = repos.crear().ejecutar(
        nombre="Uno", descripcion="Primera", fecha_creacion=_FECHA_CREACION
    )

    completada = repos.marcar_completada().ejecutar(creada.id, completada=True)

    assert completada == Tarea(
        id=creada.id,
        nombre="Uno",
        descripcion="Primera",
        fecha_creacion=_FECHA_CREACION,
        completada=True,
    )
    assert repos.tareas.listar()[0].completada is True

    pendiente = repos.marcar_completada().ejecutar(creada.id, completada=False)

    assert pendiente.completada is False
    assert repos.tareas.listar()[0].completada is False


def test_marcar_completada_una_tarea_inexistente_lanza_entidad_no_encontrada() -> None:
    repos = _Repositorios()

    with pytest.raises(EntidadNoEncontradaError):
        repos.marcar_completada().ejecutar(99, completada=True)
    assert repos.tareas.listar() == []


def test_actualizar_tarea_conserva_el_estado_completada() -> None:
    repos = _Repositorios()
    creada = repos.crear().ejecutar(
        nombre="Uno", descripcion="Primera", fecha_creacion=_FECHA_CREACION
    )
    repos.marcar_completada().ejecutar(creada.id, completada=True)

    actualizada = repos.actualizar().ejecutar(
        creada.id, nombre="Otro", descripcion="Segunda", fecha_creacion=_FECHA_CREACION
    )

    assert actualizada.completada is True
    assert repos.tareas.listar()[0].completada is True


# --- Workflow de las tareas ------------------------------------------------------

_WORKFLOWS = {"Ventas": ["Contactar", "Proponer", "Cerrar"], "Compras": ["Pedir"], "Vacio": []}


def _crear(
    repos: _Repositorios,
    workflow: str | None = None,
    nombre: str = "Venta",
    oportunidad: bool = False,
) -> Tarea:
    return repos.crear().ejecutar(
        nombre=nombre,
        descripcion="d",
        fecha_creacion=_FECHA_CREACION,
        tipo=TipoTarea.OPORTUNIDAD if oportunidad else None,
        oportunidad=Oportunidad(codigo="OP-1") if oportunidad else None,
        workflow_id=repos.workflows.id_de(workflow) if workflow else None,
    )


def _editar(
    repos: _Repositorios,
    id_tarea: int,
    workflow: str | None = None,
    tipo: TipoTarea | None = None,
    workflow_id: int | None = None,
) -> Tarea:
    return repos.actualizar().ejecutar(
        id_tarea,
        nombre="Editada",
        descripcion="d",
        fecha_creacion=_FECHA_CREACION,
        tipo=tipo,
        oportunidad=Oportunidad(codigo="OP-2") if tipo is TipoTarea.OPORTUNIDAD else None,
        workflow_id=repos.workflows.id_de(workflow) if workflow else workflow_id,
    )


def _subtareas_sin_id(tarea: Tarea) -> list[tuple[str, str | None, int | None, bool]]:
    return [(s.nombre, s.asignado, s.prioridad, s.resuelta) for s in tarea.subtareas]


def _pendientes(*nombres: str) -> list[tuple[str, None, None, bool]]:
    return [(nombre, None, None, False) for nombre in nombres]


def _referencia(repos: _Repositorios, nombre: str) -> ReferenciaWorkflow:
    return ReferenciaWorkflow(id=repos.workflows.id_de(nombre), nombre=nombre)


def test_crear_una_tarea_con_workflow_le_crea_una_subtarea_por_paso_en_orden() -> None:
    repos = _Repositorios(workflows=_WORKFLOWS)
    # Los pasos se copian por número, aunque se hayan guardado en otro orden.
    repos.workflows.workflows[repos.workflows.id_de("Ventas")].pasos.reverse()

    tarea = _crear(repos, "Ventas")

    esperadas = _pendientes("Contactar", "Proponer", "Cerrar")
    assert _subtareas_sin_id(tarea) == esperadas
    assert [s.id for s in tarea.subtareas] == [1, 2, 3]
    assert tarea.workflow == _referencia(repos, "Ventas")
    guardada = repos.tareas.listar()[0]
    assert (_subtareas_sin_id(guardada), guardada.workflow) == (esperadas, tarea.workflow)
    assert repos.workflows.lecturas_para_copiar == [repos.workflows.id_de("Ventas")]


def test_crear_una_tarea_sin_workflow_no_le_crea_subtareas_ni_lee_workflows() -> None:
    repos = _Repositorios(workflows=_WORKFLOWS)

    tarea = _crear(repos)

    assert (tarea.subtareas, tarea.workflow) == ([], None)
    assert repos.workflows.lecturas_para_copiar == []


def test_el_tipo_oportunidad_por_si_solo_no_crea_subtareas() -> None:
    repos = _Repositorios(workflows={"Workflow Oportunidades": ["Contactar", "Cerrar"]})

    tarea = _crear(repos, oportunidad=True)

    assert (tarea.subtareas, tarea.workflow) == ([], None)
    assert repos.tareas.listar()[0].subtareas == []
    assert repos.workflows.lecturas_para_copiar == []


def test_crear_una_tarea_con_un_workflow_vacio_lo_asigna_sin_subtareas() -> None:
    repos = _Repositorios(workflows=_WORKFLOWS)

    tarea = _crear(repos, "Vacio")

    assert (tarea.subtareas, tarea.workflow) == ([], _referencia(repos, "Vacio"))


def test_crear_una_tarea_con_un_workflow_que_no_existe_no_la_guarda() -> None:
    repos = _Repositorios(workflows=_WORKFLOWS)

    with pytest.raises(AsignacionDeWorkflowInvalidaError, match="^No existe el workflow con id 9$"):
        repos.crear().ejecutar(
            nombre="T", descripcion="d", fecha_creacion=_FECHA_CREACION, workflow_id=9
        )

    assert repos.tareas.listar() == []


def test_las_subtareas_creadas_no_cambian_al_cambiar_el_workflow_despues() -> None:
    repos = _Repositorios(workflows=_WORKFLOWS)
    tarea = _crear(repos, "Ventas")

    pasos = repos.workflows.workflows[repos.workflows.id_de("Ventas")].pasos
    pasos[0].nombre = "Renombrado"
    pasos.pop()
    nueva = _crear(repos, "Ventas", nombre="Otra")

    guardada = repos.tareas.obtener_por_id(tarea.id)
    assert [s.nombre for s in guardada.subtareas] == ["Contactar", "Proponer", "Cerrar"]
    assert [s.nombre for s in nueva.subtareas] == ["Renombrado", "Proponer"]


def test_las_subtareas_del_workflow_se_resuelven_como_cualquier_subtarea() -> None:
    repos = _Repositorios(workflows=_WORKFLOWS)
    tarea = _crear(repos, "Ventas")

    resuelta = repos.resolver_subtarea().ejecutar(tarea.id, tarea.subtareas[1].id, True)

    assert [s.resuelta for s in resuelta.subtareas] == [False, True, False]


def test_editar_para_dar_un_workflow_anade_sus_pasos_tras_las_subtareas_que_tenia() -> None:
    repos = _Repositorios(workflows=_WORKFLOWS)
    tarea = _crear(repos, "Compras")
    repos.resolver_subtarea().ejecutar(tarea.id, tarea.subtareas[0].id, True)

    editada = _editar(repos, tarea.id, "Ventas")

    esperadas = [("Pedir", None, None, True), *_pendientes("Contactar", "Proponer", "Cerrar")]
    assert _subtareas_sin_id(editada) == esperadas
    assert [s.id for s in editada.subtareas] == [1, 2, 3, 4]
    assert editada.workflow == _referencia(repos, "Ventas")
    guardada = repos.tareas.obtener_por_id(tarea.id)
    assert (_subtareas_sin_id(guardada), guardada.workflow) == (esperadas, editada.workflow)


def test_editar_una_tarea_sin_workflow_para_darle_uno_anade_sus_pasos() -> None:
    repos = _Repositorios(workflows=_WORKFLOWS)
    tarea = _crear(repos)

    editada = _editar(repos, tarea.id, "Compras")

    assert _subtareas_sin_id(editada) == _pendientes("Pedir")
    assert editada.workflow == _referencia(repos, "Compras")


@pytest.mark.parametrize("tipo", [TipoTarea.OPORTUNIDAD, None])
def test_editar_con_el_mismo_workflow_no_toca_las_subtareas(tipo: TipoTarea | None) -> None:
    repos = _Repositorios(workflows=_WORKFLOWS)
    tarea = _crear(repos, "Ventas", oportunidad=True)
    repos.resolver_subtarea().ejecutar(tarea.id, tarea.subtareas[0].id, True)

    editada = _editar(repos, tarea.id, "Ventas", tipo=tipo)

    esperadas = [("Contactar", None, None, True), *_pendientes("Proponer", "Cerrar")]
    assert _subtareas_sin_id(editada) == esperadas
    assert _subtareas_sin_id(repos.tareas.obtener_por_id(tarea.id)) == esperadas
    assert editada.workflow == _referencia(repos, "Ventas")


def test_editar_sin_workflow_lo_quita_y_no_toca_las_subtareas() -> None:
    repos = _Repositorios(workflows=_WORKFLOWS)
    tarea = _crear(repos, "Ventas")

    editada = _editar(repos, tarea.id)

    assert _subtareas_sin_id(editada) == _pendientes("Contactar", "Proponer", "Cerrar")
    assert editada.workflow is None
    assert repos.tareas.obtener_por_id(tarea.id).workflow is None


def test_editar_una_tarea_para_hacerla_oportunidad_no_le_crea_subtareas() -> None:
    repos = _Repositorios(workflows=_WORKFLOWS)
    tarea = _crear(repos)

    editada = _editar(repos, tarea.id, tipo=TipoTarea.OPORTUNIDAD)

    assert editada.subtareas == []
    assert repos.tareas.obtener_por_id(tarea.id).subtareas == []
    assert repos.workflows.lecturas_para_copiar == []


def test_editar_con_un_workflow_que_no_existe_no_cambia_la_tarea() -> None:
    repos = _Repositorios(workflows=_WORKFLOWS)
    tarea = _crear(repos, "Ventas")

    with pytest.raises(AsignacionDeWorkflowInvalidaError, match="^No existe el workflow con id 9$"):
        _editar(repos, tarea.id, workflow_id=9)

    guardada = repos.tareas.obtener_por_id(tarea.id)
    assert (guardada.nombre, guardada.workflow) == ("Venta", _referencia(repos, "Ventas"))
    assert len(guardada.subtareas) == 3


def test_editar_una_tarea_que_no_existe_responde_que_no_existe_aunque_el_workflow_tampoco() -> None:
    repos = _Repositorios(workflows=_WORKFLOWS)

    with pytest.raises(EntidadNoEncontradaError, match="^No existe la tarea con id 99$"):
        _editar(repos, 99, workflow_id=9)


def test_subtarea_nueva_esta_pendiente_y_sin_comentarios() -> None:
    subtarea = Subtarea(nombre="Contactar")

    assert (subtarea.resuelta, subtarea.comentarios) == (False, 0)


# --- Borrar tareas --------------------------------------------------------------


def test_eliminar_una_tarea_la_borra_y_conserva_las_demas() -> None:
    repos = _Repositorios(workflows=_WORKFLOWS)
    borrada = _crear(repos, "Ventas")
    conservada = _crear(repos, "Ventas", nombre="Otra")

    assert repos.eliminar().ejecutar(borrada.id) is None

    assert repos.tareas.obtener_por_id(borrada.id) is None
    assert [t.id for t in repos.tareas.listar()] == [conservada.id]


def test_eliminar_una_tarea_que_no_existe_lanza_no_encontrada() -> None:
    repos = _Repositorios()
    existente = repos.crear().ejecutar(nombre="T", descripcion="d", fecha_creacion=_FECHA_CREACION)

    with pytest.raises(EntidadNoEncontradaError, match="^No existe la tarea con id 99$"):
        repos.eliminar().ejecutar(99)

    assert [t.id for t in repos.tareas.listar()] == [existente.id]
