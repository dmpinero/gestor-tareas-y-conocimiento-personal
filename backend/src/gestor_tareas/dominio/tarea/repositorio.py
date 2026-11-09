from typing import Protocol

from gestor_tareas.dominio.tarea.entidades import Tarea


class RepositorioTareas(Protocol):
    """Puerto de persistencia para Tarea."""

    def crear(self, tarea: Tarea) -> Tarea: ...

    def listar(self) -> list[Tarea]:
        """Devuelve todas las tareas ordenadas por id ascendente."""
        ...
