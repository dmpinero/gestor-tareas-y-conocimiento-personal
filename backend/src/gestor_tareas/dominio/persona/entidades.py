from dataclasses import dataclass


@dataclass(frozen=True)
class Persona:
    """Persona a la que se asignan tareas: solo un nombre, sin email ni acceso.

    Forma parte de un catálogo compartido; el nombre es único sin distinguir
    mayúsculas.
    """

    id: int
    nombre: str
