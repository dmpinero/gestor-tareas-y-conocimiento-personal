from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from gestor_tareas.aplicacion.foco.casos_uso import (
    FijarFoco,
    ListarHistorialFoco,
    ObtenerFoco,
    QuitarFoco,
)
from gestor_tareas.dominio.foco.entidades import Foco, PeriodoDeFoco
from gestor_tareas.infraestructura.persistencia.repositorios.repositorio_foco_sqlalchemy import (
    RepositorioFocoSqlAlchemy,
)
from gestor_tareas.infraestructura.persistencia.repositorios.repositorio_tareas_sqlalchemy import (
    RepositorioTareasSqlAlchemy,
)
from gestor_tareas.interfaces.api.dependencias import obtener_sesion
from gestor_tareas.interfaces.api.respuestas_error import (
    RESPUESTA_CUERPO_MALFORMADO,
    RESPUESTA_FILTRO_INVALIDO,
    RESPUESTA_NO_ENCONTRADO,
)
from gestor_tareas.interfaces.api.v1.esquemas.foco import (
    FocoFijarEsquema,
    FocoSalidaEsquema,
    InstanteIsoConZona,
    PeriodoDeFocoSalidaEsquema,
)

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
    """Deja sin foco y cierra ahora su periodo del historial. Responde 204 también si
    no había foco."""
    QuitarFoco(RepositorioFocoSqlAlchemy(sesion)).ejecutar()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def _periodo_a_esquema(periodo: PeriodoDeFoco) -> PeriodoDeFocoSalidaEsquema:
    return PeriodoDeFocoSalidaEsquema(
        id=periodo.id,
        tarea_id=periodo.tarea_id,
        tarea_nombre=periodo.tarea_nombre,
        subtarea_id=periodo.subtarea_id,
        subtarea_nombre=periodo.subtarea_nombre,
        desde=periodo.desde,
        hasta=periodo.hasta,
    )


@enrutador.get(
    "/historial",
    response_model=list[PeriodoDeFocoSalidaEsquema],
    responses={**RESPUESTA_FILTRO_INVALIDO},
)
def historial(
    desde: InstanteIsoConZona | None = Query(
        default=None,
        description="Opcional. Instante ISO 8601 con zona (p. ej. `2026-11-24T00:00:00Z` o "
        "`2026-11-24T00:00:00+01:00`): solo los periodos que empiezan en él o después.",
    ),
    hasta: InstanteIsoConZona | None = Query(
        default=None,
        description="Opcional. Instante ISO 8601 con zona: solo los periodos que empiezan "
        "antes de él. Con los dos, `desde` debe ser anterior a `hasta`.",
    ),
    sesion: Session = Depends(obtener_sesion),
) -> list[PeriodoDeFocoSalidaEsquema]:
    """Historial del foco: un periodo por cada vez que se fijó, del más reciente al
    más antiguo, con los que empiezan en `[desde, hasta)`. El periodo en curso (el del
    foco actual) tiene `hasta` null. Fijar otro foco, quitarlo o borrar la tarea o la
    subtarea en foco lo cierra. Los nombres son los actuales; si la tarea o la
    subtarea se borraron, su id es null y queda el nombre que tenían. 422 si un
    límite no es un instante con zona o si `desde` no es anterior a `hasta`."""
    periodos = ListarHistorialFoco(RepositorioFocoSqlAlchemy(sesion)).ejecutar(desde, hasta)
    return [_periodo_a_esquema(p) for p in periodos]
