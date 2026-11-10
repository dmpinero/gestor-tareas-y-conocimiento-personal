from dataclasses import dataclass


@dataclass
class PasoWorkflowOportunidad:
    """Paso del workflow estándar que se sigue, en orden, en cada oportunidad.

    ``numero`` es la posición del paso (1..n, sin huecos): lo asigna el sistema al
    dar de alta el paso (va al final) y lo recalcula al eliminar o reordenar.
    """

    nombre: str
    numero: int | None = None
    id: int | None = None
