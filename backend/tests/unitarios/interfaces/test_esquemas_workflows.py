import pytest
from pydantic import ValidationError

from gestor_tareas.interfaces.api.v1.esquemas.workflows import (
    OrdenPasosEsquema,
    PasoWorkflowEsquema,
    WorkflowEsquema,
)

# El nombre del workflow y el de sus pasos siguen las mismas reglas.
_ESQUEMAS_CON_NOMBRE = pytest.mark.parametrize("esquema", [PasoWorkflowEsquema, WorkflowEsquema])


@_ESQUEMAS_CON_NOMBRE
@pytest.mark.parametrize(
    ("nombre", "esperado"),
    [
        ("Contacto inicial", "Contacto inicial"),
        ("  Propuesta \t", "Propuesta"),
        (" Cierre　", "Cierre"),
        ("n" * 50, "n" * 50),
        (" " + "n" * 50 + " ", "n" * 50),
        ("x", "x"),
    ],
)
def test_el_nombre_se_recorta_y_admite_de_1_a_50_caracteres(esquema, nombre, esperado) -> None:
    assert esquema(nombre=nombre).nombre == esperado


@_ESQUEMAS_CON_NOMBRE
@pytest.mark.parametrize("nombre", ["", "   ", "   ", "n" * 51, None, 5])
def test_el_nombre_es_obligatorio_y_de_como_mucho_50_caracteres(esquema, nombre) -> None:
    with pytest.raises(ValidationError):
        esquema(nombre=nombre)


@_ESQUEMAS_CON_NOMBRE
def test_el_nombre_es_obligatorio(esquema) -> None:
    with pytest.raises(ValidationError):
        esquema.model_validate({})


@_ESQUEMAS_CON_NOMBRE
def test_el_contrato_publica_los_limites_del_nombre(esquema) -> None:
    propiedad = esquema.model_json_schema()["properties"]["nombre"]

    assert propiedad["minLength"] == 1
    assert propiedad["maxLength"] == 50
    assert propiedad["pattern"] == r"\S"


@pytest.mark.parametrize(
    ("ids", "esperado"), [([], []), ([3, 1, 2], [3, 1, 2]), ([2.0, 1], [2, 1])]
)
def test_el_orden_admite_una_lista_de_ids_enteros_distintos(ids, esperado) -> None:
    assert OrdenPasosEsquema(ids=ids).ids == esperado


@pytest.mark.parametrize("ids", [[1, 1], [True, 2], ["1", 2], [1.5], None, "1,2", [None], [[1]]])
def test_el_orden_rechaza_ids_repetidos_o_que_no_son_enteros(ids) -> None:
    with pytest.raises(ValidationError):
        OrdenPasosEsquema(ids=ids)


def test_el_orden_es_obligatorio_y_el_contrato_publica_que_los_ids_no_se_repiten() -> None:
    with pytest.raises(ValidationError):
        OrdenPasosEsquema.model_validate({})
    propiedad = OrdenPasosEsquema.model_json_schema()["properties"]["ids"]

    assert propiedad["uniqueItems"] is True
    assert propiedad["items"]["type"] == "integer"
