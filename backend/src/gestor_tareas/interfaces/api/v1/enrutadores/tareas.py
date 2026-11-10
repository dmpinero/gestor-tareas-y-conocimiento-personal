from dataclasses import asdict

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from gestor_tareas.aplicacion.tarea.actualizar_tarea import ActualizarTarea
from gestor_tareas.aplicacion.tarea.crear_tarea import CrearTarea
from gestor_tareas.aplicacion.tarea.listar_tareas import ListarTareas
from gestor_tareas.aplicacion.tarea.marcar_completada import MarcarCompletada
from gestor_tareas.aplicacion.tarea.marcar_paso_hecho import MarcarPasoHecho
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
    PasoHechoEsquema,
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

    Una oportunidad recibe en `pasos_oportunidad` una copia de los pasos vigentes del
    workflow de las oportunidades, en su orden y pendientes; cambiar el workflow
    después no la altera.
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
    los datos de oportunidad y sus pasos); 404 si el id no existe y 422 si la fecha
    de vencimiento es anterior a la de creación o el tipo no casa con sus datos.
    El estado completada no cambia (solo lo cambia `PATCH .../completada`), ni los
    pasos de una oportunidad que sigue siéndolo. Una tarea que pasa a ser
    oportunidad no recibe pasos: solo se copian al crear la oportunidad."""
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


@enrutador.patch(
    "/{id_tarea:int}/pasos/{id_paso:int}",
    response_model=TareaSalidaEsquema,
    responses={**RESPUESTA_NO_ENCONTRADO, **RESPUESTA_CUERPO_MALFORMADO},
)
def marcar_paso_hecho(
    id_tarea: int, id_paso: int, datos: PasoHechoEsquema, sesion: Session = Depends(obtener_sesion)
) -> TareaSalidaEsquema:
    """Marca el paso de la oportunidad como hecho (`true`) o lo deja pendiente
    (`false`) y devuelve la tarea con el resto de sus datos sin cambios; 404 si la
    tarea no existe o no tiene un paso con ese id (también si el paso es de otra
    tarea) y 422 si `hecho` no es un booleano de JSON."""
    tarea = MarcarPasoHecho(RepositorioTareasSqlAlchemy(sesion)).ejecutar(
        id_tarea, id_paso, datos.hecho
    )
    return _a_esquema(tarea)
