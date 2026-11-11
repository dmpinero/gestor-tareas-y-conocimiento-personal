from datetime import datetime

import pytest

from gestor_tareas.aplicacion.tarea.actualizar_tarea import ActualizarTarea
from gestor_tareas.aplicacion.tarea.crear_tarea import CrearTarea
from gestor_tareas.aplicacion.tarea.eliminar_tarea import EliminarTarea
from gestor_tareas.aplicacion.tarea.listar_tareas import ListarTareas
from gestor_tareas.aplicacion.tarea.marcar_completada import MarcarCompletada
from gestor_tareas.aplicacion.tarea.marcar_subtarea_resuelta import MarcarSubtareaResuelta
from gestor_tareas.dominio.excepciones import EntidadNoEncontradaError
from gestor_tareas.dominio.tarea.entidades import Oportunidad, Subtarea, Tarea, TipoTarea
from tests.unitarios.aplicacion.dobles import (
    RepositorioEtiquetasFalso,
    RepositorioGruposEstadosFalso,
    RepositorioPersonasFalso,
    RepositorioTareasFalso,
    RepositorioWorkflowOportunidadesFalso,
)

_FECHA_CREACION = datetime(2026, 11, 9, 10, 30, 0)
_FECHA_VENCIMIENTO = datetime(2026, 11, 20, 18, 0, 0)


class _Repositorios:
    def __init__(
        self,
        etiquetas: tuple[str, ...] = (),
        personas: tuple[str, ...] = (),
        workflow: tuple[str, ...] = (),
        grupos: dict[str, list[str]] | None = None,
    ) -> None:
        self.tareas = RepositorioTareasFalso()
        self.etiquetas = RepositorioEtiquetasFalso(*etiquetas)
        self.personas = RepositorioPersonasFalso(*personas)
        self.workflow = RepositorioWorkflowOportunidadesFalso(*workflow)
        self.grupos = RepositorioGruposEstadosFalso(**(grupos or {}))

    def crear(self) -> CrearTarea:
        return CrearTarea(self.tareas, self.etiquetas, self.personas, self.workflow, self.grupos)

    def actualizar(self) -> ActualizarTarea:
        return ActualizarTarea(self.tareas, self.etiquetas, self.personas, self.grupos)

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


# --- Subtareas del workflow de las oportunidades ---------------------------------

_WORKFLOW = ("Contactar", "Proponer", "Cerrar")


def _crear_oportunidad(repos: _Repositorios, nombre: str = "Venta") -> Tarea:
    return repos.crear().ejecutar(
        nombre=nombre,
        descripcion="d",
        fecha_creacion=_FECHA_CREACION,
        tipo=TipoTarea.OPORTUNIDAD,
        oportunidad=Oportunidad(codigo="OP-1"),
    )


def _editar(repos: _Repositorios, id_tarea: int, tipo: TipoTarea | None) -> Tarea:
    return repos.actualizar().ejecutar(
        id_tarea,
        nombre="Editada",
        descripcion="d",
        fecha_creacion=_FECHA_CREACION,
        tipo=tipo,
        oportunidad=Oportunidad(codigo="OP-2") if tipo is TipoTarea.OPORTUNIDAD else None,
    )


def _subtareas_sin_id(tarea: Tarea) -> list[tuple[str, str | None, int | None, bool]]:
    return [(s.nombre, s.asignado, s.prioridad, s.resuelta) for s in tarea.subtareas]


def _pendientes(*nombres: str) -> list[tuple[str, None, None, bool]]:
    return [(nombre, None, None, False) for nombre in nombres]


def test_crear_una_oportunidad_le_crea_una_subtarea_por_paso_del_workflow_en_orden() -> None:
    repos = _Repositorios(workflow=_WORKFLOW)
    # El workflow se lee por número, aunque se haya guardado en otro orden.
    repos.workflow.pasos.reverse()

    tarea = _crear_oportunidad(repos)

    esperadas = _pendientes("Contactar", "Proponer", "Cerrar")
    assert _subtareas_sin_id(tarea) == esperadas
    assert [s.id for s in tarea.subtareas] == [1, 2, 3]
    assert _subtareas_sin_id(repos.tareas.listar()[0]) == esperadas
    assert repos.workflow.lecturas_para_copiar == 1


def test_crear_una_tarea_sin_tipo_no_le_crea_subtareas_ni_lee_el_workflow() -> None:
    repos = _Repositorios(workflow=_WORKFLOW)

    tarea = repos.crear().ejecutar(nombre="T", descripcion="d", fecha_creacion=_FECHA_CREACION)

    assert tarea.subtareas == []
    assert repos.workflow.lecturas_para_copiar == 0


def test_crear_una_oportunidad_con_el_workflow_vacio_no_le_crea_subtareas() -> None:
    repos = _Repositorios()

    assert _crear_oportunidad(repos).subtareas == []


def test_las_subtareas_creadas_no_cambian_al_cambiar_el_workflow_despues() -> None:
    repos = _Repositorios(workflow=_WORKFLOW)
    tarea = _crear_oportunidad(repos)

    repos.workflow.pasos[0].nombre = "Renombrado"
    repos.workflow.pasos.pop()
    nueva = _crear_oportunidad(repos, "Otra")

    guardada = repos.tareas.obtener_por_id(tarea.id)
    assert [s.nombre for s in guardada.subtareas] == ["Contactar", "Proponer", "Cerrar"]
    assert [s.nombre for s in nueva.subtareas] == ["Renombrado", "Proponer"]


def test_las_subtareas_del_workflow_se_resuelven_como_cualquier_subtarea() -> None:
    repos = _Repositorios(workflow=_WORKFLOW)
    tarea = _crear_oportunidad(repos)

    resuelta = repos.resolver_subtarea().ejecutar(tarea.id, tarea.subtareas[1].id, True)

    assert [s.resuelta for s in resuelta.subtareas] == [False, True, False]


@pytest.mark.parametrize("tipo", [TipoTarea.OPORTUNIDAD, None])
def test_editar_una_oportunidad_conserva_sus_subtareas_aunque_cambie_el_tipo(
    tipo: TipoTarea | None,
) -> None:
    repos = _Repositorios(workflow=_WORKFLOW)
    tarea = _crear_oportunidad(repos)
    repos.resolver_subtarea().ejecutar(tarea.id, tarea.subtareas[0].id, True)

    editada = _editar(repos, tarea.id, tipo)

    esperadas = [("Contactar", None, None, True), *_pendientes("Proponer", "Cerrar")]
    assert _subtareas_sin_id(editada) == esperadas
    assert _subtareas_sin_id(repos.tareas.obtener_por_id(tarea.id)) == esperadas


def test_editar_una_tarea_para_hacerla_oportunidad_no_le_crea_subtareas() -> None:
    repos = _Repositorios(workflow=_WORKFLOW)
    tarea = repos.crear().ejecutar(nombre="T", descripcion="d", fecha_creacion=_FECHA_CREACION)

    editada = _editar(repos, tarea.id, TipoTarea.OPORTUNIDAD)

    assert editada.subtareas == []
    assert repos.tareas.obtener_por_id(tarea.id).subtareas == []
    assert repos.workflow.lecturas_para_copiar == 0


def test_subtarea_nueva_esta_pendiente_y_sin_comentarios() -> None:
    subtarea = Subtarea(nombre="Contactar")

    assert (subtarea.resuelta, subtarea.comentarios) == (False, 0)


# --- Borrar tareas --------------------------------------------------------------


def test_eliminar_una_tarea_la_borra_y_conserva_las_demas() -> None:
    repos = _Repositorios(workflow=_WORKFLOW)
    borrada = _crear_oportunidad(repos, "Venta")
    conservada = _crear_oportunidad(repos, "Otra")

    assert repos.eliminar().ejecutar(borrada.id) is None

    assert repos.tareas.obtener_por_id(borrada.id) is None
    assert [t.id for t in repos.tareas.listar()] == [conservada.id]


def test_eliminar_una_tarea_que_no_existe_lanza_no_encontrada() -> None:
    repos = _Repositorios()
    existente = repos.crear().ejecutar(nombre="T", descripcion="d", fecha_creacion=_FECHA_CREACION)

    with pytest.raises(EntidadNoEncontradaError, match="^No existe la tarea con id 99$"):
        repos.eliminar().ejecutar(99)

    assert [t.id for t in repos.tareas.listar()] == [existente.id]
