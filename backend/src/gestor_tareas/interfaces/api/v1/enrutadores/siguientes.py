from fastapi import APIRouter, Depends, Query
from fastapi.exceptions import RequestValidationError
from sqlalchemy.orm import Session

from gestor_tareas.aplicacion.siguientes.casos_uso import (
    AnadirASiguientes,
    AnadirASugerencias,
    ListarSiguientes,
    ListarSugerencias,
    QuitarDeSiguientes,
    QuitarDeSugerencias,
    ReordenarSiguientes,
)
from gestor_tareas.dominio.siguientes.entidades import ClaveDeEntrada, TareaSiguiente
from gestor_tareas.dominio.siguientes.reglas import (
    OrdenDeLaColaInvalidoError,
    SubtareaResueltaEnLaColaError,
    TareaCompletadaEnLaColaError,
)
from gestor_tareas.infraestructura.persistencia.repositorios.repositorio_siguientes_sqlalchemy import (  # noqa: E501
    RepositorioSiguientesSqlAlchemy,
)
from gestor_tareas.interfaces.api.dependencias import obtener_sesion
from gestor_tareas.interfaces.api.respuestas_error import (
    RESPUESTA_CUERPO_MALFORMADO,
    RESPUESTA_NO_ENCONTRADO,
)
from gestor_tareas.interfaces.api.v1.esquemas.siguientes import (
    OrdenSiguientesEsquema,
    SiguienteAnadirEsquema,
    TareaSiguienteEsquema,
)

enrutador = APIRouter(prefix="/siguientes", tags=["Siguientes tareas"])
enrutador_sugerencias = APIRouter(prefix="/sugerencias", tags=["Siguientes tareas"])

_RESPUESTA_ID_DE_RUTA_NO_ENTERO = {404: {"description": "El id de la ruta no es un número entero"}}


def _a_esquema(cola: list[TareaSiguiente]) -> list[TareaSiguienteEsquema]:
    return [
        TareaSiguienteEsquema(
            tarea_id=t.tarea_id,
            tarea_nombre=t.tarea_nombre,
            subtarea_id=t.subtarea_id,
            subtarea_nombre=t.subtarea_nombre,
        )
        for t in cola
    ]


def _error_de_validacion(campo: str, valor: object, error: Exception) -> RequestValidationError:
    # Mismo formato que el resto de errores de validación del cuerpo, que es el que
    # publica el contrato para el 422.
    return RequestValidationError(
        [{"type": "value_error", "loc": ("body", campo), "msg": str(error), "input": valor}]
    )


def _anadir(caso_de_uso, datos: SiguienteAnadirEsquema) -> list[TareaSiguienteEsquema]:
    """Añade la entrada con el caso de uso; la tarea completada o la subtarea resuelta
    dan 422 en su campo del cuerpo."""
    try:
        lista = caso_de_uso.ejecutar(datos.tarea_id, datos.subtarea_id)
    except TareaCompletadaEnLaColaError as error:
        raise _error_de_validacion("tarea_id", datos.tarea_id, error) from error
    except SubtareaResueltaEnLaColaError as error:
        raise _error_de_validacion("subtarea_id", datos.subtarea_id, error) from error
    return _a_esquema(lista)


def _subtarea_de_la_entrada():
    return Query(
        default=None,
        description=(
            "Id de la subtarea de la entrada que se quita; sin él, la de la tarea entera "
            "(las entradas de sus subtareas se quedan)."
        ),
    )


@enrutador.get("", response_model=list[TareaSiguienteEsquema])
def listar(sesion: Session = Depends(obtener_sesion)) -> list[TareaSiguienteEsquema]:
    """Cola de siguientes: las entradas (tareas enteras o subtareas) elegidas para
    trabajar en ellas después del foco, en su orden y con sus nombres actuales. No
    incluye las sugerencias elegidas (ver `GET /sugerencias`). Las de tareas
    completadas o subtareas resueltas no aparecen; si se reabren, vuelven a su sitio.
    Borrar la tarea o la subtarea quita sus entradas. Poner en foco una tarea entera
    quita su entrada; poner en foco una subtarea quita la suya y la de su tarea."""
    return _a_esquema(ListarSiguientes(RepositorioSiguientesSqlAlchemy(sesion)).ejecutar())


@enrutador.post(
    "",
    response_model=list[TareaSiguienteEsquema],
    responses={**RESPUESTA_NO_ENCONTRADO, **RESPUESTA_CUERPO_MALFORMADO},
)
def anadir(
    datos: SiguienteAnadirEsquema, sesion: Session = Depends(obtener_sesion)
) -> list[TareaSiguienteEsquema]:
    """Añade la entrada (la tarea entera o, con `subtarea_id`, esa subtarea suya) al
    final de la cola de siguientes y devuelve la cola completa. Si estaba en las
    sugerencias elegidas, sale de ellas; si ya estaba en la cola, no cambia nada. Una
    tarea y sus subtareas son entradas distintas. 404 si la tarea no existe o la
    subtarea no es suya; 422 si la tarea está completada o la subtarea resuelta."""
    return _anadir(AnadirASiguientes(RepositorioSiguientesSqlAlchemy(sesion)), datos)


@enrutador.put(
    "",
    response_model=list[TareaSiguienteEsquema],
    responses={**RESPUESTA_CUERPO_MALFORMADO},
)
def reordenar(
    datos: OrdenSiguientesEsquema, sesion: Session = Depends(obtener_sesion)
) -> list[TareaSiguienteEsquema]:
    """Reordena la cola de siguientes: la primera de `entradas` pasa a ser la siguiente,
    y así con el resto. Devuelve la cola en el nuevo orden. `entradas` debe ser
    exactamente la cola que devuelve `GET /siguientes` (cada entrada una vez); si falta
    alguna, se repite o no está en la cola (también si está en sugerencias), 422 y no
    cambia nada. Las que no se ven (tareas completadas o subtareas resueltas) quedan
    detrás."""
    claves = [ClaveDeEntrada(e.tarea_id, e.subtarea_id) for e in datos.entradas]
    try:
        cola = ReordenarSiguientes(RepositorioSiguientesSqlAlchemy(sesion)).ejecutar(claves)
    except OrdenDeLaColaInvalidoError as error:
        valor = [e.model_dump() for e in datos.entradas]
        raise _error_de_validacion("entradas", valor, error) from error
    return _a_esquema(cola)


@enrutador.delete(
    "/{id_tarea:int}",
    response_model=list[TareaSiguienteEsquema],
    responses=_RESPUESTA_ID_DE_RUTA_NO_ENTERO,
)
def quitar(
    id_tarea: int,
    subtarea_id: int | None = _subtarea_de_la_entrada(),
    sesion: Session = Depends(obtener_sesion),
) -> list[TareaSiguienteEsquema]:
    """Saca la entrada (la tarea entera o, con `subtarea_id`, esa subtarea suya) de la
    cola de siguientes y devuelve la cola. Si no estaba (o no existe), responde
    igualmente 200 con la cola sin cambios; si está en las sugerencias elegidas, sigue
    en ellas. 404 si el id de la ruta no es un número entero."""
    return _a_esquema(
        QuitarDeSiguientes(RepositorioSiguientesSqlAlchemy(sesion)).ejecutar(id_tarea, subtarea_id)
    )


@enrutador_sugerencias.get("", response_model=list[TareaSiguienteEsquema])
def listar_sugerencias(sesion: Session = Depends(obtener_sesion)) -> list[TareaSiguienteEsquema]:
    """Sugerencias elegidas: las entradas (tareas enteras o subtareas) que el usuario ha
    puesto en Sugerencias, en el orden en que se añadieron y con sus nombres actuales.
    Una entrada está o en la cola de siguientes o aquí, no en las dos. Las de tareas
    completadas o subtareas resueltas no aparecen; si se reabren, vuelven a su sitio.
    Borrar la tarea o la subtarea, o ponerlas en foco, las saca de aquí como de la
    cola."""
    return _a_esquema(ListarSugerencias(RepositorioSiguientesSqlAlchemy(sesion)).ejecutar())


@enrutador_sugerencias.post(
    "",
    response_model=list[TareaSiguienteEsquema],
    responses={**RESPUESTA_NO_ENCONTRADO, **RESPUESTA_CUERPO_MALFORMADO},
)
def anadir_a_sugerencias(
    datos: SiguienteAnadirEsquema, sesion: Session = Depends(obtener_sesion)
) -> list[TareaSiguienteEsquema]:
    """Añade la entrada (la tarea entera o, con `subtarea_id`, esa subtarea suya) al
    final de las sugerencias elegidas y las devuelve. Si estaba en la cola de
    siguientes, sale de ella; si ya estaba en sugerencias, no cambia nada. 404 si la
    tarea no existe o la subtarea no es suya; 422 si la tarea está completada o la
    subtarea resuelta."""
    return _anadir(AnadirASugerencias(RepositorioSiguientesSqlAlchemy(sesion)), datos)


@enrutador_sugerencias.delete(
    "/{id_tarea:int}",
    response_model=list[TareaSiguienteEsquema],
    responses=_RESPUESTA_ID_DE_RUTA_NO_ENTERO,
)
def quitar_de_sugerencias(
    id_tarea: int,
    subtarea_id: int | None = _subtarea_de_la_entrada(),
    sesion: Session = Depends(obtener_sesion),
) -> list[TareaSiguienteEsquema]:
    """Saca la entrada (la tarea entera o, con `subtarea_id`, esa subtarea suya) de las
    sugerencias elegidas y las devuelve. Si no estaba (o no existe), responde
    igualmente 200 sin cambios; si está en la cola de siguientes, sigue en ella. 404 si
    el id de la ruta no es un número entero."""
    return _a_esquema(
        QuitarDeSugerencias(RepositorioSiguientesSqlAlchemy(sesion)).ejecutar(id_tarea, subtarea_id)
    )
