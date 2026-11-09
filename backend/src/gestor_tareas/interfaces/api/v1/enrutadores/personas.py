from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from gestor_tareas.aplicacion.persona.listar_personas import ListarPersonas
from gestor_tareas.infraestructura.persistencia.repositorios.repositorios_catalogos_sqlalchemy import (  # noqa: E501
    RepositorioPersonasSqlAlchemy,
)
from gestor_tareas.interfaces.api.dependencias import obtener_sesion
from gestor_tareas.interfaces.api.v1.esquemas.catalogos import PersonaSalidaEsquema

enrutador = APIRouter(prefix="/personas", tags=["Personas"])


@enrutador.get("", response_model=list[PersonaSalidaEsquema])
def listar(sesion: Session = Depends(obtener_sesion)) -> list[PersonaSalidaEsquema]:
    """Devuelve el catálogo de personas ordenado por nombre sin distinguir mayúsculas."""
    personas = ListarPersonas(RepositorioPersonasSqlAlchemy(sesion)).ejecutar()
    return [PersonaSalidaEsquema(id=p.id, nombre=p.nombre) for p in personas]
