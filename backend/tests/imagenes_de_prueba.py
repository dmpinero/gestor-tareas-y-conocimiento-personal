"""Imágenes mínimas reales (1×1 píxel) de cada tipo admitido, para los tests."""

from base64 import b64decode

PNG = b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="
)
GIF = b64decode("R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7")
WEBP = b64decode("UklGRhoAAABXRUJQVlA4TA0AAAAvAAAAEAcQERGIiP4HAA==")
# Cabecera JFIF, un comentario y el fin de imagen: lo que mira la detección.
JPEG = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00\xff\xd9"

POR_TIPO = {
    "image/png": PNG,
    "image/jpeg": JPEG,
    "image/gif": GIF,
    "image/webp": WEBP,
}
