from typing import Protocol

from gestor_tareas.dominio.imagen.entidades import Imagen


class RepositorioImagenes(Protocol):
    """Puerto de persistencia para las imágenes de los comentarios."""

    def guardar(self, imagen: Imagen) -> None:
        """Guarda una imagen nueva."""
        ...

    def obtener(self, id_imagen: str) -> Imagen | None:
        """Devuelve la imagen con ese id, o ``None`` si no existe."""
        ...
