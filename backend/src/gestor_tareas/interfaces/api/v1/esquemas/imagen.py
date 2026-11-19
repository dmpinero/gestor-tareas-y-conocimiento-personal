"""Imágenes de los comentarios: su identificador, su URL y lo que devuelve la API."""

import re

from pydantic import BaseModel, Field

# Prefijo de la API y del enrutador de las imágenes (ver main.py e imagenes.py).
RUTA_IMAGENES = "/api/v1/imagenes"

# Id de una imagen: un UUID4 en hexadecimal sin guiones (32 caracteres en minúscula).
PATRON_ID_IMAGEN = r"^[0-9a-f]{32}$"

# La única URL de imagen que admiten los comentarios: relativa, de esta aplicación.
PATRON_URL_IMAGEN = re.compile(rf"{re.escape(RUTA_IMAGENES)}/[0-9a-f]{{32}}")


def url_de_imagen(id_imagen: str) -> str:
    """URL relativa con la que se descarga la imagen y se pone en un comentario."""
    return f"{RUTA_IMAGENES}/{id_imagen}"


class ImagenSalidaEsquema(BaseModel):
    id: str = Field(pattern=PATRON_ID_IMAGEN, description="Id de la imagen guardada.")
    url: str = Field(
        description="URL relativa de la imagen, para el atributo `src` de un `img` "
        "en el HTML de un comentario.",
        examples=["/api/v1/imagenes/0123456789abcdef0123456789abcdef"],
    )
    tipo: str = Field(description="Tipo de medio detectado por el contenido del archivo.")
    tamano: int = Field(description="Tamaño en bytes.")
