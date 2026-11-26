from typing import Annotated

from pydantic import AfterValidator, BaseModel, Field

from gestor_tareas.dominio.codigo_servicio.entidades import (
    PATRON_CODIGO_SERVICIO,
    validar_nombre_codigo_servicio,
)
from gestor_tareas.interfaces.api.v1.esquemas.texto import PATRON_NO_VACIO, TextoObligatorio

# Nombre de un subestado: las mismas reglas que el de una etiqueta (1–50 caracteres
# tras recortar los espacios de los extremos y `pattern: "\\S"` en el contrato).
NombreSubestado = Annotated[
    TextoObligatorio, Field(min_length=1, max_length=50, json_schema_extra=PATRON_NO_VACIO)
]

# Nombre de un código de servicio: se recorta y la regla del dominio comprueba la
# longitud (2–20) y que no tenga espacios, con mensajes en español. El contrato
# publica esas mismas reglas en el `pattern` (que admite los espacios de los
# extremos, porque se recortan).
NombreCodigoServicio = Annotated[
    TextoObligatorio,
    AfterValidator(validar_nombre_codigo_servicio),
    Field(json_schema_extra={"pattern": PATRON_CODIGO_SERVICIO}),
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


class CodigoServicioEsquema(BaseModel):
    """Cuerpo del alta y del cambio de nombre de un código de servicio."""

    nombre: NombreCodigoServicio


class CodigoServicioSalidaEsquema(BaseModel):
    id: int
    nombre: str
