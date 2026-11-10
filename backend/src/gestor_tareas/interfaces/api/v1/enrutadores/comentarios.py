from dataclasses import asdict

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from gestor_tareas.aplicacion.comentario.anadir_comentario import AnadirComentario
from gestor_tareas.aplicacion.comentario.listar_comentarios import ListarComentarios
from gestor_tareas.dominio.comentario.entidades import Comentario
from gestor_tareas.infraestructura.persistencia.repositorios.repositorio_comentarios_sqlalchemy import (  # noqa: E501
    RepositorioComentariosSqlAlchemy,
)
from gestor_tareas.interfaces.api.dependencias import obtener_sesion
from gestor_tareas.interfaces.api.respuestas_error import (
    RESPUESTA_CUERPO_MALFORMADO,
    RESPUESTA_NO_ENCONTRADO,
)
from gestor_tareas.interfaces.api.v1.esquemas.comentario import (
    ComentarioCrearEsquema,
    ComentarioSalidaEsquema,
)

enrutador = APIRouter(prefix="/tareas", tags=["Comentarios"])


def _a_esquema(comentario: Comentario) -> ComentarioSalidaEsquema:
    return ComentarioSalidaEsquema(**asdict(comentario))


@enrutador.get(
    "/{id_tarea:int}/comentarios",
    response_model=list[ComentarioSalidaEsquema],
    responses={**RESPUESTA_NO_ENCONTRADO},
)
def listar(
    id_tarea: int, sesion: Session = Depends(obtener_sesion)
) -> list[ComentarioSalidaEsquema]:
    """Devuelve el histórico de comentarios de la tarea en orden cronológico (a
    igual instante, por orden de alta); 404 si la tarea no existe."""
    comentarios = ListarComentarios(RepositorioComentariosSqlAlchemy(sesion)).ejecutar(id_tarea)
    return [_a_esquema(c) for c in comentarios]


@enrutador.post(
    "/{id_tarea:int}/comentarios",
    response_model=ComentarioSalidaEsquema,
    status_code=status.HTTP_201_CREATED,
    responses={**RESPUESTA_NO_ENCONTRADO, **RESPUESTA_CUERPO_MALFORMADO},
)
def anadir(
    id_tarea: int, datos: ComentarioCrearEsquema, sesion: Session = Depends(obtener_sesion)
) -> ComentarioSalidaEsquema:
    """Añade un comentario al histórico de la tarea y lo devuelve. El texto es
    obligatorio (1–500 caracteres tras recortar los extremos; conserva los saltos de
    línea de su interior). El servidor pone `creado`, en UTC. Los comentarios no se
    editan ni se borran, y no se incluyen en la respuesta de la tarea. 404 si la
    tarea no existe."""
    comentario = AnadirComentario(RepositorioComentariosSqlAlchemy(sesion)).ejecutar(
        id_tarea, datos.texto
    )
    return _a_esquema(comentario)
