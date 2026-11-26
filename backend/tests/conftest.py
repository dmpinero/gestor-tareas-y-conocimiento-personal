"""Protección de la base de datos real frente a los tests.

Los tests de integración, BDD y contrato vacían todas las tablas de la base a la
que apunta ``URL_BASE_DATOS``, que por defecto es ``localhost:3306``: la de
``docker compose``, con los datos reales. Solo se lanzan si la variable
``GESTOR_TESTS_BD_DESECHABLE=1`` confirma que esa base es desechable (el CI la
define; en local, solo con una base aislada).
"""

import os
from collections.abc import Iterable, Mapping
from pathlib import Path

import pytest

VARIABLE_BD_DESECHABLE = "GESTOR_TESTS_BD_DESECHABLE"
CARPETAS_CON_BD = frozenset({"integracion", "bdd", "contrato"})
RAIZ_TESTS = Path(__file__).resolve().parent


def exigir_bd_desechable(rutas: Iterable[Path], entorno: Mapping[str, str]) -> None:
    """Falla si hay tests que tocan la base y no se ha confirmado que sea desechable."""
    if entorno.get(VARIABLE_BD_DESECHABLE) == "1":
        return
    con_bd = sorted(
        {
            ruta.relative_to(RAIZ_TESTS).parts[0]
            for ruta in rutas
            if ruta.is_relative_to(RAIZ_TESTS)
            and ruta.relative_to(RAIZ_TESTS).parts[0] in CARPETAS_CON_BD
        }
    )
    if con_bd:
        raise pytest.UsageError(
            f"Los tests de {', '.join(con_bd)} vacían todas las tablas de la base de "
            f"URL_BASE_DATOS (por defecto, la de docker compose con los datos reales). "
            f"Apunta URL_BASE_DATOS a una base aislada y define {VARIABLE_BD_DESECHABLE}=1, "
            f"o lanza solo tests/unitarios."
        )


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    exigir_bd_desechable((item.path for item in items), os.environ)
