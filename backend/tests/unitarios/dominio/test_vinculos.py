"""Vínculos entre tareas: una tarea se vincula con otras distintas de ella; los ids
repetidos cuentan una sola vez."""

import pytest

from gestor_tareas.dominio.tarea.vinculos import VinculoInvalidoError, ids_a_vincular


def test_devuelve_los_ids_sin_repetir_y_en_orden_ascendente() -> None:
    assert ids_a_vincular(1, [9, 3, 9, 5]) == [3, 5, 9]


def test_una_tarea_no_puede_vincularse_consigo_misma() -> None:
    with pytest.raises(VinculoInvalidoError, match="consigo misma"):
        ids_a_vincular(4, [2, 4])


def test_hay_que_indicar_al_menos_una_tarea() -> None:
    with pytest.raises(VinculoInvalidoError, match="al menos una"):
        ids_a_vincular(4, [])
