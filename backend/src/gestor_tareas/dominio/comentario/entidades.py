from dataclasses import dataclass
from datetime import datetime


@dataclass
class Comentario:
    """Comentario del histórico de una tarea. No tiene autor; se puede editar su
    texto y borrar.

    ``texto`` es obligatorio: HTML ya saneado (hasta 500 caracteres de texto
    visible y 10000 de HTML; lo valida la API). ``creado`` es el instante en que
    se dio de alta y ``editado`` el de su última edición (``None`` si nunca se
    editó); ambos en UTC (con zona horaria) y con precisión de segundos, y los pone
    la aplicación, no la persona usuaria.
    Editar el texto no cambia ``creado``.
    """

    id_tarea: int
    texto: str
    creado: datetime
    editado: datetime | None = None
    id: int | None = None


@dataclass
class ComentarioSubtarea:
    """Comentario del histórico de una subtarea, con las mismas reglas que
    ``Comentario``. Se borra con la subtarea (y con la tarea de la subtarea)."""

    id_tarea: int
    id_subtarea: int
    texto: str
    creado: datetime
    editado: datetime | None = None
    id: int | None = None


@dataclass
class ComentarioPaso:
    """Comentario del histórico de un paso de un workflow, con las mismas reglas que
    ``Comentario``. Se borra con el paso (y con su workflow).

    Al asignar el workflow a una tarea, la subtarea que nace del paso recibe una
    copia de sus comentarios (ver ``WorkflowPedido``); la copia es independiente:
    cambiar uno no cambia el otro.
    """

    id_workflow: int
    id_paso: int
    texto: str
    creado: datetime
    editado: datetime | None = None
    id: int | None = None
