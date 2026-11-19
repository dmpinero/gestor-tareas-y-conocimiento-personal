from dataclasses import dataclass


@dataclass(frozen=True)
class Subestado:
    """Subestado del catálogo compartido. El nombre es único sin distinguir mayúsculas.

    Una tarea tiene como mucho un subestado (opcional)."""

    id: int
    nombre: str
