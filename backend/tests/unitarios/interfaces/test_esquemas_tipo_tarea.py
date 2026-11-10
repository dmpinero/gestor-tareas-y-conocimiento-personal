import pytest
from pydantic import ValidationError

from gestor_tareas.dominio.tarea.entidades import TipoTarea
from gestor_tareas.interfaces.api.v1.esquemas.tarea import (
    OportunidadEsquema,
    TareaActualizarEsquema,
    TareaCrearEsquema,
    TareaSalidaEsquema,
)
from gestor_tareas.main import crear_aplicacion

_ESQUEMAS = (TareaCrearEsquema, TareaActualizarEsquema)

_OPORTUNIDAD = {"codigo": "OP-1", "descripcion": "Venta", "observaciones": "Notas"}


def _datos(**cambios) -> dict:
    datos = {
        "nombre": "Tarea",
        "prioridad": 3,
        "descripcion": "Descripción",
        "fecha_creacion": "2026-11-09T10:30:00",
    }
    datos.update(cambios)
    return datos


def _con_oportunidad(**campos) -> dict:
    return _datos(tipo="oportunidad", oportunidad={**_OPORTUNIDAD, **campos})


@pytest.mark.parametrize("esquema", _ESQUEMAS)
def test_sin_tipo_ni_oportunidad_quedan_nulos(esquema) -> None:
    datos = esquema(**_datos())

    assert (datos.tipo, datos.oportunidad) == (None, None)


@pytest.mark.parametrize("esquema", _ESQUEMAS)
def test_acepta_tipo_nulo_y_oportunidad_nula_explicitos(esquema) -> None:
    datos = esquema(**_datos(tipo=None, oportunidad=None))

    assert (datos.tipo, datos.oportunidad) == (None, None)


@pytest.mark.parametrize("esquema", _ESQUEMAS)
def test_acepta_el_tipo_oportunidad_con_sus_datos(esquema) -> None:
    datos = esquema(**_con_oportunidad())

    assert datos.tipo is TipoTarea.OPORTUNIDAD
    assert datos.oportunidad == OportunidadEsquema(**_OPORTUNIDAD)


@pytest.mark.parametrize("tipo", ["Oportunidad", "OPORTUNIDAD", "otro", "", 1, True])
def test_rechaza_tipos_desconocidos(tipo: object) -> None:
    for esquema in _ESQUEMAS:
        with pytest.raises(ValidationError):
            esquema(**_datos(tipo=tipo, oportunidad=_OPORTUNIDAD))


@pytest.mark.parametrize("esquema", _ESQUEMAS)
@pytest.mark.parametrize("oportunidad", [{"oportunidad": None}, {}])
def test_el_tipo_oportunidad_exige_sus_datos(esquema, oportunidad: dict) -> None:
    with pytest.raises(ValidationError) as error:
        esquema(**_datos(tipo="oportunidad", **oportunidad))

    assert "Los datos de la oportunidad son obligatorios si el tipo es «oportunidad»." in str(
        error.value
    )


@pytest.mark.parametrize("esquema", _ESQUEMAS)
@pytest.mark.parametrize("tipo", [{"tipo": None}, {}])
def test_una_tarea_sin_tipo_no_admite_datos_de_oportunidad(esquema, tipo: dict) -> None:
    with pytest.raises(ValidationError) as error:
        esquema(**_datos(oportunidad=_OPORTUNIDAD, **tipo))

    assert "Los datos de la oportunidad solo se admiten si el tipo es «oportunidad»." in str(
        error.value
    )


def test_acepta_un_codigo_de_10_caracteres() -> None:
    assert TareaCrearEsquema(**_con_oportunidad(codigo="c" * 10)).oportunidad.codigo == "c" * 10


def test_rechaza_un_codigo_de_11_caracteres() -> None:
    with pytest.raises(ValidationError):
        TareaCrearEsquema(**_con_oportunidad(codigo="c" * 11))


@pytest.mark.parametrize("codigo", ["", "   ", " ", "　\t", "﻿"])
def test_rechaza_un_codigo_vacio_o_solo_de_espacios(codigo: str) -> None:
    with pytest.raises(ValidationError):
        TareaCrearEsquema(**_con_oportunidad(codigo=codigo))


@pytest.mark.parametrize("codigo", [None, 12, ["A"]])
def test_rechaza_un_codigo_que_no_es_texto(codigo: object) -> None:
    with pytest.raises(ValidationError):
        TareaCrearEsquema(**_con_oportunidad(codigo=codigo))


def test_el_codigo_es_obligatorio() -> None:
    with pytest.raises(ValidationError):
        TareaCrearEsquema(**_datos(tipo="oportunidad", oportunidad={"descripcion": "Venta"}))


def test_recorta_los_espacios_de_los_textos_de_la_oportunidad() -> None:
    oportunidad = TareaCrearEsquema(
        **_con_oportunidad(
            codigo="  0123456789 ", descripcion="  Venta  ", observaciones="\n Notas \n"
        )
    ).oportunidad

    assert (oportunidad.codigo, oportunidad.descripcion, oportunidad.observaciones) == (
        "0123456789",
        "Venta",
        "Notas",
    )


@pytest.mark.parametrize(("campo", "maximo"), [("descripcion", 200), ("observaciones", 5000)])
def test_acepta_los_textos_opcionales_en_su_longitud_maxima(campo: str, maximo: int) -> None:
    oportunidad = TareaCrearEsquema(**_con_oportunidad(**{campo: "x" * maximo})).oportunidad

    assert getattr(oportunidad, campo) == "x" * maximo


@pytest.mark.parametrize(("campo", "maximo"), [("descripcion", 200), ("observaciones", 5000)])
def test_rechaza_los_textos_opcionales_mas_largos(campo: str, maximo: int) -> None:
    with pytest.raises(ValidationError):
        TareaCrearEsquema(**_con_oportunidad(**{campo: "x" * (maximo + 1)}))


@pytest.mark.parametrize("campo", ["descripcion", "observaciones"])
@pytest.mark.parametrize("valor", [None, "", "   ", "  "])
def test_los_textos_opcionales_vacios_o_solo_de_espacios_quedan_nulos(
    campo: str, valor: str | None
) -> None:
    oportunidad = TareaCrearEsquema(**_con_oportunidad(**{campo: valor})).oportunidad

    assert getattr(oportunidad, campo) is None


@pytest.mark.parametrize("campo", ["descripcion", "observaciones"])
def test_los_textos_opcionales_pueden_omitirse(campo: str) -> None:
    datos = {clave: valor for clave, valor in _OPORTUNIDAD.items() if clave != campo}

    oportunidad = TareaCrearEsquema(**_datos(tipo="oportunidad", oportunidad=datos)).oportunidad

    assert getattr(oportunidad, campo) is None


@pytest.mark.parametrize("esquema", _ESQUEMAS)
def test_el_contrato_publica_el_tipo_y_la_oportunidad(esquema) -> None:
    contrato = esquema.model_json_schema()
    definiciones = contrato["$defs"]

    assert contrato["properties"]["tipo"]["anyOf"] == [
        {"enum": ["oportunidad"], "type": "string"},
        {"type": "null"},
    ]
    assert contrato["properties"]["tipo"]["default"] is None
    assert contrato["properties"]["oportunidad"]["default"] is None
    assert not {"tipo", "oportunidad"} & set(contrato.get("required", []))
    oportunidad = definiciones["OportunidadEsquema"]
    assert oportunidad["required"] == ["codigo"]
    assert oportunidad["properties"]["codigo"] == {
        "maxLength": 10,
        "minLength": 1,
        "pattern": r"\S",
        "title": "Codigo",
        "type": "string",
    }
    for campo, maximo in (("descripcion", 200), ("observaciones", 5000)):
        assert oportunidad["properties"][campo]["anyOf"] == [
            {"maxLength": maximo, "type": "string"},
            {"type": "null"},
        ]


@pytest.mark.parametrize("esquema", _ESQUEMAS)
def test_el_contrato_publica_la_regla_entre_el_tipo_y_sus_datos(esquema) -> None:
    # Cada rama del `anyOf` describe un tipo válido: sin tipo y sin datos de ningún
    # tipo, o un tipo con sus datos obligatorios.
    assert esquema.model_json_schema()["anyOf"] == [
        {"properties": {"tipo": {"type": "null"}, "oportunidad": {"type": "null"}}},
        {
            "properties": {"tipo": {"const": "oportunidad"}, "oportunidad": {"type": "object"}},
            "required": ["tipo", "oportunidad"],
        },
    ]


def test_el_openapi_publica_la_regla_entre_el_tipo_y_sus_datos() -> None:
    contrato = crear_aplicacion().openapi()["components"]["schemas"]

    for nombre in ("TareaCrearEsquema", "TareaActualizarEsquema"):
        assert contrato[nombre]["anyOf"] == TareaCrearEsquema.model_json_schema()["anyOf"]


def test_la_salida_incluye_el_tipo_y_la_oportunidad() -> None:
    salida = TareaSalidaEsquema(
        id=1,
        nombre="Tarea",
        prioridad=None,
        descripcion="Texto",
        fecha_creacion="2026-11-09T10:30:00",
        fecha_vencimiento=None,
        etiquetas=[],
        asignados=[],
        tipo="oportunidad",
        oportunidad={"codigo": "OP-1", "descripcion": None, "observaciones": None},
        completada=False,
        pasos_oportunidad=[{"id": 7, "numero": 1, "nombre": "Contacto", "hecho": True}],
    )

    assert salida.model_dump(mode="json")["pasos_oportunidad"] == [
        {"id": 7, "numero": 1, "nombre": "Contacto", "hecho": True}
    ]
    assert salida.model_dump(mode="json")["tipo"] == "oportunidad"
    assert salida.model_dump(mode="json")["oportunidad"] == {
        "codigo": "OP-1",
        "descripcion": None,
        "observaciones": None,
    }
    assert set(TareaSalidaEsquema.model_json_schema()["required"]) >= {"tipo", "oportunidad"}
