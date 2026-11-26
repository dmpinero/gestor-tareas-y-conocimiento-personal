"""La protección que impide lanzar los tests que vacían la base de datos sin permiso."""

from pathlib import Path

import pytest

from tests.conftest import VARIABLE_BD_DESECHABLE, exigir_bd_desechable

RAIZ = Path(__file__).resolve().parent.parent


@pytest.mark.parametrize("carpeta", ["integracion", "bdd", "contrato"])
def test_sin_permiso_se_niega_a_lanzar_tests_que_tocan_la_base(carpeta: str) -> None:
    rutas = [RAIZ / "unitarios" / "test_algo.py", RAIZ / carpeta / "test_bd.py"]

    with pytest.raises(pytest.UsageError) as error:
        exigir_bd_desechable(rutas, entorno={})

    mensaje = str(error.value)
    assert VARIABLE_BD_DESECHABLE in mensaje
    assert "vacían" in mensaje


def test_con_permiso_deja_lanzar_los_tests_que_tocan_la_base() -> None:
    rutas = [RAIZ / "integracion" / "test_bd.py"]

    exigir_bd_desechable(rutas, entorno={VARIABLE_BD_DESECHABLE: "1"})


def test_un_valor_distinto_de_1_no_cuenta_como_permiso() -> None:
    with pytest.raises(pytest.UsageError):
        exigir_bd_desechable([RAIZ / "bdd" / "test_bd.py"], entorno={VARIABLE_BD_DESECHABLE: "0"})


def test_los_unitarios_no_necesitan_permiso() -> None:
    exigir_bd_desechable([RAIZ / "unitarios" / "test_algo.py"], entorno={})
