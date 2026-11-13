from dataclasses import dataclass, field


@dataclass
class PasoWorkflow:
    """Paso de un workflow, que se sigue en orden.

    ``numero`` es la posición del paso en su workflow (1..n, sin huecos): lo asigna
    el sistema al dar de alta el paso (va al final) y lo recalcula al eliminar o
    reordenar.
    """

    nombre: str
    numero: int | None = None
    id: int | None = None


@dataclass
class Workflow:
    """Conjunto de pasos con nombre que se añaden como subtareas a una tarea.

    ``pasos`` va por número. Las tareas guardan una copia de los pasos (sus
    subtareas): cambiar el workflow después no las altera.
    """

    nombre: str
    pasos: list[PasoWorkflow] = field(default_factory=list)
    id: int | None = None
