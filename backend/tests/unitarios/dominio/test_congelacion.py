from datetime import UTC, datetime

import pytest

from gestor_tareas.dominio.tarea.congelacion import (
    es_estado_terminado,
    esta_congelada,
    instante_de_congelacion,
)

_ANTES = datetime(2026, 11, 1, 8, 0, 0, tzinfo=UTC)
_AHORA = datetime(2026, 11, 17, 12, 30, 5, tzinfo=UTC)


@pytest.mark.parametrize("nombre", ["DONE", "done", "Done"])
def test_el_estado_done_se_reconoce_sin_distinguir_mayusculas(nombre: str) -> None:
    assert es_estado_terminado(nombre) is True


@pytest.mark.parametrize("nombre", [None, "DOING", "Hecha", "DONE ", "UNDONE"])
def test_otros_estados_no_son_done(nombre: str | None) -> None:
    assert es_estado_terminado(nombre) is False


@pytest.mark.parametrize(
    ("completada", "estado", "congelada"),
    [
        (False, None, False),
        (False, "TODO", False),
        (True, None, True),
        (True, "TODO", True),
        (False, "DONE", True),
        (True, "DONE", True),
    ],
)
def test_esta_congelada_si_esta_completada_o_en_done(
    completada: bool, estado: str | None, congelada: bool
) -> None:
    assert esta_congelada(completada, estado) is congelada


def test_al_congelarse_toma_el_instante_del_cambio() -> None:
    assert instante_de_congelacion(None, True, None, _AHORA) == _AHORA
    assert instante_de_congelacion(None, False, "DONE", _AHORA) == _AHORA


@pytest.mark.parametrize(("completada", "estado"), [(True, None), (False, "DONE"), (True, "DONE")])
def test_si_ya_estaba_congelada_conserva_su_instante(completada: bool, estado: str | None) -> None:
    assert instante_de_congelacion(_ANTES, completada, estado, _AHORA) == _ANTES


@pytest.mark.parametrize("anterior", [None, _ANTES])
def test_al_dejar_de_estar_completada_y_en_done_se_borra_el_instante(
    anterior: datetime | None,
) -> None:
    assert instante_de_congelacion(anterior, False, "DOING", _AHORA) is None
    assert instante_de_congelacion(anterior, False, None, _AHORA) is None
