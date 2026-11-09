from collections.abc import Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

# Cabeceras recomendadas por el checklist de seguridad OWASP para APIs REST.
_CABECERAS_SEGURIDAD = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Strict-Transport-Security": "max-age=63072000; includeSubDomains",
    "Content-Security-Policy": "default-src 'none'; frame-ancestors 'none'",
    "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
}

# La documentación interactiva de FastAPI (Swagger UI / ReDoc) carga su CSS y
# JS desde un CDN externo; el CSP estricto pensado para las respuestas JSON de
# la API bloquearía esos recursos y dejaría la página en blanco.
_RUTAS_DOCUMENTACION = {"/docs", "/redoc", "/openapi.json"}


class MiddlewareCabecerasSeguridad(BaseHTTPMiddleware):
    """Añade cabeceras HTTP de seguridad a toda respuesta de la API."""

    async def dispatch(
        self, request: Request, siguiente: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        respuesta = await siguiente(request)
        es_documentacion = request.url.path in _RUTAS_DOCUMENTACION
        for cabecera, valor in _CABECERAS_SEGURIDAD.items():
            if cabecera == "Content-Security-Policy" and es_documentacion:
                continue
            respuesta.headers[cabecera] = valor
        return respuesta
