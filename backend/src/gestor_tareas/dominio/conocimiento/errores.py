class ConocimientoSinConfigurarError(Exception):
    """Falta una credencial del backend (``NOTION_TOKEN`` o ``ANTHROPIC_API_KEY``)."""


class SincronizacionEnCursoError(Exception):
    """Ya hay una sincronización con Notion en curso: solo puede haber una a la vez."""


class NotionNoDisponibleError(Exception):
    """Notion no ha respondido o ha respondido con un error. El mensaje nunca
    incluye el token."""


class ModeloNoDisponibleError(Exception):
    """El modelo de lenguaje no ha podido responder (red, credenciales, límites...).
    El mensaje, en español, se le muestra al usuario y nunca incluye la clave."""


class RespuestaRechazadaError(Exception):
    """El modelo de lenguaje se ha negado a responder (``stop_reason`` ``refusal``)."""
