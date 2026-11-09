from typing import Protocol

from gestor_tareas.dominio.etiqueta.entidades import Etiqueta


class RepositorioEtiquetas(Protocol):
    """Puerto de persistencia para el catálogo de etiquetas."""

    def listar(self) -> list[Etiqueta]:
        """Devuelve todas las etiquetas ordenadas por nombre sin distinguir mayúsculas."""
        ...

    def obtener_o_crear(self, nombres: list[str]) -> list[Etiqueta]:
        """Devuelve, en el mismo orden, la etiqueta de cada nombre.

        Reutiliza la que ya exista con ese nombre sin distinguir mayúsculas
        (conservando su grafía) y da de alta las que falten. No confirma la
        transacción: lo hace el repositorio que guarda la tarea.
        """
        ...
