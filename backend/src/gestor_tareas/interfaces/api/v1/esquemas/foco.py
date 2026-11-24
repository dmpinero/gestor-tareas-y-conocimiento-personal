import re
from typing import Annotated

from pydantic import AwareDatetime, BaseModel, BeforeValidator, Field

from gestor_tareas.interfaces.api.v1.esquemas.comentario import InstanteUtc
from gestor_tareas.interfaces.api.v1.esquemas.grupo_estados import IdEntero

# Fecha y hora ISO 8601 con zona (``Z`` u offset); los segundos y su fracción son
# opcionales.
_INSTANTE_ISO_CON_ZONA = re.compile(
    r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(:\d{2}(\.\d+)?)?(Z|[+-]\d{2}:\d{2})", re.IGNORECASE
)


def _solo_texto_iso(valor: object) -> object:
    """Rechaza lo que no sea un instante ISO con zona antes de que Pydantic lo
    interprete (p. ej. ``0.5`` como segundos desde 1970)."""
    if not isinstance(valor, str) or not _INSTANTE_ISO_CON_ZONA.fullmatch(valor):
        raise ValueError("debe ser un instante ISO 8601 con zona, p. ej. 2026-11-24T00:00:00Z")
    return valor


InstanteIsoConZona = Annotated[AwareDatetime, BeforeValidator(_solo_texto_iso)]
"""Límite de un filtro: un instante ISO 8601 con zona, que se pasa a UTC al usarlo."""


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


class PeriodoDeFocoSalidaEsquema(BaseModel):
    """Un periodo del historial del foco."""

    id: int
    tarea_id: int | None = Field(description="Id de la tarea, o null si se borró.")
    tarea_nombre: str = Field(
        description="Nombre actual de la tarea o, si se borró, el que tenía al ponerla en foco."
    )
    subtarea_id: int | None = Field(
        description="Id de la subtarea en foco, o null si el foco era la tarea entera o se "
        "borró la subtarea."
    )
    subtarea_nombre: str | None = Field(
        description="Nombre actual de la subtarea o, si se borró, el que tenía al ponerla en "
        "foco; null si el foco era la tarea entera."
    )
    desde: InstanteUtc = Field(description="Instante en UTC en que empezó el periodo.")
    hasta: InstanteUtc | None = Field(
        description="Instante en UTC en que acabó el periodo, o null si sigue en curso."
    )
