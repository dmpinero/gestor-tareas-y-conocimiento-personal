"""Cliente de la API de Notion, con respuestas grabadas servidas por un transporte
simulado de httpx: nunca sale a la red."""

import json
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

import httpx
import pytest

from gestor_tareas.dominio.conocimiento.entidades import PaginaNotion
from gestor_tareas.dominio.conocimiento.errores import NotionNoDisponibleError
from gestor_tareas.infraestructura.notion.cliente_notion import ClienteNotion

_RESPUESTAS = Path(__file__).parent / "respuestas_notion"
_TOKEN = "ntn_secreto_de_prueba_123"


def _json(nombre: str) -> dict:
    return json.loads((_RESPUESTAS / nombre).read_text(encoding="utf-8"))


class _Notion:
    """Notion simulado: responde según la ruta y guarda cada petición."""

    def __init__(self, responder: Callable[[httpx.Request], httpx.Response]) -> None:
        self.peticiones: list[httpx.Request] = []
        self._responder = responder

    def __call__(self, peticion: httpx.Request) -> httpx.Response:
        self.peticiones.append(peticion)
        return self._responder(peticion)


def _cliente(notion: _Notion, esperas: list[float] | None = None) -> ClienteNotion:
    http = httpx.Client(transport=httpx.MockTransport(notion), base_url=ClienteNotion.URL_BASE)
    return ClienteNotion(
        _TOKEN, cliente_http=http, esperar=(esperas.append if esperas is not None else None)
    )


def _respuestas_grabadas(peticion: httpx.Request) -> httpx.Response:
    ruta = peticion.url.path
    if ruta == "/v1/search":
        cursor = json.loads(peticion.content).get("start_cursor")
        return httpx.Response(200, json=_json("busqueda_2.json" if cursor else "busqueda_1.json"))
    if ruta == "/v1/blocks/11111111-1111-1111-1111-111111111111/children":
        cursor = peticion.url.params.get("start_cursor")
        nombre = (
            "bloques_pagina_2.json" if cursor == "cursor-bloques-2" else "bloques_pagina_1.json"
        )
        return httpx.Response(200, json=_json(nombre))
    if ruta == "/v1/blocks/b-tog/children":
        return httpx.Response(200, json=_json("bloques_toggle.json"))
    if ruta == "/v1/blocks/b-tab/children":
        return httpx.Response(200, json=_json("bloques_tabla.json"))
    return httpx.Response(404, json={"object": "error", "status": 404, "code": "object_not_found"})


def test_lista_todas_las_paginas_compartidas_con_su_titulo_sin_las_archivadas() -> None:
    notion = _Notion(_respuestas_grabadas)

    paginas = _cliente(notion).listar_paginas()

    assert paginas == [
        PaginaNotion(
            id="11111111-1111-1111-1111-111111111111",
            titulo="Receta de paella",
            url="https://www.notion.so/Receta-de-paella-11111111111111111111111111111111",
            editada_en=datetime(2026, 11, 20, 10, 15, tzinfo=UTC),
        ),
        # Entrada de una base de datos: su título es la propiedad de tipo "title".
        PaginaNotion(
            id="33333333-3333-3333-3333-333333333333",
            titulo="Reunión con Ana",
            url="https://www.notion.so/Reunion-33333333333333333333333333333333",
            editada_en=datetime(2026, 11, 21, 16, 30, tzinfo=UTC),
        ),
        PaginaNotion(
            id="44444444-4444-4444-4444-444444444444",
            titulo="Sin título",
            url="https://www.notion.so/44444444444444444444444444444444",
            editada_en=datetime(2026, 11, 22, 7, 0, tzinfo=UTC),
        ),
    ]
    # Dos páginas de resultados: la segunda con el cursor de la primera.
    assert [p.url.path for p in notion.peticiones] == ["/v1/search", "/v1/search"]
    cuerpos = [json.loads(p.content) for p in notion.peticiones]
    assert cuerpos[0] == {"filter": {"property": "object", "value": "page"}, "page_size": 100}
    assert cuerpos[1]["start_cursor"] == "cursor-2"
    for peticion in notion.peticiones:
        assert peticion.method == "POST"
        assert peticion.headers["Authorization"] == f"Bearer {_TOKEN}"
        assert peticion.headers["Notion-Version"] == "2022-06-28"


def test_el_texto_de_una_pagina_recorre_sus_bloques_y_los_hijos_sin_imagenes_ni_subpaginas() -> (
    None
):
    notion = _Notion(_respuestas_grabadas)

    texto = _cliente(notion).texto_de_pagina("11111111-1111-1111-1111-111111111111")

    assert texto.split("\n") == [
        "Ingredientes",
        "Arroz bomba",
        "- Azafrán",
        "- Sofreír",
        "Trucos",
        "Dejar reposar 5 minutos",
        "[x] Comprar gambas",
        "[ ] Avisar a Luis",
        "La paella se come en domingo",
        "print('hola')",
        "No remover el arroz",
        "Tabla",
        "Persona | Gramos",
        "Ana | 100",
    ]
    rutas = [(p.url.path, p.url.params.get("start_cursor")) for p in notion.peticiones]
    # La subpágina es una página aparte: no se piden sus bloques.
    assert rutas == [
        ("/v1/blocks/11111111-1111-1111-1111-111111111111/children", None),
        ("/v1/blocks/11111111-1111-1111-1111-111111111111/children", "cursor-bloques-2"),
        ("/v1/blocks/b-tog/children", None),
        ("/v1/blocks/b-tab/children", None),
    ]
    assert all(p.method == "GET" for p in notion.peticiones)
    assert all(p.url.params["page_size"] == "100" for p in notion.peticiones)


def test_si_notion_limita_las_peticiones_espera_lo_que_pide_y_reintenta() -> None:
    respuestas = iter(
        [
            httpx.Response(429, headers={"Retry-After": "2"}, json={"code": "rate_limited"}),
            httpx.Response(200, json=_json("busqueda_2.json")),
        ]
    )
    notion = _Notion(lambda _: next(respuestas))
    esperas: list[float] = []

    paginas = _cliente(notion, esperas).listar_paginas()

    assert [p.titulo for p in paginas] == ["Reunión con Ana", "Sin título"]
    assert esperas == [2.0]
    assert len(notion.peticiones) == 2


def test_si_notion_sigue_limitando_se_rinde_con_un_error_claro() -> None:
    notion = _Notion(lambda _: httpx.Response(429, json={"code": "rate_limited"}))
    esperas: list[float] = []

    with pytest.raises(NotionNoDisponibleError, match="demasiadas peticiones"):
        _cliente(notion, esperas).listar_paginas()

    assert len(notion.peticiones) == 4
    assert esperas == [1.0, 1.0, 1.0]


def test_un_token_rechazado_da_un_error_que_no_incluye_el_token() -> None:
    notion = _Notion(
        lambda _: httpx.Response(
            401, json={"code": "unauthorized", "message": f"API token is invalid: {_TOKEN}"}
        )
    )

    with pytest.raises(NotionNoDisponibleError) as error:
        _cliente(notion).listar_paginas()

    assert "NOTION_TOKEN" in str(error.value)
    assert _TOKEN not in str(error.value)


def test_un_error_de_notion_da_un_error_con_su_codigo_y_sin_el_token() -> None:
    notion = _Notion(lambda _: httpx.Response(500, json={"code": "internal_server_error"}))

    with pytest.raises(NotionNoDisponibleError, match=r"\(500\)") as error:
        _cliente(notion).texto_de_pagina("x")

    assert _TOKEN not in str(error.value)


def test_sin_conexion_con_notion_da_un_error_claro() -> None:
    def sin_red(peticion: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError(f"fallo con {_TOKEN}", request=peticion)

    with pytest.raises(NotionNoDisponibleError, match="No se ha podido conectar") as error:
        _cliente(_Notion(sin_red)).listar_paginas()

    assert _TOKEN not in str(error.value)


def test_cerrar_cierra_el_cliente_http() -> None:
    http = httpx.Client(transport=httpx.MockTransport(_respuestas_grabadas))
    cliente = ClienteNotion(_TOKEN, cliente_http=http)

    cliente.cerrar()

    assert http.is_closed
