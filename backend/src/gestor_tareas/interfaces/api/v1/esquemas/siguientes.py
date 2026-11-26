from typing import Annotated

from pydantic import AfterValidator, BaseModel, Field

from gestor_tareas.interfaces.api.v1.esquemas.grupo_estados import IdEntero


def _sin_repetidos(ids: list[int]) -> list[int]:
    if len(set(ids)) != len(ids):
        raise ValueError("El orden no puede repetir tareas.")
    return ids


class SiguienteAnadirEsquema(BaseModel):
    """Cuerpo para añadir una tarea al final de la cola de siguientes."""

    tarea_id: IdEntero = Field(description="Obligatorio. Id de una tarea no completada.")


class OrdenSiguientesEsquema(BaseModel):
    """Cuerpo de la reordenación: los ids de todas las tareas de la cola en su orden."""

    ids: Annotated[list[IdEntero], AfterValidator(_sin_repetidos)] = Field(
        json_schema_extra={"uniqueItems": True},
        description=(
            "Ids de todas las tareas de la cola (las que devuelve `GET /siguientes`) en el "
            "nuevo orden: cada una exactamente una vez. Si falta alguna, se repite o no "
            "está en la cola, 422."
        ),
    )


class TareaSiguienteEsquema(BaseModel):
    """Una tarea de la cola de siguientes."""

    tarea_id: int
    tarea_nombre: str = Field(description="Nombre actual de la tarea.")
