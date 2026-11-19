from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from gestor_tareas.aplicacion.subestado.casos_uso import (
    CrearSubestado,
    EliminarSubestado,
    ListarSubestados,
    RenombrarSubestado,
)
from gestor_tareas.dominio.subestado.entidades import Subestado
from gestor_tareas.infraestructura.persistencia.repositorios.repositorios_catalogos_sqlalchemy import (  # noqa: E501
    RepositorioSubestadosSqlAlchemy,
)
from gestor_tareas.interfaces.api.dependencias import obtener_sesion
from gestor_tareas.interfaces.api.respuestas_error import (
    RESPUESTA_CONFLICTO,
    RESPUESTA_CUERPO_MALFORMADO,
    RESPUESTA_NO_ENCONTRADO,
)
from gestor_tareas.interfaces.api.v1.esquemas.catalogos import (
    SubestadoEsquema,
    SubestadoSalidaEsquema,
)

enrutador = APIRouter(prefix="/subestados", tags=["Subestados"])


def _a_esquema(subestado: Subestado) -> SubestadoSalidaEsquema:
    return SubestadoSalidaEsquema(id=subestado.id, nombre=subestado.nombre)


def _repositorio(sesion: Session) -> RepositorioSubestadosSqlAlchemy:
    return RepositorioSubestadosSqlAlchemy(sesion)


@enrutador.get("", response_model=list[SubestadoSalidaEsquema])
def listar(sesion: Session = Depends(obtener_sesion)) -> list[SubestadoSalidaEsquema]:
    """Devuelve el catálogo de subestados ordenado por nombre sin distinguir mayúsculas."""
    return [_a_esquema(s) for s in ListarSubestados(_repositorio(sesion)).ejecutar()]


@enrutador.post(
    "",
    response_model=SubestadoSalidaEsquema,
    status_code=status.HTTP_201_CREATED,
    responses={**RESPUESTA_CONFLICTO, **RESPUESTA_CUERPO_MALFORMADO},
)
def crear(
    datos: SubestadoEsquema, sesion: Session = Depends(obtener_sesion)
) -> SubestadoSalidaEsquema:
    """Da de alta un subestado. El nombre es obligatorio (1–50 caracteres sin contar
    los espacios de los extremos) y único sin distinguir mayúsculas (409). También se
    dan de alta al crear o editar una tarea con un subestado nuevo."""
    return _a_esquema(CrearSubestado(_repositorio(sesion)).ejecutar(datos.nombre))


@enrutador.put(
    "/{id_subestado:int}",
    response_model=SubestadoSalidaEsquema,
    responses={**RESPUESTA_NO_ENCONTRADO, **RESPUESTA_CONFLICTO, **RESPUESTA_CUERPO_MALFORMADO},
)
def renombrar(
    id_subestado: int, datos: SubestadoEsquema, sesion: Session = Depends(obtener_sesion)
) -> SubestadoSalidaEsquema:
    """Cambia el nombre del subestado (mismas reglas que en el alta); sus tareas lo
    muestran con el nombre nuevo. 404 si no existe."""
    subestado = RenombrarSubestado(_repositorio(sesion)).ejecutar(id_subestado, datos.nombre)
    return _a_esquema(subestado)


@enrutador.delete(
    "/{id_subestado:int}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    responses={**RESPUESTA_NO_ENCONTRADO},
)
def eliminar(id_subestado: int, sesion: Session = Depends(obtener_sesion)) -> Response:
    """Elimina el subestado del catálogo; sus tareas quedan sin subestado. 404 si no
    existe."""
    EliminarSubestado(_repositorio(sesion)).ejecutar(id_subestado)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
