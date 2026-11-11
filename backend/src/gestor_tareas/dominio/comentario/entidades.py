from dataclasses import dataclass
from datetime import datetime


@dataclass
class Comentario:
    """Comentario del histórico de una tarea. No tiene autor; se puede editar su
    texto y borrar.

    ``texto`` es obligatorio (hasta 500 caracteres, con los saltos de línea que
    tenga). ``creado`` es el instante en que se dio de alta y ``editado`` el de su
    última edición (``None`` si nunca se editó); ambos en UTC (con zona horaria) y
    con precisión de segundos, y los pone la aplicación, no la persona usuaria.
    Editar el texto no cambia ``creado``.
    """

    id_tarea: int
    texto: str
    creado: datetime
    editado: datetime | None = None
    id: int | None = None
