from typing import Protocol

from gestor_tareas.dominio.persona.entidades import Persona


class RepositorioPersonas(Protocol):
    """Puerto de persistencia para el catálogo de personas."""

    def listar(self) -> list[Persona]:
        """Devuelve todas las personas ordenadas por nombre sin distinguir mayúsculas."""
        ...

    def obtener_o_crear(self, nombres: list[str]) -> list[Persona]:
        """Devuelve, en el mismo orden, la persona de cada nombre.

        Reutiliza la que ya exista con ese nombre sin distinguir mayúsculas
        (conservando su grafía) y da de alta las que falten. No confirma la
        transacción: lo hace el repositorio que guarda la tarea.
        """
        ...
