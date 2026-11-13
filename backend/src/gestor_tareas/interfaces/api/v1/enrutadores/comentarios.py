from dataclasses import asdict

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from gestor_tareas.aplicacion.comentario.anadir_comentario import AnadirComentario
from gestor_tareas.aplicacion.comentario.editar_comentario import EditarComentario
from gestor_tareas.aplicacion.comentario.eliminar_comentario import EliminarComentario
from gestor_tareas.aplicacion.comentario.listar_comentarios import ListarComentarios
from gestor_tareas.aplicacion.comentario_paso.casos_uso import (
    AnadirComentarioPaso,
    EditarComentarioPaso,
    EliminarComentarioPaso,
    ListarComentariosPaso,
)
from gestor_tareas.aplicacion.comentario_subtarea.anadir_comentario_subtarea import (
    AnadirComentarioSubtarea,
)
from gestor_tareas.aplicacion.comentario_subtarea.editar_comentario_subtarea import (
    EditarComentarioSubtarea,
)
from gestor_tareas.aplicacion.comentario_subtarea.eliminar_comentario_subtarea import (
    EliminarComentarioSubtarea,
)
from gestor_tareas.aplicacion.comentario_subtarea.listar_comentarios_subtarea import (
    ListarComentariosSubtarea,
)
from gestor_tareas.dominio.comentario.entidades import (
    Comentario,
    ComentarioPaso,
    ComentarioSubtarea,
)
from gestor_tareas.infraestructura.persistencia.repositorios.repositorio_comentarios_paso_sqlalchemy import (  # noqa: E501
    RepositorioComentariosPasoSqlAlchemy,
)
from gestor_tareas.infraestructura.persistencia.repositorios.repositorio_comentarios_sqlalchemy import (  # noqa: E501
    RepositorioComentariosSqlAlchemy,
)
from gestor_tareas.infraestructura.persistencia.repositorios.repositorio_comentarios_subtarea_sqlalchemy import (  # noqa: E501
    RepositorioComentariosSubtareaSqlAlchemy,
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


def _a_esquema(
    comentario: Comentario | ComentarioSubtarea | ComentarioPaso,
) -> ComentarioSalidaEsquema:
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
    HTML que se guarda saneado (lo no permitido se elimina; un texto sin etiquetas
    se convierte en un párrafo por línea), con 1–500 caracteres visibles tras
    recortar los extremos y como mucho 10000 caracteres de HTML saneado. El
    servidor pone `creado`, en UTC; `editado` es `null`.
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
    alta (HTML saneado, 1–500 caracteres visibles y como mucho 10000 de HTML).
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


# --- Comentarios de las subtareas ---------------------------------------------------
# Mismos cuerpos, respuestas y códigos que los de la tarea. Una subtarea de otra
# tarea se trata como si no existiera, y un comentario de otra subtarea también.

_RUTA_SUBTAREA = "/{id_tarea:int}/subtareas/{id_subtarea:int}/comentarios"


@enrutador.get(
    _RUTA_SUBTAREA,
    response_model=list[ComentarioSalidaEsquema],
    responses={**RESPUESTA_NO_ENCONTRADO},
)
def listar_de_subtarea(
    id_tarea: int, id_subtarea: int, sesion: Session = Depends(obtener_sesion)
) -> list[ComentarioSalidaEsquema]:
    """Devuelve el histórico de comentarios de la subtarea en orden cronológico (a
    igual instante, por orden de alta); 404 si la tarea no existe o no tiene una
    subtarea con ese id (también si la subtarea es de otra tarea)."""
    comentarios = ListarComentariosSubtarea(
        RepositorioComentariosSubtareaSqlAlchemy(sesion)
    ).ejecutar(id_tarea, id_subtarea)
    return [_a_esquema(c) for c in comentarios]


@enrutador.post(
    _RUTA_SUBTAREA,
    response_model=ComentarioSalidaEsquema,
    status_code=status.HTTP_201_CREATED,
    responses={**RESPUESTA_NO_ENCONTRADO, **RESPUESTA_CUERPO_MALFORMADO},
)
def anadir_a_subtarea(
    id_tarea: int,
    id_subtarea: int,
    datos: ComentarioCrearEsquema,
    sesion: Session = Depends(obtener_sesion),
) -> ComentarioSalidaEsquema:
    """Añade un comentario al histórico de la subtarea y lo devuelve, con las reglas
    de los comentarios de la tarea (HTML saneado, 1–500 caracteres visibles y como
    mucho 10000 de HTML; el servidor pone `creado`, en UTC, y `editado` es
    `null`). La respuesta de la tarea solo incluye el número de comentarios de cada
    subtarea. 404 si la tarea no existe o no tiene una subtarea con ese id."""
    comentario = AnadirComentarioSubtarea(
        RepositorioComentariosSubtareaSqlAlchemy(sesion)
    ).ejecutar(id_tarea, id_subtarea, datos.texto)
    return _a_esquema(comentario)


@enrutador.put(
    _RUTA_SUBTAREA + "/{id_comentario:int}",
    response_model=ComentarioSalidaEsquema,
    responses={**RESPUESTA_NO_ENCONTRADO, **RESPUESTA_CUERPO_MALFORMADO},
)
def editar_de_subtarea(
    id_tarea: int,
    id_subtarea: int,
    id_comentario: int,
    datos: ComentarioEditarEsquema,
    sesion: Session = Depends(obtener_sesion),
) -> ComentarioSalidaEsquema:
    """Sustituye el texto del comentario de la subtarea y lo devuelve, con las reglas
    del alta. `creado` no cambia; el servidor pone `editado`, en UTC. 404 si la
    tarea no existe, no tiene una subtarea con ese id o la subtarea no tiene un
    comentario con ese id (también si es de otra subtarea)."""
    comentario = EditarComentarioSubtarea(
        RepositorioComentariosSubtareaSqlAlchemy(sesion)
    ).ejecutar(id_tarea, id_subtarea, id_comentario, datos.texto)
    return _a_esquema(comentario)


@enrutador.delete(
    _RUTA_SUBTAREA + "/{id_comentario:int}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    responses={**RESPUESTA_NO_ENCONTRADO},
)
def eliminar_de_subtarea(
    id_tarea: int,
    id_subtarea: int,
    id_comentario: int,
    sesion: Session = Depends(obtener_sesion),
) -> Response:
    """Borra el comentario del histórico de la subtarea. 404 si la tarea no existe,
    no tiene una subtarea con ese id o la subtarea no tiene un comentario con ese id
    (también si es de otra subtarea)."""
    EliminarComentarioSubtarea(RepositorioComentariosSubtareaSqlAlchemy(sesion)).ejecutar(
        id_tarea, id_subtarea, id_comentario
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# --- Comentarios de los pasos de los workflows ---------------------------------------
# Mismos cuerpos, respuestas y códigos que los de las subtareas. Un paso de otro
# workflow se trata como si no existiera, y un comentario de otro paso también.

enrutador_pasos = APIRouter(prefix="/workflows", tags=["Comentarios"])

_RUTA_PASO = "/{id_workflow:int}/pasos/{id_paso:int}/comentarios"


@enrutador_pasos.get(
    _RUTA_PASO,
    response_model=list[ComentarioSalidaEsquema],
    responses={**RESPUESTA_NO_ENCONTRADO},
)
def listar_de_paso(
    id_workflow: int, id_paso: int, sesion: Session = Depends(obtener_sesion)
) -> list[ComentarioSalidaEsquema]:
    """Devuelve el histórico de comentarios del paso en orden cronológico (a igual
    instante, por orden de alta); 404 si el workflow no existe o no tiene un paso con
    ese id (también si el paso es de otro workflow)."""
    comentarios = ListarComentariosPaso(RepositorioComentariosPasoSqlAlchemy(sesion)).ejecutar(
        id_workflow, id_paso
    )
    return [_a_esquema(c) for c in comentarios]


@enrutador_pasos.post(
    _RUTA_PASO,
    response_model=ComentarioSalidaEsquema,
    status_code=status.HTTP_201_CREATED,
    responses={**RESPUESTA_NO_ENCONTRADO, **RESPUESTA_CUERPO_MALFORMADO},
)
def anadir_a_paso(
    id_workflow: int,
    id_paso: int,
    datos: ComentarioCrearEsquema,
    sesion: Session = Depends(obtener_sesion),
) -> ComentarioSalidaEsquema:
    """Añade un comentario al histórico del paso y lo devuelve, con las reglas de los
    comentarios de las tareas (HTML saneado, 1–500 caracteres visibles y como mucho
    10000 de HTML; el servidor pone `creado`, en UTC, y `editado` es `null`). El
    workflow solo incluye el número de comentarios de cada paso. Al asignar el
    workflow a una tarea, cada subtarea que nace de un paso recibe una copia de sus
    comentarios. 404 si el workflow no existe o no tiene un paso con ese id."""
    comentario = AnadirComentarioPaso(RepositorioComentariosPasoSqlAlchemy(sesion)).ejecutar(
        id_workflow, id_paso, datos.texto
    )
    return _a_esquema(comentario)


@enrutador_pasos.put(
    _RUTA_PASO + "/{id_comentario:int}",
    response_model=ComentarioSalidaEsquema,
    responses={**RESPUESTA_NO_ENCONTRADO, **RESPUESTA_CUERPO_MALFORMADO},
)
def editar_de_paso(
    id_workflow: int,
    id_paso: int,
    id_comentario: int,
    datos: ComentarioEditarEsquema,
    sesion: Session = Depends(obtener_sesion),
) -> ComentarioSalidaEsquema:
    """Sustituye el texto del comentario del paso y lo devuelve, con las reglas del
    alta. `creado` no cambia; el servidor pone `editado`, en UTC. Las copias ya hechas
    en las subtareas no cambian. 404 si el workflow no existe, no tiene un paso con ese
    id o el paso no tiene un comentario con ese id (también si es de otro paso)."""
    comentario = EditarComentarioPaso(RepositorioComentariosPasoSqlAlchemy(sesion)).ejecutar(
        id_workflow, id_paso, id_comentario, datos.texto
    )
    return _a_esquema(comentario)


@enrutador_pasos.delete(
    _RUTA_PASO + "/{id_comentario:int}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    responses={**RESPUESTA_NO_ENCONTRADO},
)
def eliminar_de_paso(
    id_workflow: int,
    id_paso: int,
    id_comentario: int,
    sesion: Session = Depends(obtener_sesion),
) -> Response:
    """Borra el comentario del histórico del paso; las copias ya hechas en las
    subtareas no cambian. 404 si el workflow no existe, no tiene un paso con ese id o
    el paso no tiene un comentario con ese id (también si es de otro paso)."""
    EliminarComentarioPaso(RepositorioComentariosPasoSqlAlchemy(sesion)).ejecutar(
        id_workflow, id_paso, id_comentario
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
