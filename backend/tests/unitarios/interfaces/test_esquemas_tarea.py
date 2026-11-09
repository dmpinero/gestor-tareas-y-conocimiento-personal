from datetime import datetime

import pytest
from pydantic import ValidationError

from gestor_tareas.interfaces.api.v1.esquemas.tarea import (
    TareaActualizarEsquema,
    TareaCrearEsquema,
    TareaSalidaEsquema,
)


def _datos(**cambios) -> dict:
    datos = {
        "nombre": "Tarea",
        "prioridad": 3,
        "descripcion": "Descripción",
        "fecha_hora": "2026-11-09T10:30:00",
    }
    datos.update(cambios)
    return datos


def test_acepta_nombre_de_200_caracteres() -> None:
    assert TareaCrearEsquema(**_datos(nombre="n" * 200)).nombre == "n" * 200


def test_rechaza_nombre_de_201_caracteres() -> None:
    with pytest.raises(ValidationError):
        TareaCrearEsquema(**_datos(nombre="n" * 201))


@pytest.mark.parametrize("nombre", ["", "   "])
def test_rechaza_nombre_vacio_o_solo_espacios(nombre: str) -> None:
    with pytest.raises(ValidationError):
        TareaCrearEsquema(**_datos(nombre=nombre))


def test_nombre_es_obligatorio() -> None:
    datos = _datos()
    del datos["nombre"]
    with pytest.raises(ValidationError):
        TareaCrearEsquema(**datos)


def test_recorta_espacios_de_nombre_y_descripcion() -> None:
    esquema = TareaCrearEsquema(**_datos(nombre="  Tarea  ", descripcion="  Texto  "))

    assert esquema.nombre == "Tarea"
    assert esquema.descripcion == "Texto"


def test_acepta_descripcion_de_500_caracteres() -> None:
    assert TareaCrearEsquema(**_datos(descripcion="d" * 500)).descripcion == "d" * 500


def test_rechaza_descripcion_de_501_caracteres() -> None:
    with pytest.raises(ValidationError):
        TareaCrearEsquema(**_datos(descripcion="d" * 501))


@pytest.mark.parametrize("descripcion", ["", "   "])
def test_rechaza_descripcion_vacia_o_solo_espacios(descripcion: str) -> None:
    with pytest.raises(ValidationError):
        TareaCrearEsquema(**_datos(descripcion=descripcion))


def test_descripcion_es_obligatoria() -> None:
    datos = _datos()
    del datos["descripcion"]
    with pytest.raises(ValidationError):
        TareaCrearEsquema(**datos)


@pytest.mark.parametrize("prioridad", [1, 5])
def test_acepta_prioridad_en_los_limites(prioridad: int) -> None:
    assert TareaCrearEsquema(**_datos(prioridad=prioridad)).prioridad == prioridad


@pytest.mark.parametrize("prioridad", [0, 6])
def test_rechaza_prioridad_fuera_de_rango(prioridad: int) -> None:
    with pytest.raises(ValidationError):
        TareaCrearEsquema(**_datos(prioridad=prioridad))


def test_prioridad_es_opcional() -> None:
    datos = _datos()
    del datos["prioridad"]

    assert TareaCrearEsquema(**datos).prioridad is None
    assert TareaCrearEsquema(**_datos(prioridad=None)).prioridad is None


def test_acepta_fecha_hora_iso_sin_zona_horaria() -> None:
    assert TareaCrearEsquema(**_datos()).fecha_hora == datetime(2026, 11, 9, 10, 30, 0)


def test_fecha_hora_es_obligatoria() -> None:
    datos = _datos()
    del datos["fecha_hora"]
    with pytest.raises(ValidationError):
        TareaCrearEsquema(**datos)


@pytest.mark.parametrize("fecha_hora", ["2026-11-09T10:30:00Z", "2026-11-09T10:30:00+01:00"])
def test_rechaza_fecha_hora_con_zona_horaria(fecha_hora: str) -> None:
    with pytest.raises(ValidationError):
        TareaCrearEsquema(**_datos(fecha_hora=fecha_hora))


@pytest.mark.parametrize(
    "fecha_hora",
    ["", "09/11/2026 10:30:00", "2026-02-30T10:30:00", "2027-02-29T10:30:00", "2026-11-09", 0],
)
def test_rechaza_fecha_hora_con_formato_invalido(fecha_hora: object) -> None:
    with pytest.raises(ValidationError):
        TareaCrearEsquema(**_datos(fecha_hora=fecha_hora))


def test_acepta_el_29_de_febrero_de_un_anio_bisiesto() -> None:
    esquema = TareaCrearEsquema(**_datos(fecha_hora="2028-02-29T23:59:59"))

    assert esquema.fecha_hora == datetime(2028, 2, 29, 23, 59, 59)


def test_descarta_los_microsegundos_de_fecha_hora() -> None:
    esquema = TareaCrearEsquema(**_datos(fecha_hora="2026-11-09T10:30:15.987654"))

    assert esquema.fecha_hora == datetime(2026, 11, 9, 10, 30, 15)


def test_actualizar_usa_el_mismo_cuerpo_y_validaciones_que_el_alta() -> None:
    esquema = TareaActualizarEsquema(**_datos(nombre="  Editada  "))

    assert esquema.model_dump() == {
        "nombre": "Editada",
        "prioridad": 3,
        "descripcion": "Descripción",
        "fecha_hora": datetime(2026, 11, 9, 10, 30, 0),
    }
    with pytest.raises(ValidationError):
        TareaActualizarEsquema(**_datos(fecha_hora="2026-11-09T10:30:00Z"))
    with pytest.raises(ValidationError):
        TareaActualizarEsquema(**_datos(nombre="n" * 201))


def test_salida_expone_exactamente_los_campos_del_contrato() -> None:
    salida = TareaSalidaEsquema(
        id=1,
        nombre="Tarea",
        prioridad=None,
        descripcion="Texto",
        fecha_hora=datetime(2026, 11, 9, 10, 30, 0),
    )

    assert salida.model_dump(mode="json") == {
        "id": 1,
        "nombre": "Tarea",
        "prioridad": None,
        "descripcion": "Texto",
        "fecha_hora": "2026-11-09T10:30:00",
    }


# Regresión: schemathesis generó un nombre "\u00a0" (espacio duro) que cumplía el
# contrato publicado (`minLength: 1`) pero la API rechazaba con 422 al recortarlo.
# El contrato y la validación deben usar la misma definición de espacio.
ESPACIOS_UNICODE = ["\u00a0", "\u2003", "\u3000", "\ufeff", "\t\n", "\u00a0 \u2028"]


@pytest.mark.parametrize("campo", ["nombre", "descripcion"])
@pytest.mark.parametrize("valor", ESPACIOS_UNICODE)
def test_rechaza_textos_formados_solo_por_espacios_unicode(campo: str, valor: str) -> None:
    with pytest.raises(ValidationError):
        TareaCrearEsquema(**_datos(**{campo: valor}))
    with pytest.raises(ValidationError):
        TareaActualizarEsquema(**_datos(**{campo: valor}))


@pytest.mark.parametrize("campo", ["nombre", "descripcion"])
def test_el_contrato_exige_un_caracter_que_no_sea_espacio(campo: str) -> None:
    for esquema in (TareaCrearEsquema, TareaActualizarEsquema):
        propiedad = esquema.model_json_schema()["properties"][campo]
        assert propiedad["pattern"] == r"\S"


def test_recorta_espacios_unicode_alrededor_del_texto() -> None:
    esquema = TareaCrearEsquema(**_datos(nombre="\u00a0Tarea\u3000", descripcion="\ufeffTexto\t"))

    assert esquema.nombre == "Tarea"
    assert esquema.descripcion == "Texto"


# Regresión: en modo laxo Pydantic aceptaba `true` (→ 1) y `"2"` (→ 2)
# aunque el contrato publica `integer | null`.
@pytest.mark.parametrize("prioridad", [True, False, "2", 2.5])
def test_rechaza_prioridad_que_no_es_un_entero_json(prioridad: object) -> None:
    with pytest.raises(ValidationError):
        TareaCrearEsquema(**_datos(prioridad=prioridad))
    with pytest.raises(ValidationError):
        TareaActualizarEsquema(**_datos(prioridad=prioridad))


def test_acepta_prioridad_entera_escrita_como_decimal() -> None:
    # En JSON Schema `3.0` es un `integer` válido; se guarda como 3.
    esquema = TareaCrearEsquema(**_datos(prioridad=3.0))

    assert esquema.prioridad == 3
    assert isinstance(esquema.prioridad, int)


def test_el_contrato_publica_el_rango_de_la_prioridad() -> None:
    for esquema in (TareaCrearEsquema, TareaActualizarEsquema):
        variantes = esquema.model_json_schema()["properties"]["prioridad"]["anyOf"]
        entero = next(v for v in variantes if v.get("type") == "integer")
        assert (entero["minimum"], entero["maximum"]) == (1, 5)


@pytest.mark.parametrize("valor", ["\x1c", "\x1f", "\x85"])
def test_acepta_caracteres_que_json_schema_no_considera_espacio(valor: str) -> None:
    # Python los trata como espacio, pero el `\S` del contrato no: deben aceptarse.
    esquema = TareaCrearEsquema(**_datos(nombre=valor))

    assert esquema.nombre == valor
