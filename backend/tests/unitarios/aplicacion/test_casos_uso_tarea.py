from gestor_tareas.aplicacion.tarea.crear_tarea import CrearTarea
from gestor_tareas.aplicacion.tarea.listar_tareas import ListarTareas
from gestor_tareas.dominio.tarea.entidades import Tarea
from tests.unitarios.aplicacion.dobles import RepositorioTareasFalso


def test_crear_tarea_la_guarda_y_le_asigna_id() -> None:
    repo = RepositorioTareasFalso()

    tarea = CrearTarea(repo).ejecutar(
        nombre="Preparar informe", prioridad=2, descripcion="Informe trimestral"
    )

    assert tarea == Tarea(
        id=1, nombre="Preparar informe", prioridad=2, descripcion="Informe trimestral"
    )
    assert repo.listar() == [tarea]


def test_crear_tarea_sin_prioridad_la_guarda_con_prioridad_nula() -> None:
    repo = RepositorioTareasFalso()

    tarea = CrearTarea(repo).ejecutar(nombre="Leer", prioridad=None, descripcion="Un libro")

    assert tarea.prioridad is None
    assert repo.listar() == [tarea]


def test_listar_tareas_devuelve_las_tareas_creadas_en_orden() -> None:
    repo = RepositorioTareasFalso()
    primera = CrearTarea(repo).ejecutar(nombre="Uno", prioridad=1, descripcion="Primera")
    segunda = CrearTarea(repo).ejecutar(nombre="Dos", prioridad=None, descripcion="Segunda")

    assert ListarTareas(repo).ejecutar() == [primera, segunda]


def test_listar_tareas_sin_tareas_devuelve_lista_vacia() -> None:
    assert ListarTareas(RepositorioTareasFalso()).ejecutar() == []
