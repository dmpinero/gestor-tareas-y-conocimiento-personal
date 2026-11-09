from dataclasses import dataclass


@dataclass(frozen=True)
class Etiqueta:
    """Etiqueta del catálogo compartido. El nombre es único sin distinguir mayúsculas."""

    id: int
    nombre: str
