import re

import pytest
from pydantic import ValidationError

from gestor_tareas.dominio.codigo_servicio.entidades import ESPACIOS_ECMA
from gestor_tareas.interfaces.api.v1.esquemas.catalogos import CodigoServicioEsquema
from gestor_tareas.main import crear_aplicacion


def _patron_publicado() -> str:
    esquemas = crear_aplicacion().openapi()["components"]["schemas"]
    return esquemas["CodigoServicioEsquema"]["properties"]["nombre"]["pattern"]


def _cumple_patron_ecma(patron: str, valor: str) -> bool:
    """Evalúa el `pattern` como lo haría un validador ECMA-262 (el del contrato):
    `\\s` son exactamente los espacios de ECMA, no los de Python."""
    clase = re.escape(ESPACIOS_ECMA)
    traducido = patron.replace(r"\S", f"[^{clase}]").replace(r"\s", f"[{clase}]")
    return re.search(traducido, valor) is not None


# La API recorta los espacios de los extremos antes de validar: lo que acepta
# tiene que cumplir el `pattern` publicado, y lo que rechaza (espacios dentro o
# una longitud fuera de 2–20 tras recortar), no.
@pytest.mark.parametrize(
    "nombre",
    ["AXAS0024", "AB\v", " AB ", "\u3000AXAS0024\t", "A" * 20, " " + "A" * 20 + " "],
)
def test_el_patron_publicado_acepta_lo_que_la_api_acepta(nombre):
    CodigoServicioEsquema(nombre=nombre)

    assert _cumple_patron_ecma(_patron_publicado(), nombre)


@pytest.mark.parametrize("nombre", ["AX AS", "AB\u00a0CD", "0 ", " A ", "A" * 21, " " + "A" * 21])
def test_el_patron_publicado_rechaza_lo_que_la_api_rechaza(nombre):
    with pytest.raises(ValidationError):
        CodigoServicioEsquema(nombre=nombre)

    assert not _cumple_patron_ecma(_patron_publicado(), nombre)
