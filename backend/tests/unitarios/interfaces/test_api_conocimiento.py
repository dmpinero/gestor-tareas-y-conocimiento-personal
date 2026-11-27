"""API de Conocimiento con dobles de Notion, del modelo y del índice (sin base de
datos ni red)."""

import json
from dataclasses import dataclass
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from gestor_tareas.aplicacion.conocimiento.casos_uso import RECHAZADA, SIN_RESULTADOS
from gestor_tareas.configuracion import Configuracion
from gestor_tareas.dominio.conocimiento.entidades import PaginaNotion
from gestor_tareas.dominio.conocimiento.errores import RespuestaRechazadaError
from gestor_tareas.infraestructura.llm.modelo_anthropic import ModeloAnthropic
from gestor_tareas.infraestructura.notion.cliente_notion import ClienteNotion
from gestor_tareas.interfaces.api.v1.enrutadores import conocimiento as enrutador_conocimiento
from gestor_tareas.interfaces.api.v1.enrutadores.conocimiento import (
    obtener_fuente_notion,
    obtener_modelo_lenguaje,
    obtener_repositorio_conocimiento,
)
from gestor_tareas.main import crear_aplicacion
from tests.unitarios.aplicacion.dobles_conocimiento import (
    FuenteNotionFalsa,
    ModeloLenguajeFalso,
    RepositorioConocimientoEnMemoria,
)

_RUTA = "/api/v1/conocimiento"
_EDITADA = datetime(2026, 11, 20, 9, 0, tzinfo=UTC)


@dataclass
class Entorno:
    cliente: TestClient
    repositorio: RepositorioConocimientoEnMemoria
    fuente: FuenteNotionFalsa | None
    modelo: ModeloLenguajeFalso | None


def _montar(fuente: FuenteNotionFalsa | None, modelo: ModeloLenguajeFalso | None) -> Entorno:
    aplicacion = crear_aplicacion()
    repositorio = RepositorioConocimientoEnMemoria()
    aplicacion.dependency_overrides[obtener_repositorio_conocimiento] = lambda: repositorio
    aplicacion.dependency_overrides[obtener_fuente_notion] = lambda: fuente
    aplicacion.dependency_overrides[obtener_modelo_lenguaje] = lambda: modelo
    return Entorno(TestClient(aplicacion), repositorio, fuente, modelo)


@pytest.fixture
def configurado() -> Entorno:
    return _montar(
        FuenteNotionFalsa(
            paginas=[PaginaNotion("receta", "Receta de paella", "https://n.so/receta", _EDITADA)],
            textos={"receta": "La paella lleva arroz bomba."},
        ),
        ModeloLenguajeFalso(trozos=["Lleva ", "arroz [Receta de paella]."]),
    )


@pytest.fixture
def sin_configurar() -> Entorno:
    return _montar(None, None)


def _eventos(cuerpo: str) -> list[tuple[str, object]]:
    eventos = []
    for bloque in cuerpo.split("\n\n"):
        if not bloque.strip():
            continue
        lineas = dict(linea.split(": ", 1) for linea in bloque.split("\n"))
        eventos.append((lineas["event"], json.loads(lineas["data"])))
    return eventos


def _preguntar(cliente: TestClient, *mensajes: tuple[str, str]):
    return cliente.post(
        f"{_RUTA}/preguntar", json={"mensajes": [{"rol": r, "texto": t} for r, t in mensajes]}
    )


# --- Estado ---------------------------------------------------------------------


def test_el_estado_sin_configurar_lo_dice_sin_desvelar_nada(sin_configurar: Entorno) -> None:
    respuesta = sin_configurar.cliente.get(f"{_RUTA}/estado")

    assert respuesta.status_code == 200
    assert respuesta.json() == {
        "configurado": {"notion": False, "anthropic": False},
        "paginas": 0,
        "fragmentos": 0,
        "ultima_sincronizacion": None,
    }


def test_el_estado_tras_sincronizar_cuenta_paginas_y_trozos(configurado: Entorno) -> None:
    configurado.cliente.post(f"{_RUTA}/sincronizar")

    respuesta = configurado.cliente.get(f"{_RUTA}/estado")

    datos = respuesta.json()
    assert datos["configurado"] == {"notion": True, "anthropic": True}
    assert (datos["paginas"], datos["fragmentos"]) == (1, 1)
    assert datos["ultima_sincronizacion"].endswith("Z")


# --- Sincronizar ----------------------------------------------------------------


def test_sincronizar_devuelve_el_resumen(configurado: Entorno) -> None:
    respuesta = configurado.cliente.post(f"{_RUTA}/sincronizar")

    assert respuesta.status_code == 200
    datos = respuesta.json()
    assert {k: v for k, v in datos.items() if k != "ultima_sincronizacion"} == {
        "paginas": 1,
        "fragmentos": 1,
        "nuevas": 1,
        "actualizadas": 0,
        "eliminadas": 0,
    }
    assert datetime.fromisoformat(datos["ultima_sincronizacion"]).tzinfo is not None


def test_sincronizar_sin_token_da_503(sin_configurar: Entorno) -> None:
    respuesta = sin_configurar.cliente.post(f"{_RUTA}/sincronizar")

    assert respuesta.status_code == 503
    assert respuesta.json() == {"detalle": "Falta configurar NOTION_TOKEN en backend/.env"}


def test_sincronizar_con_otra_en_curso_da_409(configurado: Entorno) -> None:
    configurado.repositorio.en_curso_desde = datetime.now(UTC)

    respuesta = configurado.cliente.post(f"{_RUTA}/sincronizar")

    assert respuesta.status_code == 409
    assert "en curso" in respuesta.json()["detalle"]
    assert configurado.repositorio.paginas == {}


def test_sincronizar_si_notion_falla_da_502_con_su_mensaje(configurado: Entorno) -> None:
    configurado.fuente.falla_al_listar = True

    respuesta = configurado.cliente.post(f"{_RUTA}/sincronizar")

    assert respuesta.status_code == 502
    assert respuesta.json() == {"detalle": "Notion ha respondido con un error (500)."}
    assert configurado.repositorio.en_curso_desde is None


# --- Preguntar ------------------------------------------------------------------


def test_preguntar_responde_en_streaming_con_fuentes_texto_y_fin(configurado: Entorno) -> None:
    configurado.cliente.post(f"{_RUTA}/sincronizar")

    respuesta = _preguntar(configurado.cliente, ("usuario", "¿Qué lleva la paella?"))

    assert respuesta.status_code == 200
    assert respuesta.headers["content-type"].startswith("text/event-stream")
    assert respuesta.headers["cache-control"] == "no-cache"
    assert respuesta.headers["x-accel-buffering"] == "no"
    assert _eventos(respuesta.text) == [
        (
            "fuentes",
            [{"pagina_id": "receta", "titulo": "Receta de paella", "url": "https://n.so/receta"}],
        ),
        ("texto", {"delta": "Lleva "}),
        ("texto", {"delta": "arroz [Receta de paella]."}),
        ("fin", {}),
    ]


def test_preguntar_sin_nada_relevante_lo_dice_sin_llamar_al_modelo(configurado: Entorno) -> None:
    respuesta = _preguntar(configurado.cliente, ("usuario", "¿Cuándo es el dentista?"))

    assert _eventos(respuesta.text) == [
        ("fuentes", []),
        ("texto", {"delta": SIN_RESULTADOS}),
        ("fin", {}),
    ]
    assert configurado.modelo.llamadas == []


def test_preguntar_si_claude_se_niega_termina_con_un_evento_de_error(configurado: Entorno) -> None:
    configurado.cliente.post(f"{_RUTA}/sincronizar")
    configurado.modelo.trozos = []
    configurado.modelo.error = RespuestaRechazadaError("no")

    respuesta = _preguntar(configurado.cliente, ("usuario", "paella"))

    assert _eventos(respuesta.text)[1:] == [("error", {"detalle": RECHAZADA})]


def test_preguntar_ante_un_fallo_inesperado_termina_con_un_evento_de_error(
    configurado: Entorno,
) -> None:
    configurado.cliente.post(f"{_RUTA}/sincronizar")
    configurado.modelo.trozos = ["Empie"]
    configurado.modelo.error = RuntimeError("fallo interno con datos privados")

    respuesta = _preguntar(configurado.cliente, ("usuario", "paella"))

    eventos = _eventos(respuesta.text)
    assert eventos[1] == ("texto", {"delta": "Empie"})
    nombre, datos = eventos[2]
    assert nombre == "error"
    assert "privados" not in datos["detalle"]


def test_preguntar_sin_clave_da_503(sin_configurar: Entorno) -> None:
    respuesta = _preguntar(sin_configurar.cliente, ("usuario", "Hola"))

    assert respuesta.status_code == 503
    assert respuesta.json() == {"detalle": "Falta configurar ANTHROPIC_API_KEY en backend/.env"}


@pytest.mark.parametrize(
    "mensajes",
    [
        [],
        [{"rol": "asistente", "texto": "Hola"}],
        [{"rol": "usuario", "texto": "Hola"}, {"rol": "asistente", "texto": "¿Sí?"}],
        [{"rol": "usuario", "texto": "   "}],
        [{"rol": "usuario", "texto": "x" * 4001}],
        [{"rol": "sistema", "texto": "Hola"}],
        [{"rol": "usuario", "texto": "Hola"}] * 21,
    ],
)
def test_preguntar_con_una_conversacion_invalida_da_422(
    configurado: Entorno, mensajes: list[dict]
) -> None:
    respuesta = configurado.cliente.post(f"{_RUTA}/preguntar", json={"mensajes": mensajes})

    assert respuesta.status_code == 422
    assert configurado.modelo.llamadas == []


def test_preguntar_admite_20_mensajes_de_4000_caracteres(configurado: Entorno) -> None:
    mensajes = [
        {"rol": "usuario" if i % 2 == 0 else "asistente", "texto": "paella " + "x" * 3993}
        for i in range(19)
    ]

    respuesta = configurado.cliente.post(
        f"{_RUTA}/preguntar", json={"mensajes": [*mensajes, mensajes[0]]}
    )

    assert respuesta.status_code == 200


def test_el_contrato_publica_el_streaming_y_los_errores() -> None:
    rutas = TestClient(crear_aplicacion()).get("/openapi.json").json()["paths"]

    assert set(rutas[f"{_RUTA}/estado"]) == {"get"}
    assert set(rutas[f"{_RUTA}/sincronizar"]) == {"post"}
    assert set(rutas[f"{_RUTA}/preguntar"]) == {"post"}
    preguntar = rutas[f"{_RUTA}/preguntar"]["post"]["responses"]
    assert set(preguntar["200"]["content"]) == {"text/event-stream"}
    assert {"422", "503"} <= set(preguntar)
    assert {"409", "502", "503"} <= set(rutas[f"{_RUTA}/sincronizar"]["post"]["responses"])


# --- Credenciales de la configuración ------------------------------------------


def _con_configuracion(monkeypatch: pytest.MonkeyPatch, **valores: str) -> None:
    configuracion = Configuracion(_env_file=None, **valores)
    monkeypatch.setattr(enrutador_conocimiento, "obtener_configuracion", lambda: configuracion)


def test_sin_credenciales_no_hay_ni_notion_ni_modelo(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("NOTION_TOKEN", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    _con_configuracion(monkeypatch)

    assert list(obtener_fuente_notion()) == [None]
    assert obtener_modelo_lenguaje() is None


def test_con_token_hay_un_cliente_de_notion_que_se_cierra_al_acabar(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _con_configuracion(monkeypatch, notion_token="ntn_x")

    dependencia = obtener_fuente_notion()
    cliente = next(dependencia)
    assert isinstance(cliente, ClienteNotion)
    dependencia.close()

    assert cliente._http.is_closed


def test_con_clave_hay_un_modelo_de_claude_que_se_reutiliza(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _con_configuracion(monkeypatch, anthropic_api_key="sk-ant-x")

    modelo = obtener_modelo_lenguaje()

    assert isinstance(modelo, ModeloAnthropic)
    assert obtener_modelo_lenguaje() is modelo


# --- Buscar (sin IA) ------------------------------------------------------------


def _con_notas(entorno: Entorno) -> Entorno:
    entorno.repositorio.guardar_pagina(
        PaginaNotion("receta", "Receta de paella", "https://n.so/receta", _EDITADA),
        ["Receta de paella", "La paella lleva arroz bomba y azafrán."],
    )
    entorno.repositorio.guardar_pagina(
        PaginaNotion("reunion", "Reunión", "https://n.so/reunion", _EDITADA),
        ["Ana trae la paella y el arroz."],
    )
    return entorno


def test_buscar_devuelve_los_trozos_por_relevancia_con_su_pagina(configurado: Entorno) -> None:
    _con_notas(configurado)

    respuesta = configurado.cliente.get(f"{_RUTA}/buscar", params={"q": "  arroz paella  "})

    assert respuesta.status_code == 200
    assert respuesta.json() == [
        {
            "pagina_id": "receta",
            "titulo": "Receta de paella",
            "url": "https://n.so/receta",
            "fragmento": "La paella lleva arroz bomba y azafrán.",
            "orden": 1,
        },
        {
            "pagina_id": "reunion",
            "titulo": "Reunión",
            "url": "https://n.so/reunion",
            "fragmento": "Ana trae la paella y el arroz.",
            "orden": 0,
        },
        {
            "pagina_id": "receta",
            "titulo": "Receta de paella",
            "url": "https://n.so/receta",
            "fragmento": "Receta de paella",
            "orden": 0,
        },
    ]
    assert configurado.repositorio.busquedas == ["arroz paella"]
    # Buscar no usa a Claude.
    assert configurado.modelo.llamadas == []


def test_buscar_limita_a_20_por_defecto_y_admite_de_1_a_50(configurado: Entorno) -> None:
    configurado.repositorio.guardar_pagina(
        PaginaNotion("larga", "Larga", "https://n.so/larga", _EDITADA),
        [f"paella {i}" for i in range(60)],
    )

    def contar(**params: object) -> int:
        respuesta = configurado.cliente.get(f"{_RUTA}/buscar", params={"q": "paella", **params})
        assert respuesta.status_code == 200
        return len(respuesta.json())

    assert contar() == 20
    assert contar(limite=1) == 1
    assert contar(limite=50) == 50


def test_buscar_funciona_sin_credenciales(sin_configurar: Entorno) -> None:
    vacio = sin_configurar.cliente.get(f"{_RUTA}/buscar", params={"q": "paella"})
    assert (vacio.status_code, vacio.json()) == (200, [])

    _con_notas(sin_configurar)
    respuesta = sin_configurar.cliente.get(f"{_RUTA}/buscar", params={"q": "azafrán"})

    assert respuesta.status_code == 200
    assert [r["pagina_id"] for r in respuesta.json()] == ["receta"]


def test_buscar_sin_coincidencias_devuelve_una_lista_vacia(configurado: Entorno) -> None:
    _con_notas(configurado)

    respuesta = configurado.cliente.get(f"{_RUTA}/buscar", params={"q": "dentista"})

    assert (respuesta.status_code, respuesta.json()) == (200, [])


@pytest.mark.parametrize(
    "params",
    [
        {},
        {"q": ""},
        {"q": "   "},
        {"q": " \t"},
        {"q": "x" * 201},
        {"q": "paella", "limite": 0},
        {"q": "paella", "limite": 51},
        {"q": "paella", "limite": "muchos"},
    ],
)
def test_buscar_con_parametros_invalidos_da_422(configurado: Entorno, params: dict) -> None:
    respuesta = configurado.cliente.get(f"{_RUTA}/buscar", params=params)

    assert respuesta.status_code == 422
    assert configurado.repositorio.busquedas == []


def test_buscar_admite_200_caracteres(configurado: Entorno) -> None:
    respuesta = configurado.cliente.get(f"{_RUTA}/buscar", params={"q": "p" * 200})

    assert respuesta.status_code == 200


def test_el_contrato_publica_la_busqueda() -> None:
    rutas = TestClient(crear_aplicacion()).get("/openapi.json").json()["paths"]

    buscar = rutas[f"{_RUTA}/buscar"]
    assert set(buscar) == {"get"}
    parametros = {p["name"]: p for p in buscar["get"]["parameters"]}
    assert parametros["q"]["required"] is True
    assert parametros["q"]["schema"]["maxLength"] == 200
    assert parametros["limite"]["schema"]["minimum"] == 1
    assert parametros["limite"]["schema"]["maximum"] == 50
    assert parametros["limite"]["schema"]["default"] == 20
    assert {"200", "422"} <= set(buscar["get"]["responses"])
