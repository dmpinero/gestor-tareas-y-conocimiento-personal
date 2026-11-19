class ImagenNoAdmitidaError(Exception):
    """Se lanza al subir un archivo que no es una imagen PNG, JPEG, GIF o WebP."""


class ImagenDemasiadoGrandeError(Exception):
    """Se lanza al subir una imagen que pasa del tamaño máximo."""
