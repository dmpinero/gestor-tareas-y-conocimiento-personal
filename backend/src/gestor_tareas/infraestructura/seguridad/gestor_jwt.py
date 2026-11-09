from datetime import UTC, datetime, timedelta
from typing import Any

import jwt

from gestor_tareas.configuracion import obtener_configuracion

configuracion = obtener_configuracion()


class TokenInvalidoError(Exception):
    """Se lanza cuando un token JWT no es válido o ha caducado."""


def crear_token_acceso(datos: dict[str, Any]) -> str:
    """Crea un token JWT de acceso firmado con la clave secreta de la aplicación."""
    expiracion = datetime.now(UTC) + timedelta(minutes=configuracion.minutos_expiracion_token)
    payload = {**datos, "exp": expiracion}
    return jwt.encode(
        payload, configuracion.clave_secreta_jwt, algorithm=configuracion.algoritmo_jwt
    )


def decodificar_token_acceso(token: str) -> dict[str, Any]:
    """Decodifica y valida un token JWT, lanzando TokenInvalidoError si no es válido."""
    try:
        return jwt.decode(
            token,
            configuracion.clave_secreta_jwt,
            algorithms=[configuracion.algoritmo_jwt],
        )
    except jwt.PyJWTError as error:
        raise TokenInvalidoError("El token de acceso no es válido o ha caducado") from error
