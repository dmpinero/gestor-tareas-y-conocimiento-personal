from typing import Annotated

from pydantic import AfterValidator, BaseModel, BeforeValidator, Field

from gestor_tareas.interfaces.api.v1.esquemas.texto import PATRON_NO_VACIO, TextoObligatorio

NombreWorkflowOPaso = Annotated[
    TextoObligatorio,
    Field(
        min_length=1,
        max_length=50,
        json_schema_extra=PATRON_NO_VACIO,
        description="Se guarda sin los espacios de los extremos.",
    ),
]


class WorkflowEsquema(BaseModel):
    """Cuerpo del alta y del cambio de nombre de un workflow."""

    nombre: NombreWorkflowOPaso


class PasoWorkflowEsquema(BaseModel):
    """Cuerpo del alta y del cambio de nombre de un paso de un workflow."""

    nombre: NombreWorkflowOPaso


def _normalizar_entero(valor: object) -> object:
    """Aplica la semántica de `integer` de JSON Schema.

    `3.0` es un entero válido y se convierte en 3; los booleanos no son enteros
    (en Python `True` es un `int`). El resto lo valida `int` en modo estricto, que
    rechaza cadenas como `"2"` y `2.5`.
    """
    if isinstance(valor, bool):
        raise ValueError("El id del paso debe ser un número entero.")
    if isinstance(valor, float) and valor.is_integer():
        return int(valor)
    return valor


def _sin_repetidos(ids: list[int]) -> list[int]:
    if len(set(ids)) != len(ids):
        raise ValueError("El orden no puede repetir pasos.")
    return ids


IdPaso = Annotated[int, Field(strict=True), BeforeValidator(_normalizar_entero)]


class OrdenPasosEsquema(BaseModel):
    """Cuerpo de la reordenación: los ids de todos los pasos en su nuevo orden."""

    ids: Annotated[list[IdPaso], AfterValidator(_sin_repetidos)] = Field(
        json_schema_extra={"uniqueItems": True},
        description=(
            "Ids de todos los pasos del workflow en el nuevo orden: cada uno exactamente "
            "una vez. Si falta alguno, se repite o no es del workflow, 422."
        ),
    )


class PasoWorkflowSalidaEsquema(BaseModel):
    id: int
    numero: int
    nombre: str


class WorkflowSalidaEsquema(BaseModel):
    id: int
    nombre: str
    pasos: list[PasoWorkflowSalidaEsquema] = Field(description="Pasos por número (1..n).")


class WorkflowDeTareaEsquema(BaseModel):
    id: int
    nombre: str
