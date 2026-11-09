from dataclasses import asdict

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from gestor_tareas.aplicacion.tarea.actualizar_tarea import ActualizarTarea
from gestor_tareas.aplicacion.tarea.crear_tarea import CrearTarea
from gestor_tareas.aplicacion.tarea.listar_tareas import ListarTareas
from gestor_tareas.dominio.tarea.entidades import Tarea
from gestor_tareas.infraestructura.persistencia.repositorios.repositorio_tareas_sqlalchemy import (
    RepositorioTareasSqlAlchemy,
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
    TareaActualizarEsquema,
    TareaCrearEsquema,
    TareaSalidaEsquema,
)

enrutador = APIRouter(prefix="/tareas", tags=["Tareas"])


def _a_esquema(tarea: Tarea) -> TareaSalidaEsquema:
    return TareaSalidaEsquema(**asdict(tarea))


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
    """Crea una tarea con nombre, prioridad opcional (1–5), descripción, fecha de creación,
    fecha de vencimiento opcional (no anterior a la de creación; si lo es, 422),
    etiquetas y personas asignadas.

    Las etiquetas y personas se buscan en su catálogo sin distinguir mayúsculas
    (se conserva la grafía guardada) y se dan de alta si no existen.
    """
    tarea = CrearTarea(
        RepositorioTareasSqlAlchemy(sesion),
        RepositorioEtiquetasSqlAlchemy(sesion),
        RepositorioPersonasSqlAlchemy(sesion),
    ).ejecutar(**datos.model_dump())
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
    etiquetas y personas asignadas; 404 si el id no existe y 422 si la fecha de
    vencimiento es anterior a la de creación."""
    tarea = ActualizarTarea(
        RepositorioTareasSqlAlchemy(sesion),
        RepositorioEtiquetasSqlAlchemy(sesion),
        RepositorioPersonasSqlAlchemy(sesion),
    ).ejecutar(id_tarea, **datos.model_dump())
    return _a_esquema(tarea)
