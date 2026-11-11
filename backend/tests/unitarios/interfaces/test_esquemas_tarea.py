from datetime import datetime

import pytest
from pydantic import ValidationError

from gestor_tareas.interfaces.api.v1.esquemas.tarea import (
    PATRON_FECHA_HORA,
    TareaActualizarEsquema,
    TareaCompletadaEsquema,
    TareaCrearEsquema,
    TareaSalidaEsquema,
)


def _datos(**cambios) -> dict:
    datos = {
        "nombre": "Tarea",
        "prioridad": 3,
        "descripcion": "Descripción",
        "fecha_creacion": "2026-11-09T10:30:00",
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


def test_acepta_fecha_creacion_iso_sin_zona_horaria() -> None:
    assert TareaCrearEsquema(**_datos()).fecha_creacion == datetime(2026, 11, 9, 10, 30, 0)


def test_fecha_creacion_es_obligatoria() -> None:
    datos = _datos()
    del datos["fecha_creacion"]
    with pytest.raises(ValidationError):
        TareaCrearEsquema(**datos)


@pytest.mark.parametrize("fecha_creacion", ["2026-11-09T10:30:00Z", "2026-11-09T10:30:00+01:00"])
def test_rechaza_fecha_creacion_con_zona_horaria(fecha_creacion: str) -> None:
    with pytest.raises(ValidationError):
        TareaCrearEsquema(**_datos(fecha_creacion=fecha_creacion))


@pytest.mark.parametrize(
    "fecha_creacion",
    ["", "09/11/2026 10:30:00", "2026-02-30T10:30:00", "2027-02-29T10:30:00", "2026-11-09", 0],
)
def test_rechaza_fecha_creacion_con_formato_invalido(fecha_creacion: object) -> None:
    with pytest.raises(ValidationError):
        TareaCrearEsquema(**_datos(fecha_creacion=fecha_creacion))


def test_acepta_el_29_de_febrero_de_un_anio_bisiesto() -> None:
    esquema = TareaCrearEsquema(**_datos(fecha_creacion="2028-02-29T23:59:59"))

    assert esquema.fecha_creacion == datetime(2028, 2, 29, 23, 59, 59)


def test_descarta_los_microsegundos_de_fecha_creacion() -> None:
    esquema = TareaCrearEsquema(**_datos(fecha_creacion="2026-11-09T10:30:15.987654"))

    assert esquema.fecha_creacion == datetime(2026, 11, 9, 10, 30, 15)


def test_actualizar_usa_el_mismo_cuerpo_y_validaciones_que_el_alta() -> None:
    esquema = TareaActualizarEsquema(**_datos(nombre="  Editada  "))

    assert esquema.model_dump() == {
        "nombre": "Editada",
        "prioridad": 3,
        "descripcion": "Descripción",
        "fecha_creacion": datetime(2026, 11, 9, 10, 30, 0),
        "fecha_vencimiento": None,
        "etiquetas": [],
        "asignados": [],
        "tipo": None,
        "oportunidad": None,
        "grupo_estados_id": None,
    }
    with pytest.raises(ValidationError):
        TareaActualizarEsquema(**_datos(fecha_creacion="2026-11-09T10:30:00Z"))
    with pytest.raises(ValidationError):
        TareaActualizarEsquema(**_datos(nombre="n" * 201))


def test_salida_expone_exactamente_los_campos_del_contrato() -> None:
    salida = TareaSalidaEsquema(
        id=1,
        nombre="Tarea",
        prioridad=None,
        descripcion="Texto",
        fecha_creacion=datetime(2026, 11, 9, 10, 30, 0),
        fecha_vencimiento=datetime(2026, 11, 20, 18, 0, 0),
        etiquetas=["casa"],
        asignados=["Ana"],
        tipo=None,
        oportunidad=None,
        completada=False,
        subtareas=[],
        grupo_estados=None,
        estado=None,
    )

    assert salida.model_dump(mode="json") == {
        "id": 1,
        "nombre": "Tarea",
        "prioridad": None,
        "descripcion": "Texto",
        "fecha_creacion": "2026-11-09T10:30:00",
        "fecha_vencimiento": "2026-11-20T18:00:00",
        "etiquetas": ["casa"],
        "asignados": ["Ana"],
        "tipo": None,
        "oportunidad": None,
        "completada": False,
        "subtareas": [],
        "grupo_estados": None,
        "estado": None,
    }


def test_salida_serializa_la_fecha_de_vencimiento_ausente_como_null() -> None:
    salida = TareaSalidaEsquema(
        id=1,
        nombre="Tarea",
        prioridad=None,
        descripcion="Texto",
        fecha_creacion=datetime(2026, 11, 9, 10, 30, 0),
        fecha_vencimiento=None,
        etiquetas=[],
        asignados=[],
        tipo=None,
        oportunidad=None,
        completada=False,
        subtareas=[],
        grupo_estados=None,
        estado=None,
    )

    assert salida.model_dump(mode="json")["fecha_vencimiento"] is None


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


# --- Fecha de vencimiento (S4) ---


def test_fecha_vencimiento_es_opcional() -> None:
    assert TareaCrearEsquema(**_datos()).fecha_vencimiento is None
    assert TareaCrearEsquema(**_datos(fecha_vencimiento=None)).fecha_vencimiento is None


def test_acepta_fecha_vencimiento_con_el_mismo_formato_que_la_de_creacion() -> None:
    esquema = TareaCrearEsquema(**_datos(fecha_vencimiento="2026-11-20T18:00:00.123"))

    assert esquema.fecha_vencimiento == datetime(2026, 11, 20, 18, 0, 0)


@pytest.mark.parametrize(
    "fecha_vencimiento",
    ["", "20/11/2026 18:00:00", "2026-11-20T18:00:00Z", "2026-02-30T10:30:00", 0],
)
def test_rechaza_fecha_vencimiento_con_formato_invalido(fecha_vencimiento: object) -> None:
    for esquema in (TareaCrearEsquema, TareaActualizarEsquema):
        with pytest.raises(ValidationError):
            esquema(**_datos(fecha_vencimiento=fecha_vencimiento))


def test_rechaza_fecha_vencimiento_anterior_a_la_de_creacion() -> None:
    for esquema in (TareaCrearEsquema, TareaActualizarEsquema):
        with pytest.raises(ValidationError) as error:
            esquema(**_datos(fecha_vencimiento="2026-11-09T10:29:59"))
        assert "La fecha de vencimiento no puede ser anterior a la fecha de creación." in str(
            error.value
        )


def test_acepta_fecha_vencimiento_igual_a_la_de_creacion() -> None:
    esquema = TareaCrearEsquema(**_datos(fecha_vencimiento="2026-11-09T10:30:00"))

    assert esquema.fecha_vencimiento == esquema.fecha_creacion


def test_el_contrato_publica_la_fecha_de_vencimiento_como_texto_o_null() -> None:
    for esquema in (TareaCrearEsquema, TareaActualizarEsquema):
        propiedad = esquema.model_json_schema()["properties"]["fecha_vencimiento"]
        tipos = {v.get("type") for v in propiedad["anyOf"]}
        assert tipos == {"string", "null"}
        texto = next(v for v in propiedad["anyOf"] if v.get("type") == "string")
        assert texto["pattern"] == PATRON_FECHA_HORA
        assert "fecha_vencimiento" not in esquema.model_json_schema().get("required", [])


# --- Etiquetas (S1) y asignados (S2) ---

_LIMITES = [("etiquetas", 50), ("asignados", 100)]


@pytest.mark.parametrize("campo", ["etiquetas", "asignados"])
def test_etiquetas_y_asignados_son_opcionales_y_por_defecto_vacios(campo: str) -> None:
    assert getattr(TareaCrearEsquema(**_datos()), campo) == []


@pytest.mark.parametrize(("campo", "maximo"), _LIMITES)
def test_acepta_nombres_en_el_limite_y_los_recorta(campo: str, maximo: int) -> None:
    esquema = TareaCrearEsquema(**_datos(**{campo: ["\u00a0" + "x" * maximo + " ", "a"]}))

    assert getattr(esquema, campo) == ["x" * maximo, "a"]


@pytest.mark.parametrize(("campo", "maximo"), _LIMITES)
def test_rechaza_nombres_demasiado_largos(campo: str, maximo: int) -> None:
    for esquema in (TareaCrearEsquema, TareaActualizarEsquema):
        with pytest.raises(ValidationError):
            esquema(**_datos(**{campo: ["x" * (maximo + 1)]}))


@pytest.mark.parametrize("campo", ["etiquetas", "asignados"])
@pytest.mark.parametrize("valor", ["", "   ", *ESPACIOS_UNICODE])
def test_rechaza_nombres_vacios_o_solo_espacios(campo: str, valor: str) -> None:
    for esquema in (TareaCrearEsquema, TareaActualizarEsquema):
        with pytest.raises(ValidationError):
            esquema(**_datos(**{campo: ["valido", valor]}))


@pytest.mark.parametrize("campo", ["etiquetas", "asignados"])
@pytest.mark.parametrize("valor", [None, "casa", [1], [None]])
def test_rechaza_valores_que_no_son_listas_de_textos(campo: str, valor: object) -> None:
    with pytest.raises(ValidationError):
        TareaCrearEsquema(**_datos(**{campo: valor}))


@pytest.mark.parametrize(("campo", "maximo"), _LIMITES)
def test_el_contrato_publica_las_restricciones_de_cada_nombre(campo: str, maximo: int) -> None:
    for esquema in (TareaCrearEsquema, TareaActualizarEsquema):
        propiedad = esquema.model_json_schema()["properties"][campo]
        assert propiedad["type"] == "array"
        assert propiedad["items"] == {
            "type": "string",
            "minLength": 1,
            "maxLength": maximo,
            "pattern": r"\S",
        }
        assert campo not in esquema.model_json_schema().get("required", [])


def test_la_salida_exige_el_estado_completada() -> None:
    assert "completada" in TareaSalidaEsquema.model_json_schema()["required"]
    assert TareaSalidaEsquema.model_json_schema()["properties"]["completada"]["type"] == ("boolean")


@pytest.mark.parametrize("esquema", [TareaCrearEsquema, TareaActualizarEsquema])
def test_el_alta_y_la_edicion_no_reciben_el_estado_completada(esquema) -> None:
    # El estado solo se cambia con PATCH /completada: el campo no forma parte del
    # cuerpo y, como cualquier otro campo desconocido, se descarta.
    assert "completada" not in esquema.model_json_schema()["properties"]
    assert "completada" not in esquema(**_datos(completada=True)).model_dump()


@pytest.mark.parametrize("valor", [True, False])
def test_el_cambio_de_estado_acepta_booleanos(valor: bool) -> None:
    assert TareaCompletadaEsquema(completada=valor).completada is valor


@pytest.mark.parametrize("valor", ["true", "false", 1, 0, None, "si", 1.0])
def test_el_cambio_de_estado_rechaza_lo_que_no_es_booleano(valor: object) -> None:
    with pytest.raises(ValidationError):
        TareaCompletadaEsquema(completada=valor)


def test_el_cambio_de_estado_exige_el_campo_completada() -> None:
    with pytest.raises(ValidationError):
        TareaCompletadaEsquema()

    contrato = TareaCompletadaEsquema.model_json_schema()
    assert contrato["properties"] == {"completada": {"title": "Completada", "type": "boolean"}}
    assert contrato["required"] == ["completada"]
