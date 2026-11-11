from dataclasses import asdict

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from gestor_tareas.aplicacion.comentario.anadir_comentario import AnadirComentario
from gestor_tareas.aplicacion.comentario.editar_comentario import EditarComentario
from gestor_tareas.aplicacion.comentario.eliminar_comentario import EliminarComentario
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
    ComentarioEditarEsquema,
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
    línea de su interior). El servidor pone `creado`, en UTC; `editado` es `null`.
    Los comentarios no se incluyen en la respuesta de la tarea. 404 si la tarea no
    existe."""
    comentario = AnadirComentario(RepositorioComentariosSqlAlchemy(sesion)).ejecutar(
        id_tarea, datos.texto
    )
    return _a_esquema(comentario)


@enrutador.put(
    "/{id_tarea:int}/comentarios/{id_comentario:int}",
    response_model=ComentarioSalidaEsquema,
    responses={**RESPUESTA_NO_ENCONTRADO, **RESPUESTA_CUERPO_MALFORMADO},
)
def editar(
    id_tarea: int,
    id_comentario: int,
    datos: ComentarioEditarEsquema,
    sesion: Session = Depends(obtener_sesion),
) -> ComentarioSalidaEsquema:
    """Sustituye el texto del comentario y lo devuelve. El texto sigue las reglas del
    alta (1–500 caracteres tras recortar los extremos, con sus saltos de línea).
    `creado` no cambia; el servidor pone `editado`, en UTC. 404 si la tarea no
    existe o no tiene un comentario con ese id (también si es de otra tarea)."""
    comentario = EditarComentario(RepositorioComentariosSqlAlchemy(sesion)).ejecutar(
        id_tarea, id_comentario, datos.texto
    )
    return _a_esquema(comentario)


@enrutador.delete(
    "/{id_tarea:int}/comentarios/{id_comentario:int}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    responses={**RESPUESTA_NO_ENCONTRADO},
)
def eliminar(
    id_tarea: int, id_comentario: int, sesion: Session = Depends(obtener_sesion)
) -> Response:
    """Borra el comentario del histórico. 404 si la tarea no existe o no tiene un
    comentario con ese id (también si es de otra tarea)."""
    EliminarComentario(RepositorioComentariosSqlAlchemy(sesion)).ejecutar(id_tarea, id_comentario)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
