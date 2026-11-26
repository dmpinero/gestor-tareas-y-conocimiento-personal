"""Adaptador de ``ModeloLenguaje`` con Claude (SDK oficial de Anthropic).

Usa ``claude-opus-5-5`` en streaming con esfuerzo bajo (es un chat) y el
*fallback* del servidor (``fallbacks="default"``, beta
``server-side-fallback-2026-07-01``): si el modelo rechaza la petición, la API la
repite con el modelo de respaldo recomendado dentro de la misma llamada. Si aun así
termina con ``stop_reason`` ``refusal``, se lanza ``RespuestaRechazadaError``. El
razonamiento de este modelo no se puede desactivar, así que no se envía
``thinking``.

Los errores del SDK se traducen a ``ModeloNoDisponibleError`` con un mensaje en
español que nunca incluye la clave.
"""

from collections.abc import Iterator, Sequence

import anthropic

from gestor_tareas.dominio.conocimiento.entidades import MensajeChat, Rol
from gestor_tareas.dominio.conocimiento.errores import (
    ModeloNoDisponibleError,
    RespuestaRechazadaError,
)

MODELO = "claude-opus-5-5"
_BETA_FALLBACK = "server-side-fallback-2026-07-01"
_MAX_TOKENS = 4096
_ROLES = {Rol.USUARIO: "user", Rol.ASISTENTE: "assistant"}


class ModeloAnthropic:
    """Claude como modelo de lenguaje de Conocimiento."""

    def __init__(self, cliente: anthropic.Anthropic) -> None:
        self._cliente = cliente

    @classmethod
    def crear(cls, clave: str) -> "ModeloAnthropic":
        """Con un cliente del SDK para la clave ``clave`` (la de la configuración)."""
        return cls(
            anthropic.Anthropic(
                api_key=clave,
                timeout=anthropic.Timeout(120.0, connect=10.0),
                max_retries=2,
            )
        )

    def responder(self, sistema: str, mensajes: Sequence[MensajeChat]) -> Iterator[str]:
        try:
            with self._cliente.beta.messages.stream(
                model=MODELO,
                max_tokens=_MAX_TOKENS,
                system=sistema,
                messages=[{"role": _ROLES[m.rol], "content": m.texto} for m in mensajes],
                output_config={"effort": "low"},
                betas=[_BETA_FALLBACK],
                fallbacks="default",
            ) as flujo:
                yield from flujo.text_stream
                final = flujo.get_final_message()
        except anthropic.AuthenticationError as error:
            raise ModeloNoDisponibleError(
                "Claude ha rechazado ANTHROPIC_API_KEY: revisa la clave en backend/.env."
            ) from error
        except anthropic.RateLimitError as error:
            raise ModeloNoDisponibleError(
                "Se ha alcanzado el límite de uso de Claude; inténtalo de nuevo en un rato."
            ) from error
        except anthropic.APIStatusError as error:
            raise ModeloNoDisponibleError(
                f"Claude ha respondido con un error ({error.status_code}); "
                "inténtalo de nuevo en un rato."
            ) from error
        except anthropic.APIConnectionError as error:
            raise ModeloNoDisponibleError("No se ha podido conectar con Claude.") from error
        if final.stop_reason == "refusal":
            raise RespuestaRechazadaError("Claude no ha querido responder a esa pregunta.")
