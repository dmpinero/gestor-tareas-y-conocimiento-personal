"""Reglas de la cola de siguientes tareas: qué entradas (tareas o subtareas) admite y
cómo se reordena."""

import pytest

from gestor_tareas.dominio.siguientes.entidades import ClaveDeEntrada, Lista
from gestor_tareas.dominio.siguientes.reglas import (
    EntradaDeLaCola,
    OrdenDeLaColaInvalidoError,
    SubtareaResueltaEnLaColaError,
    TareaCompletadaEnLaColaError,
    comprobar_que_se_puede_anadir,
    nuevo_orden_de_la_cola,
)


def _cola(*entradas: tuple[int, bool]) -> list[EntradaDeLaCola]:
    return [EntradaDeLaCola(tarea_id=i, completada=c) for i, c in entradas]


def _claves(*ids: int) -> list[ClaveDeEntrada]:
    return [ClaveDeEntrada(i) for i in ids]


def test_una_tarea_pendiente_se_puede_anadir() -> None:
    comprobar_que_se_puede_anadir(completada=False)


def test_una_tarea_completada_no_se_puede_anadir() -> None:
    with pytest.raises(TareaCompletadaEnLaColaError, match="completada"):
        comprobar_que_se_puede_anadir(completada=True)


def test_una_subtarea_pendiente_de_una_tarea_pendiente_se_puede_anadir() -> None:
    comprobar_que_se_puede_anadir(completada=False, resuelta=False)


def test_una_subtarea_resuelta_no_se_puede_anadir() -> None:
    with pytest.raises(SubtareaResueltaEnLaColaError, match="resuelta"):
        comprobar_que_se_puede_anadir(completada=False, resuelta=True)


def test_una_subtarea_de_una_tarea_completada_no_se_puede_anadir() -> None:
    with pytest.raises(TareaCompletadaEnLaColaError, match="completada"):
        comprobar_que_se_puede_anadir(completada=True, resuelta=False)


def test_la_clave_de_una_tarea_entera_no_tiene_subtarea() -> None:
    assert ClaveDeEntrada(3) == ClaveDeEntrada(3, None) == (3, None)
    assert ClaveDeEntrada(3) != ClaveDeEntrada(3, 7)


def test_la_entrada_dice_su_clave() -> None:
    assert EntradaDeLaCola(tarea_id=3, completada=False).clave == ClaveDeEntrada(3)
    assert EntradaDeLaCola(3, False, subtarea_id=7).clave == ClaveDeEntrada(3, 7)


def test_reordenar_con_las_visibles_en_otro_orden() -> None:
    cola = _cola((1, False), (2, False), (3, False))

    assert nuevo_orden_de_la_cola(cola, _claves(3, 1, 2)) == _claves(3, 1, 2)


def test_reordenar_deja_las_completadas_detras_en_su_orden() -> None:
    cola = _cola((1, False), (2, True), (3, False), (4, True))

    assert nuevo_orden_de_la_cola(cola, _claves(3, 1)) == _claves(3, 1, 2, 4)


def test_reordenar_una_cola_vacia_con_ninguna() -> None:
    assert nuevo_orden_de_la_cola([], []) == []


def test_reordenar_una_tarea_y_una_subtarea_suya_por_separado() -> None:
    cola = [
        EntradaDeLaCola(1, False),
        EntradaDeLaCola(1, False, subtarea_id=10),
        EntradaDeLaCola(2, False, subtarea_id=20),
        EntradaDeLaCola(1, True, subtarea_id=11),
    ]
    orden = [ClaveDeEntrada(2, 20), ClaveDeEntrada(1), ClaveDeEntrada(1, 10)]

    assert nuevo_orden_de_la_cola(cola, orden) == [*orden, ClaveDeEntrada(1, 11)]


@pytest.mark.parametrize(
    "claves",
    [
        pytest.param(_claves(1), id="falta una"),
        pytest.param(_claves(1, 2, 5), id="sobra una que no esta en la cola"),
        pytest.param(_claves(1, 2, 2), id="repite una"),
        pytest.param(_claves(1, 2, 3), id="incluye una completada"),
        pytest.param([], id="ninguna"),
        pytest.param([ClaveDeEntrada(1), ClaveDeEntrada(2, 9)], id="subtarea en vez de tarea"),
    ],
)
def test_reordenar_con_claves_que_no_son_la_cola_visible_falla(
    claves: list[ClaveDeEntrada],
) -> None:
    cola = _cola((1, False), (2, False), (3, True))

    with pytest.raises(OrdenDeLaColaInvalidoError):
        nuevo_orden_de_la_cola(cola, claves)


def test_hay_dos_listas_siguientes_y_sugerencias_con_su_valor_guardado() -> None:
    assert [lista.value for lista in Lista] == ["siguientes", "sugerencias"]
