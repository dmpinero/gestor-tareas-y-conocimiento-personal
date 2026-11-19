from dataclasses import dataclass
from datetime import datetime


@dataclass
class Imagen:
    """Imagen subida para ponerla en los comentarios (capturas de pantalla).

    ``id`` es un identificador difícil de adivinar (UUID4 en hexadecimal) y es
    lo que usa la URL de la imagen. ``tipo`` es el tipo de medio detectado por el
    contenido (no el que dice quien la sube); ``tamano`` son los bytes de
    ``contenido``. ``creada`` es el instante de la subida, en UTC. No se cambia ni
    se borra: varios comentarios (p. ej. los copiados de un paso) pueden usarla.
    """

    id: str
    tipo: str
    contenido: bytes
    creada: datetime

    @property
    def tamano(self) -> int:
        return len(self.contenido)
