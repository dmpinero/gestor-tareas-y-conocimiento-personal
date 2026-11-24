from pydantic import BaseModel, Field

from gestor_tareas.interfaces.api.v1.esquemas.comentario import InstanteUtc
from gestor_tareas.interfaces.api.v1.esquemas.grupo_estados import IdEntero


class FocoFijarEsquema(BaseModel):
    """Cuerpo para poner en foco una tarea o una subtarea de esa tarea."""

    tarea_id: IdEntero = Field(description="Obligatorio. Id de la tarea.")
    subtarea_id: IdEntero | None = Field(
        default=None,
        description="Opcional. Id de una subtarea de la tarea, o null para la tarea entera.",
    )


class FocoSalidaEsquema(BaseModel):
    tarea_id: int
    tarea_nombre: str
    subtarea_id: int | None = Field(description="Id de la subtarea en foco, o null.")
    subtarea_nombre: str | None
    desde: InstanteUtc = Field(
        description="Instante en UTC en que se fijó el foco; vuelve a empezar en cada PUT."
    )
