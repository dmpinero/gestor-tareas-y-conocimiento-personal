import pytest
from pydantic import ValidationError

from gestor_tareas.interfaces.api.v1.esquemas.tarea import (
    PasoHechoEsquema,
    TareaActualizarEsquema,
    TareaCrearEsquema,
    TareaSalidaEsquema,
)

_DATOS = {"nombre": "Venta", "descripcion": "d", "fecha_creacion": "2026-11-10T09:00:00"}


@pytest.mark.parametrize("valor", [True, False])
def test_el_cambio_de_un_paso_acepta_booleanos(valor: bool) -> None:
    assert PasoHechoEsquema(hecho=valor).hecho is valor


@pytest.mark.parametrize("valor", ["true", "false", 1, 0, None, 1.0])
def test_el_cambio_de_un_paso_rechaza_lo_que_no_es_booleano(valor: object) -> None:
    with pytest.raises(ValidationError):
        PasoHechoEsquema(hecho=valor)


def test_el_cambio_de_un_paso_exige_el_campo_hecho() -> None:
    with pytest.raises(ValidationError):
        PasoHechoEsquema()

    contrato = PasoHechoEsquema.model_json_schema()
    assert contrato["properties"] == {"hecho": {"title": "Hecho", "type": "boolean"}}
    assert contrato["required"] == ["hecho"]


def test_la_salida_incluye_los_pasos_de_la_oportunidad() -> None:
    contrato = TareaSalidaEsquema.model_json_schema()
    assert "pasos_oportunidad" in contrato["required"]
    paso = contrato["$defs"]["PasoOportunidadSalidaEsquema"]
    assert set(paso["required"]) == {"id", "numero", "nombre", "hecho"}


@pytest.mark.parametrize("esquema", [TareaCrearEsquema, TareaActualizarEsquema])
def test_el_alta_y_la_edicion_no_reciben_los_pasos(esquema) -> None:
    # Los pasos se copian del workflow al crear la oportunidad y solo cambian con
    # PATCH .../pasos/{id_paso}: como cualquier campo desconocido, se descartan.
    pasos = [{"numero": 1, "nombre": "X", "hecho": True}]
    assert "pasos_oportunidad" not in esquema.model_json_schema()["properties"]
    assert "pasos_oportunidad" not in esquema(**_DATOS, pasos_oportunidad=pasos).model_dump()
