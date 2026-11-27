from typing import Annotated

from pydantic import AfterValidator, BaseModel, Field

from gestor_tareas.interfaces.api.v1.esquemas.grupo_estados import IdEntero


class EntradaSiguienteEsquema(BaseModel):
    """Una entrada de la cola de siguientes o de las sugerencias elegidas: una tarea
    entera (sin `subtarea_id` o con `null`) o una subtarea suya."""

    tarea_id: IdEntero = Field(description="Obligatorio. Id de la tarea.")
    subtarea_id: IdEntero | None = Field(
        default=None,
        description="Id de una subtarea de la tarea; sin él (o `null`), la tarea entera.",
    )


def _sin_repetidas(entradas: list[EntradaSiguienteEsquema]) -> list[EntradaSiguienteEsquema]:
    claves = [(e.tarea_id, e.subtarea_id) for e in entradas]
    if len(set(claves)) != len(claves):
        raise ValueError("El orden no puede repetir entradas.")
    return entradas


class SiguienteAnadirEsquema(EntradaSiguienteEsquema):
    """Cuerpo para añadir una entrada (una tarea no completada, o una subtarea no
    resuelta suya) al final de la cola de siguientes o de las sugerencias
    elegidas."""


class OrdenSiguientesEsquema(BaseModel):
    """Cuerpo de la reordenación: todas las entradas de la cola en su orden."""

    entradas: Annotated[list[EntradaSiguienteEsquema], AfterValidator(_sin_repetidas)] = Field(
        json_schema_extra={"uniqueItems": True},
        description=(
            "Todas las entradas de la cola (las que devuelve `GET /siguientes`) en el "
            "nuevo orden: cada una exactamente una vez. Si falta alguna, se repite o no "
            "está en la cola, 422."
        ),
    )


class TareaSiguienteEsquema(BaseModel):
    """Una entrada de la cola de siguientes o de las sugerencias elegidas: una tarea
    entera (`subtarea_id` y `subtarea_nombre` a `null`) o una subtarea suya."""

    tarea_id: int
    tarea_nombre: str = Field(description="Nombre actual de la tarea.")
    subtarea_id: int | None = Field(description="Id de la subtarea; `null` en una tarea entera.")
    subtarea_nombre: str | None = Field(
        description="Nombre actual de la subtarea; `null` en una tarea entera."
    )
