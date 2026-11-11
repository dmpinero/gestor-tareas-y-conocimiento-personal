from datetime import UTC, datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from gestor_tareas.interfaces.api.v1.esquemas.comentario import (
    ComentarioCrearEsquema,
    ComentarioEditarEsquema,
    ComentarioSalidaEsquema,
)
from gestor_tareas.interfaces.api.v1.esquemas.tarea import (
    SubtareaCrearEsquema,
    SubtareaEditarEsquema,
    SubtareaResueltaEsquema,
    TareaSalidaEsquema,
)


def test_el_alta_de_una_subtarea_recorta_el_nombre_y_la_persona() -> None:
    datos = SubtareaCrearEsquema(nombre="  Embalar \n", asignado="  Ana\t", prioridad=3.0)
    assert datos.model_dump() == {"nombre": "Embalar", "asignado": "Ana", "prioridad": 3}


def test_el_alta_de_una_subtarea_solo_exige_el_nombre() -> None:
    assert SubtareaCrearEsquema(nombre="A").model_dump() == {
        "nombre": "A",
        "asignado": None,
        "prioridad": None,
    }
    assert SubtareaCrearEsquema.model_json_schema()["required"] == ["nombre"]


@pytest.mark.parametrize(
    "datos",
    [
        {"nombre": "　"},
        {"nombre": "n" * 201},
        {"nombre": "A", "asignado": " "},
        {"nombre": "A", "asignado": "p" * 101},
        {"nombre": "A", "prioridad": False},
    ],
)
def test_el_alta_de_una_subtarea_rechaza_datos_invalidos(datos: dict) -> None:
    with pytest.raises(ValidationError):
        SubtareaCrearEsquema(**datos)


def test_el_contrato_de_la_subtarea_publica_sus_limites() -> None:
    propiedades = SubtareaCrearEsquema.model_json_schema()["properties"]
    assert propiedades["nombre"] == {
        "title": "Nombre",
        "type": "string",
        "minLength": 1,
        "maxLength": 200,
        "pattern": r"\S",
    }
    persona = next(r for r in propiedades["asignado"]["anyOf"] if r.get("type") == "string")
    assert (persona["minLength"], persona["maxLength"], persona["pattern"]) == (1, 100, r"\S")
    prioridad = next(r for r in propiedades["prioridad"]["anyOf"] if r.get("type") == "integer")
    assert (prioridad["minimum"], prioridad["maximum"]) == (1, 5)


@pytest.mark.parametrize("valor", ["true", 1, 0, None, 1.0])
def test_el_cambio_de_estado_de_una_subtarea_solo_admite_booleanos(valor: object) -> None:
    assert SubtareaResueltaEsquema(resuelta=True).resuelta is True
    with pytest.raises(ValidationError):
        SubtareaResueltaEsquema(resuelta=valor)


def test_la_salida_de_la_tarea_incluye_las_subtareas() -> None:
    contrato = TareaSalidaEsquema.model_json_schema()
    assert "subtareas" in contrato["required"]
    subtarea = contrato["$defs"]["SubtareaSalidaEsquema"]
    assert set(subtarea["required"]) == {
        "id",
        "nombre",
        "asignado",
        "prioridad",
        "resuelta",
        "comentarios",
    }
    assert subtarea["properties"]["comentarios"]["type"] == "integer"


def test_el_comentario_recorta_los_extremos_y_conserva_los_saltos_de_linea() -> None:
    assert ComentarioCrearEsquema(texto="\n Uno\r\n\nDos \t").texto == "Uno\r\n\nDos"


@pytest.mark.parametrize("texto", ["", " \n\t ", " ", "a" * 501, None, 5])
def test_el_comentario_rechaza_textos_invalidos(texto: object) -> None:
    with pytest.raises(ValidationError):
        ComentarioCrearEsquema(texto=texto)


def test_el_comentario_admite_500_caracteres() -> None:
    assert ComentarioCrearEsquema(texto="á" * 500).texto == "á" * 500


def test_la_salida_del_comentario_serializa_el_instante_en_utc_con_z() -> None:
    madrid = timezone(timedelta(hours=1))
    for creado in (
        datetime(2026, 11, 10, 16, 30, 5, tzinfo=UTC),
        datetime(2026, 11, 10, 17, 30, 5, tzinfo=madrid),
    ):
        salida = ComentarioSalidaEsquema(id=1, texto="Hola", creado=creado, editado=None)
        assert salida.model_dump(mode="json") == {
            "id": 1,
            "texto": "Hola",
            "creado": "2026-11-10T16:30:05Z",
            "editado": None,
        }

    contrato = ComentarioSalidaEsquema.model_json_schema(mode="serialization")
    assert contrato["properties"]["creado"]["pattern"] == r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$"


def test_la_salida_del_comentario_serializa_editado_en_utc_con_z() -> None:
    madrid = timezone(timedelta(hours=1))
    salida = ComentarioSalidaEsquema(
        id=1,
        texto="Hola",
        creado=datetime(2026, 11, 10, 16, 30, 5, tzinfo=UTC),
        editado=datetime(2026, 11, 10, 19, 0, 1, tzinfo=madrid),
    )

    assert salida.model_dump(mode="json")["editado"] == "2026-11-10T18:00:01Z"
    contrato = ComentarioSalidaEsquema.model_json_schema(mode="serialization")
    assert set(contrato["required"]) == {"id", "texto", "creado", "editado"}
    variantes = contrato["properties"]["editado"]["anyOf"]
    assert {"type": "null"} in variantes
    instante = next(v for v in variantes if v.get("type") == "string")
    assert instante["pattern"] == r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$"


def test_la_edicion_de_un_comentario_valida_como_el_alta() -> None:
    assert ComentarioEditarEsquema(texto="\n Uno\nDos ").texto == "Uno\nDos"
    assert ComentarioEditarEsquema(texto="á" * 500).texto == "á" * 500
    for texto in ["", " \n\t ", "a" * 501, None, 5]:
        with pytest.raises(ValidationError):
            ComentarioEditarEsquema(texto=texto)
    assert (
        ComentarioEditarEsquema.model_json_schema()["properties"]["texto"]
        == (ComentarioCrearEsquema.model_json_schema()["properties"]["texto"])
    )


def test_la_edicion_de_una_subtarea_valida_como_el_alta_y_sin_campos_opcionales_los_vacia() -> None:
    assert SubtareaEditarEsquema(nombre="  Embalar ").model_dump() == {
        "nombre": "Embalar",
        "asignado": None,
        "prioridad": None,
    }
    assert SubtareaEditarEsquema(nombre="A", asignado=" Ana ", prioridad=2).model_dump() == {
        "nombre": "A",
        "asignado": "Ana",
        "prioridad": 2,
    }
    for datos in [
        {},
        {"nombre": "n" * 201},
        {"nombre": "A", "asignado": "p" * 101},
        {"nombre": "A", "prioridad": True},
    ]:
        with pytest.raises(ValidationError):
            SubtareaEditarEsquema(**datos)
    edicion = SubtareaEditarEsquema.model_json_schema()
    assert edicion["required"] == ["nombre"]
    assert edicion["properties"] == SubtareaCrearEsquema.model_json_schema()["properties"]
