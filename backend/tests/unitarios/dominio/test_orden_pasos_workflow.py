import pytest

from gestor_tareas.dominio.excepciones import OrdenDePasosInvalidoError
from gestor_tareas.dominio.workflow_oportunidades.orden import comprobar_nuevo_orden


@pytest.mark.parametrize(
    ("actuales", "nuevos"),
    [([], []), ([1], [1]), ([1, 2, 3], [3, 1, 2]), ([7, 4], [4, 7])],
)
def test_admite_cualquier_permutacion_de_los_pasos_actuales(actuales, nuevos) -> None:
    comprobar_nuevo_orden(actuales, nuevos)


@pytest.mark.parametrize(
    ("nuevos", "motivo"),
    [
        ([1, 2, 2, 3], "repetidos: 2"),
        ([1, 2], "faltan: 3"),
        ([1, 2, 3, 9], "no existen: 9"),
        ([1, 2, 9], "faltan: 3"),
        ([], "faltan: 1, 2, 3"),
    ],
)
def test_rechaza_lo_que_no_es_una_permutacion_exacta(nuevos, motivo) -> None:
    with pytest.raises(OrdenDePasosInvalidoError, match=motivo):
        comprobar_nuevo_orden([1, 2, 3], nuevos)


def test_con_varios_problemas_los_indica_todos() -> None:
    with pytest.raises(OrdenDePasosInvalidoError) as error:
        comprobar_nuevo_orden([1, 2, 3], [1, 1, 9])

    assert str(error.value) == (
        "El nuevo orden debe incluir cada paso del workflow exactamente una vez "
        "(repetidos: 1; faltan: 2, 3; no existen: 9)"
    )
