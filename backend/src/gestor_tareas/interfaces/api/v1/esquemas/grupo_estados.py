from typing import Annotated

from pydantic import AfterValidator, BaseModel, BeforeValidator, Field

from gestor_tareas.interfaces.api.v1.esquemas.texto import PATRON_NO_VACIO, TextoObligatorio


def _normalizar_id(valor: object) -> object:
    """Aplica la semántica de `integer` de JSON Schema a un id.

    `3.0` es un entero válido y se convierte en 3; los booleanos no son enteros (en
    Python `True` es un `int`). El resto lo valida `int` en modo estricto, que
    rechaza cadenas como `"2"` y `2.5`.
    """
    if isinstance(valor, bool):
        raise ValueError("El id debe ser un número entero.")
    if isinstance(valor, float) and valor.is_integer():
        return int(valor)
    return valor


# Las restricciones van antes del `BeforeValidator` (ver `PrioridadEntera`).
IdEntero = Annotated[int, Field(strict=True), BeforeValidator(_normalizar_id)]

NombreGrupoOEstado = Annotated[
    TextoObligatorio,
    Field(
        min_length=1,
        max_length=50,
        json_schema_extra=PATRON_NO_VACIO,
        description="Se guarda sin los espacios de los extremos.",
    ),
]


class GrupoEstadosEsquema(BaseModel):
    """Cuerpo del alta y del cambio de nombre de un grupo de estados."""

    nombre: NombreGrupoOEstado


class EstadoGrupoEsquema(BaseModel):
    """Cuerpo del alta y del cambio de nombre de un estado de un grupo."""

    nombre: NombreGrupoOEstado


def _sin_repetidos(ids: list[int]) -> list[int]:
    if len(set(ids)) != len(ids):
        raise ValueError("El orden no puede repetir estados.")
    return ids


class OrdenEstadosEsquema(BaseModel):
    """Cuerpo de la reordenación: los ids de todos los estados del grupo en su orden."""

    ids: Annotated[list[IdEntero], AfterValidator(_sin_repetidos)] = Field(
        json_schema_extra={"uniqueItems": True},
        description=(
            "Ids de todos los estados del grupo en el nuevo orden: cada uno exactamente "
            "una vez. Si falta alguno, se repite o no es del grupo, 422."
        ),
    )


class EstadoGrupoSalidaEsquema(BaseModel):
    id: int
    nombre: str
    posicion: int = Field(description="Posición del estado en el grupo (1..n).")
    tareas: int = Field(description="Número de tareas en el estado.")


class GrupoEstadosSalidaEsquema(BaseModel):
    id: int
    nombre: str
    tareas: int = Field(description="Número de tareas del grupo.")
    estados: list[EstadoGrupoSalidaEsquema] = Field(description="Estados por posición.")


class TareaEstadoEsquema(BaseModel):
    """Cuerpo del cambio de estado de una tarea: un estado de su grupo."""

    estado_id: IdEntero


class GrupoEstadosDeTareaEsquema(BaseModel):
    id: int
    nombre: str


class EstadoDeTareaEsquema(BaseModel):
    id: int
    nombre: str
