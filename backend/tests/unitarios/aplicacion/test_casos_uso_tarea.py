from datetime import datetime

import pytest

from gestor_tareas.aplicacion.tarea.actualizar_tarea import ActualizarTarea
from gestor_tareas.aplicacion.tarea.crear_tarea import CrearTarea
from gestor_tareas.aplicacion.tarea.listar_tareas import ListarTareas
from gestor_tareas.dominio.excepciones import EntidadNoEncontradaError
from gestor_tareas.dominio.tarea.entidades import Tarea
from tests.unitarios.aplicacion.dobles import RepositorioTareasFalso

_FECHA_HORA = datetime(2026, 11, 9, 10, 30, 0)


def test_crear_tarea_la_guarda_y_le_asigna_id() -> None:
    repo = RepositorioTareasFalso()

    tarea = CrearTarea(repo).ejecutar(
        nombre="Preparar informe",
        prioridad=2,
        descripcion="Informe trimestral",
        fecha_hora=_FECHA_HORA,
    )

    assert tarea == Tarea(
        id=1,
        nombre="Preparar informe",
        prioridad=2,
        descripcion="Informe trimestral",
        fecha_hora=_FECHA_HORA,
    )
    assert repo.listar() == [tarea]


def test_crear_tarea_sin_prioridad_la_guarda_con_prioridad_nula() -> None:
    repo = RepositorioTareasFalso()

    tarea = CrearTarea(repo).ejecutar(
        nombre="Leer", prioridad=None, descripcion="Un libro", fecha_hora=_FECHA_HORA
    )

    assert tarea.prioridad is None
    assert repo.listar() == [tarea]


def test_listar_tareas_devuelve_las_tareas_creadas_en_orden() -> None:
    repo = RepositorioTareasFalso()
    primera = CrearTarea(repo).ejecutar(
        nombre="Uno", prioridad=1, descripcion="Primera", fecha_hora=_FECHA_HORA
    )
    segunda = CrearTarea(repo).ejecutar(
        nombre="Dos", prioridad=None, descripcion="Segunda", fecha_hora=_FECHA_HORA
    )

    assert ListarTareas(repo).ejecutar() == [primera, segunda]


def test_listar_tareas_sin_tareas_devuelve_lista_vacia() -> None:
    assert ListarTareas(RepositorioTareasFalso()).ejecutar() == []


def test_actualizar_tarea_sustituye_todos_sus_datos() -> None:
    repo = RepositorioTareasFalso()
    creada = CrearTarea(repo).ejecutar(
        nombre="Uno", prioridad=1, descripcion="Primera", fecha_hora=_FECHA_HORA
    )
    nueva_fecha_hora = datetime(2026, 12, 1, 8, 0, 0)

    actualizada = ActualizarTarea(repo).ejecutar(
        creada.id,
        nombre="Uno editada",
        prioridad=None,
        descripcion="Primera editada",
        fecha_hora=nueva_fecha_hora,
    )

    esperada = Tarea(
        id=creada.id,
        nombre="Uno editada",
        prioridad=None,
        descripcion="Primera editada",
        fecha_hora=nueva_fecha_hora,
    )
    assert actualizada == esperada
    assert repo.listar() == [esperada]


def test_actualizar_tarea_inexistente_lanza_entidad_no_encontrada() -> None:
    repo = RepositorioTareasFalso()

    with pytest.raises(EntidadNoEncontradaError):
        ActualizarTarea(repo).ejecutar(
            99, nombre="X", prioridad=None, descripcion="Y", fecha_hora=_FECHA_HORA
        )
    assert repo.listar() == []
