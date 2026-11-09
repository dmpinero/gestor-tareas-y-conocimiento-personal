from typing import Protocol

from gestor_tareas.dominio.tarea.entidades import Tarea


class RepositorioTareas(Protocol):
    """Puerto de persistencia para Tarea."""

    def crear(self, tarea: Tarea) -> Tarea: ...

    def listar(self) -> list[Tarea]:
        """Devuelve todas las tareas ordenadas por id ascendente."""
        ...

    def obtener_por_id(self, id_tarea: int) -> Tarea | None:
        """Devuelve la tarea con ese id, o ``None`` si no existe."""
        ...

    def actualizar(self, tarea: Tarea) -> Tarea:
        """Guarda los datos de una tarea ya existente (``tarea.id`` debe existir)."""
        ...
