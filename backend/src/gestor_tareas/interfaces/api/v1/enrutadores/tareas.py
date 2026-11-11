from dataclasses import asdict

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from gestor_tareas.aplicacion.tarea.actualizar_tarea import ActualizarTarea
from gestor_tareas.aplicacion.tarea.anadir_subtarea import AnadirSubtarea
from gestor_tareas.aplicacion.tarea.crear_tarea import CrearTarea
from gestor_tareas.aplicacion.tarea.editar_subtarea import EditarSubtarea
from gestor_tareas.aplicacion.tarea.eliminar_subtarea import EliminarSubtarea
from gestor_tareas.aplicacion.tarea.eliminar_tarea import EliminarTarea
from gestor_tareas.aplicacion.tarea.listar_tareas import ListarTareas
from gestor_tareas.aplicacion.tarea.marcar_completada import MarcarCompletada
from gestor_tareas.aplicacion.tarea.marcar_subtarea_resuelta import MarcarSubtareaResuelta
from gestor_tareas.dominio.tarea.entidades import Oportunidad, Tarea
from gestor_tareas.infraestructura.persistencia.repositorios.repositorio_tareas_sqlalchemy import (
    RepositorioTareasSqlAlchemy,
)
from gestor_tareas.infraestructura.persistencia.repositorios.repositorio_workflow_oportunidades_sqlalchemy import (  # noqa: E501
    RepositorioWorkflowOportunidadesSqlAlchemy,
)
from gestor_tareas.infraestructura.persistencia.repositorios.repositorios_catalogos_sqlalchemy import (  # noqa: E501
    RepositorioEtiquetasSqlAlchemy,
    RepositorioPersonasSqlAlchemy,
)
from gestor_tareas.interfaces.api.dependencias import obtener_sesion
from gestor_tareas.interfaces.api.respuestas_error import (
    RESPUESTA_CUERPO_MALFORMADO,
    RESPUESTA_NO_ENCONTRADO,
)
from gestor_tareas.interfaces.api.v1.esquemas.tarea import (
    SubtareaCrearEsquema,
    SubtareaEditarEsquema,
    SubtareaResueltaEsquema,
    TareaActualizarEsquema,
    TareaCompletadaEsquema,
    TareaCrearEsquema,
    TareaSalidaEsquema,
)

enrutador = APIRouter(prefix="/tareas", tags=["Tareas"])


def _a_esquema(tarea: Tarea) -> TareaSalidaEsquema:
    return TareaSalidaEsquema(**asdict(tarea))


def _argumentos(datos: TareaCrearEsquema) -> dict:
    """Datos del cuerpo para el caso de uso, con la oportunidad como entidad."""
    argumentos = datos.model_dump(exclude={"oportunidad"})
    if datos.oportunidad is not None:
        argumentos["oportunidad"] = Oportunidad(**datos.oportunidad.model_dump())
    return argumentos


@enrutador.get("", response_model=list[TareaSalidaEsquema])
def listar(sesion: Session = Depends(obtener_sesion)) -> list[TareaSalidaEsquema]:
    """Devuelve todas las tareas ordenadas por id ascendente."""
    tareas = ListarTareas(RepositorioTareasSqlAlchemy(sesion)).ejecutar()
    return [_a_esquema(t) for t in tareas]


@enrutador.post(
    "",
    response_model=TareaSalidaEsquema,
    status_code=status.HTTP_201_CREATED,
    responses={**RESPUESTA_CUERPO_MALFORMADO},
)
def crear(
    datos: TareaCrearEsquema, sesion: Session = Depends(obtener_sesion)
) -> TareaSalidaEsquema:
    """Crea una tarea pendiente con nombre, prioridad opcional (1–5), descripción, fecha de
    creación, fecha de vencimiento opcional (no anterior a la de creación; si lo es, 422),
    etiquetas, personas asignadas y tipo opcional. Con tipo "oportunidad", los
    datos de `oportunidad` son obligatorios; sin tipo, deben ser null (422).

    Las etiquetas y personas se buscan en su catálogo sin distinguir mayúsculas
    (se conserva la grafía guardada) y se dan de alta si no existen.

    Una oportunidad recibe en `subtareas` una subtarea por cada paso vigente del
    workflow de las oportunidades, en su orden, pendiente y sin persona ni
    prioridad; son subtareas como cualquier otra, y cambiar el workflow después no
    las altera.
    """
    tarea = CrearTarea(
        RepositorioTareasSqlAlchemy(sesion),
        RepositorioEtiquetasSqlAlchemy(sesion),
        RepositorioPersonasSqlAlchemy(sesion),
        RepositorioWorkflowOportunidadesSqlAlchemy(sesion),
    ).ejecutar(**_argumentos(datos))
    return _a_esquema(tarea)


@enrutador.put(
    "/{id_tarea:int}",
    response_model=TareaSalidaEsquema,
    responses={**RESPUESTA_NO_ENCONTRADO, **RESPUESTA_CUERPO_MALFORMADO},
)
def actualizar(
    id_tarea: int, datos: TareaActualizarEsquema, sesion: Session = Depends(obtener_sesion)
) -> TareaSalidaEsquema:
    """Sustituye todos los datos de una tarea existente, incluidos sus conjuntos de
    etiquetas y personas asignadas, y su tipo con sus datos (sin tipo, se borran
    los datos de oportunidad); 404 si el id no existe y 422 si la fecha de
    vencimiento es anterior a la de creación o el tipo no casa con sus datos.
    El estado completada no cambia (solo lo cambia `PATCH .../completada`), ni las
    subtareas, tampoco al cambiar el tipo: una tarea que pasa a ser oportunidad no
    recibe las del workflow (solo se crean al dar de alta la oportunidad)."""
    tarea = ActualizarTarea(
        RepositorioTareasSqlAlchemy(sesion),
        RepositorioEtiquetasSqlAlchemy(sesion),
        RepositorioPersonasSqlAlchemy(sesion),
    ).ejecutar(id_tarea, **_argumentos(datos))
    return _a_esquema(tarea)


@enrutador.patch(
    "/{id_tarea:int}/completada",
    response_model=TareaSalidaEsquema,
    responses={**RESPUESTA_NO_ENCONTRADO, **RESPUESTA_CUERPO_MALFORMADO},
)
def marcar_completada(
    id_tarea: int, datos: TareaCompletadaEsquema, sesion: Session = Depends(obtener_sesion)
) -> TareaSalidaEsquema:
    """Marca la tarea como completada (`true`) o la deja pendiente (`false`) y la
    devuelve con el resto de sus datos sin cambios; 404 si el id no existe y 422
    si `completada` no es un booleano de JSON."""
    tarea = MarcarCompletada(RepositorioTareasSqlAlchemy(sesion)).ejecutar(
        id_tarea, datos.completada
    )
    return _a_esquema(tarea)


@enrutador.delete(
    "/{id_tarea:int}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    responses={**RESPUESTA_NO_ENCONTRADO},
)
def eliminar(id_tarea: int, sesion: Session = Depends(obtener_sesion)) -> Response:
    """Borra la tarea con sus datos de tipo, sus subtareas, sus comentarios y los de
    sus subtareas. Las etiquetas y personas del catálogo se conservan. 404 si la
    tarea no existe."""
    EliminarTarea(RepositorioTareasSqlAlchemy(sesion)).ejecutar(id_tarea)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@enrutador.post(
    "/{id_tarea:int}/subtareas",
    response_model=TareaSalidaEsquema,
    status_code=status.HTTP_201_CREATED,
    responses={**RESPUESTA_NO_ENCONTRADO, **RESPUESTA_CUERPO_MALFORMADO},
)
def anadir_subtarea(
    id_tarea: int, datos: SubtareaCrearEsquema, sesion: Session = Depends(obtener_sesion)
) -> TareaSalidaEsquema:
    """Añade una subtarea pendiente al final de las de la tarea y devuelve la tarea
    completa. El nombre es obligatorio (1–200 caracteres tras recortar); la persona
    asignada (1–100) y la prioridad (1–5) son opcionales. La persona se busca en su
    catálogo sin distinguir mayúsculas (se conserva la grafía guardada) y se da de
    alta si no existe. 404 si la tarea no existe."""
    tarea = AnadirSubtarea(
        RepositorioTareasSqlAlchemy(sesion), RepositorioPersonasSqlAlchemy(sesion)
    ).ejecutar(id_tarea, **datos.model_dump())
    return _a_esquema(tarea)


@enrutador.patch(
    "/{id_tarea:int}/subtareas/{id_subtarea:int}/resuelta",
    response_model=TareaSalidaEsquema,
    responses={**RESPUESTA_NO_ENCONTRADO, **RESPUESTA_CUERPO_MALFORMADO},
)
def marcar_subtarea_resuelta(
    id_tarea: int,
    id_subtarea: int,
    datos: SubtareaResueltaEsquema,
    sesion: Session = Depends(obtener_sesion),
) -> TareaSalidaEsquema:
    """Marca la subtarea como resuelta (`true`) o la reabre (`false`) y devuelve la
    tarea con el resto de sus datos sin cambios; 404 si la tarea no existe o no
    tiene una subtarea con ese id (también si la subtarea es de otra tarea) y 422
    si `resuelta` no es un booleano de JSON."""
    tarea = MarcarSubtareaResuelta(RepositorioTareasSqlAlchemy(sesion)).ejecutar(
        id_tarea, id_subtarea, datos.resuelta
    )
    return _a_esquema(tarea)


@enrutador.put(
    "/{id_tarea:int}/subtareas/{id_subtarea:int}",
    response_model=TareaSalidaEsquema,
    responses={**RESPUESTA_NO_ENCONTRADO, **RESPUESTA_CUERPO_MALFORMADO},
)
def editar_subtarea(
    id_tarea: int,
    id_subtarea: int,
    datos: SubtareaEditarEsquema,
    sesion: Session = Depends(obtener_sesion),
) -> TareaSalidaEsquema:
    """Sustituye el nombre, la persona asignada y la prioridad de la subtarea y
    devuelve la tarea completa. Las validaciones son las del alta. Es un reemplazo
    completo: si `asignado` o `prioridad` faltan o son `null`, se vacían; el estado
    resuelta no cambia. La persona se busca en su catálogo sin distinguir mayúsculas
    y se da de alta si no existe. 404 si la tarea no existe o no tiene una subtarea
    con ese id (también si la subtarea es de otra tarea); entonces no se da de alta
    a nadie."""
    tarea = EditarSubtarea(
        RepositorioTareasSqlAlchemy(sesion), RepositorioPersonasSqlAlchemy(sesion)
    ).ejecutar(id_tarea, id_subtarea, **datos.model_dump())
    return _a_esquema(tarea)


@enrutador.delete(
    "/{id_tarea:int}/subtareas/{id_subtarea:int}",
    response_model=TareaSalidaEsquema,
    responses={**RESPUESTA_NO_ENCONTRADO},
)
def eliminar_subtarea(
    id_tarea: int, id_subtarea: int, sesion: Session = Depends(obtener_sesion)
) -> TareaSalidaEsquema:
    """Borra la subtarea con sus comentarios y devuelve la tarea con el resto de sus
    datos sin cambios; 404 si la tarea no existe o no tiene una subtarea con ese id
    (también si la subtarea es de otra tarea)."""
    tarea = EliminarSubtarea(RepositorioTareasSqlAlchemy(sesion)).ejecutar(id_tarea, id_subtarea)
    return _a_esquema(tarea)
