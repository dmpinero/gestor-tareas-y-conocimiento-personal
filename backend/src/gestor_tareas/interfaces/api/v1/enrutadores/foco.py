from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from gestor_tareas.aplicacion.foco.casos_uso import FijarFoco, ObtenerFoco, QuitarFoco
from gestor_tareas.dominio.foco.entidades import Foco
from gestor_tareas.infraestructura.persistencia.repositorios.repositorio_foco_sqlalchemy import (
    RepositorioFocoSqlAlchemy,
)
from gestor_tareas.infraestructura.persistencia.repositorios.repositorio_tareas_sqlalchemy import (
    RepositorioTareasSqlAlchemy,
)
from gestor_tareas.interfaces.api.dependencias import obtener_sesion
from gestor_tareas.interfaces.api.respuestas_error import (
    RESPUESTA_CUERPO_MALFORMADO,
    RESPUESTA_NO_ENCONTRADO,
)
from gestor_tareas.interfaces.api.v1.esquemas.foco import FocoFijarEsquema, FocoSalidaEsquema

enrutador = APIRouter(prefix="/foco", tags=["Foco de trabajo"])


def _a_esquema(foco: Foco) -> FocoSalidaEsquema:
    return FocoSalidaEsquema(
        tarea_id=foco.tarea_id,
        tarea_nombre=foco.tarea_nombre,
        subtarea_id=foco.subtarea_id,
        subtarea_nombre=foco.subtarea_nombre,
        desde=foco.desde,
    )


@enrutador.get("", response_model=FocoSalidaEsquema | None)
def obtener(sesion: Session = Depends(obtener_sesion)) -> FocoSalidaEsquema | None:
    """Devuelve la tarea (o la subtarea) con la que se está trabajando, con sus
    nombres actuales y desde cuándo, o `null` si no hay foco."""
    foco = ObtenerFoco(RepositorioFocoSqlAlchemy(sesion)).ejecutar()
    return _a_esquema(foco) if foco is not None else None


@enrutador.put(
    "",
    response_model=FocoSalidaEsquema,
    responses={**RESPUESTA_NO_ENCONTRADO, **RESPUESTA_CUERPO_MALFORMADO},
)
def fijar(datos: FocoFijarEsquema, sesion: Session = Depends(obtener_sesion)) -> FocoSalidaEsquema:
    """Pone en foco la tarea o, con `subtarea_id`, una subtarea de esa tarea, y la
    devuelve. Solo hay un foco: sustituye al anterior sin avisar, y `desde` vuelve a
    empezar ahora (también si ya estaba en foco). 404 si la tarea no existe o la
    subtarea no es de ella. Completar la tarea no quita el foco; borrarla (o borrar
    la subtarea en foco), sí."""
    foco = FijarFoco(
        RepositorioFocoSqlAlchemy(sesion), RepositorioTareasSqlAlchemy(sesion)
    ).ejecutar(datos.tarea_id, datos.subtarea_id)
    return _a_esquema(foco)


@enrutador.delete("", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
def quitar(sesion: Session = Depends(obtener_sesion)) -> Response:
    """Deja sin foco. Responde 204 también si no había foco."""
    QuitarFoco(RepositorioFocoSqlAlchemy(sesion)).ejecutar()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
