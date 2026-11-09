from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from gestor_tareas.aplicacion.etiqueta.listar_etiquetas import ListarEtiquetas
from gestor_tareas.infraestructura.persistencia.repositorios.repositorios_catalogos_sqlalchemy import (  # noqa: E501
    RepositorioEtiquetasSqlAlchemy,
)
from gestor_tareas.interfaces.api.dependencias import obtener_sesion
from gestor_tareas.interfaces.api.v1.esquemas.catalogos import EtiquetaSalidaEsquema

enrutador = APIRouter(prefix="/etiquetas", tags=["Etiquetas"])


@enrutador.get("", response_model=list[EtiquetaSalidaEsquema])
def listar(sesion: Session = Depends(obtener_sesion)) -> list[EtiquetaSalidaEsquema]:
    """Devuelve el catálogo de etiquetas ordenado por nombre sin distinguir mayúsculas."""
    etiquetas = ListarEtiquetas(RepositorioEtiquetasSqlAlchemy(sesion)).ejecutar()
    return [EtiquetaSalidaEsquema(id=e.id, nombre=e.nombre) for e in etiquetas]
