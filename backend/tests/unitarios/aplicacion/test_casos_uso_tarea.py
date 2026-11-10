from datetime import datetime

import pytest

from gestor_tareas.aplicacion.tarea.actualizar_tarea import ActualizarTarea
from gestor_tareas.aplicacion.tarea.crear_tarea import CrearTarea
from gestor_tareas.aplicacion.tarea.listar_tareas import ListarTareas
from gestor_tareas.dominio.excepciones import EntidadNoEncontradaError
from gestor_tareas.dominio.tarea.entidades import Oportunidad, Tarea, TipoTarea
from tests.unitarios.aplicacion.dobles import (
    RepositorioEtiquetasFalso,
    RepositorioPersonasFalso,
    RepositorioTareasFalso,
)

_FECHA_CREACION = datetime(2026, 11, 9, 10, 30, 0)
_FECHA_VENCIMIENTO = datetime(2026, 11, 20, 18, 0, 0)


class _Repositorios:
    def __init__(self, etiquetas: tuple[str, ...] = (), personas: tuple[str, ...] = ()) -> None:
        self.tareas = RepositorioTareasFalso()
        self.etiquetas = RepositorioEtiquetasFalso(*etiquetas)
        self.personas = RepositorioPersonasFalso(*personas)

    def crear(self) -> CrearTarea:
        return CrearTarea(self.tareas, self.etiquetas, self.personas)

    def actualizar(self) -> ActualizarTarea:
        return ActualizarTarea(self.tareas, self.etiquetas, self.personas)


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
