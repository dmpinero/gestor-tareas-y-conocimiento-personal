from dataclasses import dataclass
from datetime import datetime


@dataclass
class Comentario:
    """Comentario del histórico de una tarea. No tiene autor y no se edita ni se borra.

    ``texto`` es obligatorio (hasta 500 caracteres, con los saltos de línea que
    tenga). ``creado`` es el instante en que se dio de alta, en UTC (con zona
    horaria) y con precisión de segundos; lo pone la aplicación, no la persona
    usuaria.
    """

    id_tarea: int
    texto: str
    creado: datetime
    id: int | None = None
