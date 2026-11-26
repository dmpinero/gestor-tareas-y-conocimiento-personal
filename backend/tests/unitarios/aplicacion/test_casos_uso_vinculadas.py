"""Casos de uso de las tareas vinculadas: la relación es simétrica, sin tipos; se
quita en ambos sentidos y desaparece al borrar una de las tareas."""

from datetime import datetime

import pytest

from gestor_tareas.aplicacion.tarea.desvincular_tarea import DesvincularTarea
from gestor_tareas.aplicacion.tarea.eliminar_tarea import EliminarTarea
from gestor_tareas.aplicacion.tarea.vincular_tareas import VincularTareas
from gestor_tareas.dominio.excepciones import EntidadNoEncontradaError
from gestor_tareas.dominio.tarea.entidades import Tarea
from gestor_tareas.dominio.tarea.vinculos import VinculoInvalidoError
from tests.unitarios.aplicacion.dobles import RepositorioTareasFalso


def _repositorio_con_tareas(cuantas: int) -> RepositorioTareasFalso:
    repositorio = RepositorioTareasFalso()
    for numero in range(1, cuantas + 1):
        repositorio.crear(
            Tarea(nombre=f"T{numero}", descripcion="d", fecha_creacion=datetime(2026, 11, 26))
        )
    return repositorio


def _vinculadas(repositorio: RepositorioTareasFalso, id_tarea: int) -> list[int]:
    tarea = repositorio.obtener_por_id(id_tarea)
    assert tarea is not None
    return tarea.vinculadas


def test_vincular_varias_a_la_vez_es_simetrico_y_devuelve_la_tarea() -> None:
    repositorio = _repositorio_con_tareas(3)

    tarea = VincularTareas(repositorio).ejecutar(1, [3, 2])

    assert tarea.id == 1
    assert tarea.vinculadas == [2, 3]
    assert _vinculadas(repositorio, 2) == [1]
    assert _vinculadas(repositorio, 3) == [1]


def test_vincular_ignora_las_ya_vinculadas() -> None:
    repositorio = _repositorio_con_tareas(3)
    VincularTareas(repositorio).ejecutar(1, [2])

    tarea = VincularTareas(repositorio).ejecutar(1, [2, 3])

    assert tarea.vinculadas == [2, 3]
    assert _vinculadas(repositorio, 2) == [1]


def test_vincular_consigo_misma_no_cambia_nada() -> None:
    repositorio = _repositorio_con_tareas(2)

    with pytest.raises(VinculoInvalidoError):
        VincularTareas(repositorio).ejecutar(1, [1, 2])

    assert _vinculadas(repositorio, 1) == []
    assert _vinculadas(repositorio, 2) == []


def test_vincular_una_tarea_que_no_existe_lanza_no_encontrada() -> None:
    repositorio = _repositorio_con_tareas(1)

    with pytest.raises(EntidadNoEncontradaError):
        VincularTareas(repositorio).ejecutar(99, [1])


def test_vincular_con_un_id_que_no_existe_lanza_no_encontrada_sin_cambiar_nada() -> None:
    repositorio = _repositorio_con_tareas(2)

    with pytest.raises(EntidadNoEncontradaError):
        VincularTareas(repositorio).ejecutar(1, [2, 99])

    assert _vinculadas(repositorio, 1) == []
    assert _vinculadas(repositorio, 2) == []


def test_desvincular_quita_la_relacion_en_ambos_sentidos() -> None:
    repositorio = _repositorio_con_tareas(3)
    VincularTareas(repositorio).ejecutar(1, [2, 3])

    tarea = DesvincularTarea(repositorio).ejecutar(2, 1)

    assert tarea.id == 2
    assert tarea.vinculadas == []
    assert _vinculadas(repositorio, 1) == [3]


def test_desvincular_tareas_no_vinculadas_no_cambia_nada() -> None:
    repositorio = _repositorio_con_tareas(2)

    tarea = DesvincularTarea(repositorio).ejecutar(1, 2)

    assert tarea.vinculadas == []


@pytest.mark.parametrize(("id_tarea", "id_vinculada"), [(99, 1), (1, 99)])
def test_desvincular_con_una_tarea_que_no_existe_lanza_no_encontrada(
    id_tarea: int, id_vinculada: int
) -> None:
    repositorio = _repositorio_con_tareas(1)

    with pytest.raises(EntidadNoEncontradaError):
        DesvincularTarea(repositorio).ejecutar(id_tarea, id_vinculada)


def test_borrar_una_tarea_la_quita_de_las_vinculadas_de_las_demas() -> None:
    repositorio = _repositorio_con_tareas(3)
    VincularTareas(repositorio).ejecutar(1, [2, 3])

    EliminarTarea(repositorio).ejecutar(2)

    assert _vinculadas(repositorio, 1) == [3]
