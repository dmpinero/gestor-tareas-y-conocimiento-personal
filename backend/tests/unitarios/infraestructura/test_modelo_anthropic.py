"""Adaptador de Claude con el SDK oficial, con la API servida por un transporte
simulado (``httpx2``, el cliente HTTP del SDK): nunca sale a la red."""

import json
from collections.abc import Callable

import anthropic
import httpx2
import pytest

from gestor_tareas.dominio.conocimiento.entidades import MensajeChat, Rol
from gestor_tareas.dominio.conocimiento.errores import (
    ModeloNoDisponibleError,
    RespuestaRechazadaError,
)
from gestor_tareas.infraestructura.llm.modelo_anthropic import ModeloAnthropic

_CLAVE = "sk-ant-clave-de-prueba"


def _sse(eventos: list[dict]) -> bytes:
    return "".join(f"event: {e['type']}\ndata: {json.dumps(e)}\n\n" for e in eventos).encode()


def _flujo(textos: list[str], stop_reason: str) -> bytes:
    eventos: list[dict] = [
        {
            "type": "message_start",
            "message": {
                "id": "msg_1",
                "type": "message",
                "role": "assistant",
                "model": "claude-opus-5-5",
                "content": [],
                "stop_reason": None,
                "stop_sequence": None,
                "usage": {"input_tokens": 10, "output_tokens": 1},
            },
        },
        {"type": "content_block_start", "index": 0, "content_block": {"type": "text", "text": ""}},
        *(
            {"type": "content_block_delta", "index": 0, "delta": {"type": "text_delta", "text": t}}
            for t in textos
        ),
        {"type": "content_block_stop", "index": 0},
        {
            "type": "message_delta",
            "delta": {"stop_reason": stop_reason, "stop_sequence": None},
            "usage": {"output_tokens": 5},
        },
        {"type": "message_stop"},
    ]
    return _sse(eventos)


class _Api:
    def __init__(self, responder: Callable[[httpx2.Request], httpx2.Response]) -> None:
        self.peticiones: list[httpx2.Request] = []
        self._responder = responder

    def __call__(self, peticion: httpx2.Request) -> httpx2.Response:
        self.peticiones.append(peticion)
        return self._responder(peticion)


def _modelo(api: _Api) -> ModeloAnthropic:
    cliente = anthropic.Anthropic(
        api_key=_CLAVE,
        http_client=httpx2.Client(transport=httpx2.MockTransport(api)),
        max_retries=0,
    )
    return ModeloAnthropic(cliente)


def _respuesta_sse(cuerpo: bytes) -> Callable[[httpx2.Request], httpx2.Response]:
    return lambda _: httpx2.Response(
        200, headers={"content-type": "text/event-stream"}, content=cuerpo
    )


_MENSAJES = [
    MensajeChat(Rol.USUARIO, "Hola"),
    MensajeChat(Rol.ASISTENTE, "Hola, ¿qué buscas?"),
    MensajeChat(Rol.USUARIO, "La receta de la paella"),
]


def test_devuelve_el_texto_en_trozos_y_pide_opus_con_fallback_y_esfuerzo_bajo() -> None:
    api = _Api(_respuesta_sse(_flujo(["La paella ", "lleva arroz."], "end_turn")))

    trozos = list(_modelo(api).responder("Instrucciones", _MENSAJES))

    assert trozos == ["La paella ", "lleva arroz."]
    (peticion,) = api.peticiones
    assert peticion.url.path == "/v1/messages"
    assert "server-side-fallback-2026-07-01" in peticion.headers["anthropic-beta"]
    cuerpo = json.loads(peticion.content)
    assert cuerpo["model"] == "claude-opus-5-5"
    assert cuerpo["fallbacks"] == "default"
    assert cuerpo["output_config"] == {"effort": "low"}
    assert cuerpo["stream"] is True
    assert cuerpo["system"] == "Instrucciones"
    assert "thinking" not in cuerpo
    assert 4096 <= cuerpo["max_tokens"] <= 8000
    assert cuerpo["messages"] == [
        {"role": "user", "content": "Hola"},
        {"role": "assistant", "content": "Hola, ¿qué buscas?"},
        {"role": "user", "content": "La receta de la paella"},
    ]


def test_si_claude_se_niega_lanza_respuesta_rechazada_tras_lo_que_haya_escrito() -> None:
    api = _Api(_respuesta_sse(_flujo(["Empiezo"], "refusal")))
    respuesta = _modelo(api).responder("Instrucciones", _MENSAJES)

    assert next(respuesta) == "Empiezo"
    with pytest.raises(RespuestaRechazadaError):
        next(respuesta)


@pytest.mark.parametrize(
    ("codigo", "tipo", "mensaje"),
    [
        (401, "authentication_error", "ANTHROPIC_API_KEY"),
        (429, "rate_limit_error", "límite"),
        (529, "overloaded_error", "(529)"),
        (400, "invalid_request_error", "(400)"),
    ],
)
def test_los_errores_de_la_api_dan_un_error_claro_sin_la_clave(
    codigo: int, tipo: str, mensaje: str
) -> None:
    api = _Api(
        lambda _: httpx2.Response(
            codigo,
            json={"type": "error", "error": {"type": tipo, "message": f"x {_CLAVE}"}},
        )
    )

    with pytest.raises(ModeloNoDisponibleError) as error:
        list(_modelo(api).responder("Instrucciones", _MENSAJES))

    assert mensaje in str(error.value)
    assert _CLAVE not in str(error.value)


def test_sin_conexion_da_un_error_claro() -> None:
    def sin_red(peticion: httpx2.Request) -> httpx2.Response:
        raise httpx2.ConnectError("sin red", request=peticion)

    with pytest.raises(ModeloNoDisponibleError, match="No se ha podido conectar con Claude"):
        list(_modelo(_Api(sin_red)).responder("Instrucciones", _MENSAJES))


def test_crear_construye_el_cliente_con_la_clave_indicada() -> None:
    modelo = ModeloAnthropic.crear(_CLAVE)

    assert isinstance(modelo, ModeloAnthropic)
    assert modelo._cliente.api_key == _CLAVE
