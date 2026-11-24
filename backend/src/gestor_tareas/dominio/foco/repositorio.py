from datetime import datetime
from typing import Protocol

from gestor_tareas.dominio.foco.entidades import Foco


class RepositorioFoco(Protocol):
    """Puerto de persistencia del foco de trabajo (como mucho uno)."""

    def obtener(self) -> Foco | None:
        """Devuelve el foco actual con los nombres actuales de su tarea y su subtarea,
        o ``None`` si no hay foco."""
        ...

    def fijar(self, id_tarea: int, id_subtarea: int | None, desde: datetime) -> Foco:
        """Pone en foco la tarea (o su subtarea) desde ese instante, sustituyendo al
        foco anterior si lo había, y confirma. La subtarea debe ser de la tarea.

        Lanza ``EntidadNoEncontradaError`` si la tarea o la subtarea ya no existen
        (p. ej. otra petición las ha borrado); el foco anterior no cambia."""
        ...

    def quitar(self) -> None:
        """Deja sin foco y confirma. No hace nada si no había foco."""
        ...
