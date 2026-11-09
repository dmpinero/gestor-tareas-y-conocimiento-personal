from pydantic import BaseModel


class EtiquetaSalidaEsquema(BaseModel):
    id: int
    nombre: str


class PersonaSalidaEsquema(BaseModel):
    id: int
    nombre: str
