from datetime import UTC, datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from gestor_tareas.interfaces.api.v1.esquemas.comentario import (
    ComentarioCrearEsquema,
    ComentarioEditarEsquema,
    ComentarioSalidaEsquema,
)
from gestor_tareas.interfaces.api.v1.esquemas.html_comentario import sanear_html
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


def test_el_comentario_en_texto_plano_se_guarda_como_un_parrafo_por_linea() -> None:
    assert ComentarioCrearEsquema(texto="\n Uno\r\n\nDos \t").texto == "<p>Uno</p><p></p><p>Dos</p>"


def test_el_comentario_en_texto_plano_escapa_los_caracteres_especiales() -> None:
    assert ComentarioCrearEsquema(texto='a < b & "c"').texto == '<p>a &lt; b &amp; "c"</p>'


def test_el_comentario_conserva_el_formato_permitido() -> None:
    html = (
        "<p><strong>N</strong><em>C</em><u>S</u><s>T</s><br>"
        '<span style="color:#e03131">R</span>'
        '<mark data-color="#ffec99" style="background-color:#ffec99">M</mark></p>'
        "<ul><li>V</li></ul><ol><li>1</li></ol>"
        '<p><a href="https://ejemplo.com" target="_blank" '
        'rel="noopener noreferrer nofollow">E</a></p>'
    )
    assert ComentarioCrearEsquema(texto=html).texto == html


@pytest.mark.parametrize(
    ("texto", "saneado"),
    [
        ("<p>a<script>alert(1)</script>b</p>", "<p>ab</p>"),
        ('<p><img src="x" onerror="alert(1)">a</p>', "<p>a</p>"),
        ('<p onclick="alert(1)">a</p>', "<p>a</p>"),
        (
            '<a href="javascript:alert(1)">a</a>',
            '<a rel="noopener noreferrer nofollow">a</a>',
        ),
        (
            '<a href="mailto:a@b.es" rel="opener" target="_top">a</a>',
            '<a href="mailto:a@b.es" rel="noopener noreferrer nofollow">a</a>',
        ),
        ("<div><h1>a</h1></div><table><tr><td>b</td></tr></table>", "<p>ab</p>"),
        (
            '<span style="color:red;position:fixed;background-color:blue">a</span>',
            '<span style="color:red">a</span>',
        ),
        (
            '<mark style="background-color:#ff0;color:red">a</mark>',
            '<mark style="background-color:#ff0">a</mark>',
        ),
        ('<span style="color:url(javascript:alert(1))" class="x">a</span>', "<span>a</span>"),
        # Ningún atributo genérico (nh3 deja lang y title si no se le dice).
        ('<p lang="en" title="t" class="c">a</p>', "<p>a</p>"),
        ('<p><strong title="x">a</strong></p>', "<p><strong>a</strong></p>"),
    ],
)
def test_el_comentario_elimina_lo_que_no_esta_permitido(texto: str, saneado: str) -> None:
    assert ComentarioCrearEsquema(texto=texto).texto == saneado


def test_sanear_de_nuevo_un_comentario_guardado_no_lo_cambia() -> None:
    for texto in ["Uno\nDos & <3", "<div>a &lt; b</div>", "<p><strong>a</strong></p>"]:
        guardado = ComentarioCrearEsquema(texto=texto).texto
        assert ComentarioCrearEsquema(texto=guardado).texto == guardado


def test_el_comentario_admite_500_caracteres_visibles() -> None:
    assert ComentarioCrearEsquema(texto="á" * 500).texto == f"<p>{'á' * 500}</p>"
    # Las etiquetas no cuentan; las entidades cuentan como un carácter.
    html = f"<p><strong>{'a' * 498}</strong>&amp;&lt;</p>"
    assert ComentarioCrearEsquema(texto=html).texto == html
    # Los espacios de los extremos del texto visible no cuentan.
    assert ComentarioCrearEsquema(texto=f"<p> {'a' * 500} </p>").texto == f"<p> {'a' * 500} </p>"


@pytest.mark.parametrize(
    "texto",
    [
        "",
        " \n\t ",
        " ",
        "<p> </p>",
        "<p>&nbsp;</p><p></p>",
        "<script>alert(1)</script>",
        "a" * 501,
        f"<p><em>{'a' * 501}</em></p>",
        f"<p>{'&amp;' * 501}</p>",
        None,
        5,
    ],
)
def test_el_comentario_rechaza_textos_invalidos(texto: object) -> None:
    with pytest.raises(ValidationError):
        ComentarioCrearEsquema(texto=texto)


def test_el_comentario_rechaza_un_html_saneado_de_mas_de_10000_caracteres() -> None:
    # 400 caracteres visibles y 3207 de entrada, pero al sanear cada enlace recibe
    # su `rel` y el HTML guardado pasaría de 10000.
    enlaces = f"<p>{'<a>a</a>' * 400}</p>"
    assert len(enlaces) <= 10000 < len(sanear_html(enlaces))
    with pytest.raises(ValidationError):
        ComentarioCrearEsquema(texto=enlaces)
    color = '<span style="color:#e03131">a</span>'
    assert len(ComentarioCrearEsquema(texto=f"<p>{color * 250}</p>").texto) == 9007


def test_el_contrato_del_comentario_publica_sus_limites() -> None:
    texto = ComentarioCrearEsquema.model_json_schema()["properties"]["texto"]
    assert (texto["type"], texto["minLength"], texto["maxLength"], texto["pattern"]) == (
        "string",
        1,
        10000,
        r"\S",
    )
    assert "500 caracteres visibles" in texto["description"]


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
    assert ComentarioEditarEsquema(texto="\n Uno\nDos ").texto == "<p>Uno</p><p>Dos</p>"
    assert ComentarioEditarEsquema(texto="á" * 500).texto == f"<p>{'á' * 500}</p>"
    assert ComentarioEditarEsquema(texto="<p>a<script>x</script></p>").texto == "<p>a</p>"
    for texto in ["", " \n\t ", "<p> </p>", "a" * 501, None, 5]:
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
