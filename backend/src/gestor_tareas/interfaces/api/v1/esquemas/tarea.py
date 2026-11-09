from pydantic import BaseModel, ConfigDict, Field


class TareaCrearEsquema(BaseModel):
    # Se recortan los espacios antes de validar: un nombre o una descripción
    # formados solo por espacios quedan vacíos y se rechazan con 422.
    model_config = ConfigDict(str_strip_whitespace=True)

    nombre: str = Field(min_length=1, max_length=200)
    prioridad: int | None = Field(default=None, ge=1, le=5)
    descripcion: str = Field(min_length=1, max_length=500)


class TareaSalidaEsquema(BaseModel):
    id: int
    nombre: str
    prioridad: int | None
    descripcion: str
