"""Qué se admite como imagen de un comentario: PNG, JPEG, GIF y WebP de hasta 5 MB.

El tipo se reconoce por la firma del contenido, no por el nombre ni por el tipo
que declara quien lo sube.
"""

TAMANO_MAXIMO = 5 * 1024 * 1024

_FIRMAS = (
    (b"\x89PNG\r\n\x1a\n", "image/png"),
    (b"\xff\xd8\xff", "image/jpeg"),
    (b"GIF87a", "image/gif"),
    (b"GIF89a", "image/gif"),
)


def detectar_tipo(contenido: bytes) -> str | None:
    """El tipo de medio de la imagen según su firma, o ``None`` si no es de un tipo
    admitido."""
    for firma, tipo in _FIRMAS:
        if contenido.startswith(firma):
            return tipo
    # WebP: contenedor RIFF ("RIFF", 4 bytes de tamaño, "WEBP").
    if len(contenido) >= 12 and contenido[:4] == b"RIFF" and contenido[8:12] == b"WEBP":
        return "image/webp"
    return None
