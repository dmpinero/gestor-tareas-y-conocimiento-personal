from typing import Annotated

from pydantic import BaseModel, Field

from gestor_tareas.interfaces.api.v1.esquemas.texto import PATRON_NO_VACIO, TextoObligatorio

# Nombre de un subestado: las mismas reglas que el de una etiqueta (1–50 caracteres
# tras recortar los espacios de los extremos y `pattern: "\\S"` en el contrato).
NombreSubestado = Annotated[
    TextoObligatorio, Field(min_length=1, max_length=50, json_schema_extra=PATRON_NO_VACIO)
]


class EtiquetaSalidaEsquema(BaseModel):
    id: int
    nombre: str


class PersonaSalidaEsquema(BaseModel):
    id: int
    nombre: str


class SubestadoEsquema(BaseModel):
    """Cuerpo del alta y del cambio de nombre de un subestado."""

    nombre: NombreSubestado


class SubestadoSalidaEsquema(BaseModel):
    id: int
    nombre: str
