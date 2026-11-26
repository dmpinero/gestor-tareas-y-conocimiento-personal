"""Reglas de la cola de siguientes tareas: qué tareas admite y cómo se reordena."""

import pytest

from gestor_tareas.dominio.siguientes.reglas import (
    EntradaDeLaCola,
    OrdenDeLaColaInvalidoError,
    TareaCompletadaEnLaColaError,
    comprobar_que_se_puede_anadir,
    nuevo_orden_de_la_cola,
)


def _cola(*entradas: tuple[int, bool]) -> list[EntradaDeLaCola]:
    return [EntradaDeLaCola(tarea_id=i, completada=c) for i, c in entradas]


def test_una_tarea_pendiente_se_puede_anadir() -> None:
    comprobar_que_se_puede_anadir(completada=False)


def test_una_tarea_completada_no_se_puede_anadir() -> None:
    with pytest.raises(TareaCompletadaEnLaColaError, match="completada"):
        comprobar_que_se_puede_anadir(completada=True)


def test_reordenar_con_las_visibles_en_otro_orden() -> None:
    cola = _cola((1, False), (2, False), (3, False))

    assert nuevo_orden_de_la_cola(cola, [3, 1, 2]) == [3, 1, 2]


def test_reordenar_deja_las_completadas_detras_en_su_orden() -> None:
    cola = _cola((1, False), (2, True), (3, False), (4, True))

    assert nuevo_orden_de_la_cola(cola, [3, 1]) == [3, 1, 2, 4]


def test_reordenar_una_cola_vacia_con_ninguna() -> None:
    assert nuevo_orden_de_la_cola([], []) == []


@pytest.mark.parametrize(
    "ids",
    [
        pytest.param([1], id="falta una"),
        pytest.param([1, 2, 5], id="sobra una que no esta en la cola"),
        pytest.param([1, 2, 2], id="repite una"),
        pytest.param([1, 2, 3], id="incluye una completada"),
        pytest.param([], id="ninguna"),
    ],
)
def test_reordenar_con_ids_que_no_son_la_cola_visible_falla(ids: list[int]) -> None:
    cola = _cola((1, False), (2, False), (3, True))

    with pytest.raises(OrdenDeLaColaInvalidoError):
        nuevo_orden_de_la_cola(cola, ids)
