from dataclasses import asdict

from fastapi import APIRouter, Depends, Query, Response, status
from fastapi.exceptions import RequestValidationError
from sqlalchemy.orm import Session

from gestor_tareas.aplicacion.grupo_estados.casos_uso import (
    AnadirEstado,
    CrearGrupoEstados,
    EliminarEstado,
    EliminarGrupoEstados,
    ListarGruposEstados,
    RenombrarEstado,
    RenombrarGrupoEstados,
    ReordenarEstados,
)
from gestor_tareas.dominio.excepciones import OrdenDeEstadosInvalidoError
from gestor_tareas.dominio.grupo_estados.entidades import GrupoEstados
from gestor_tareas.infraestructura.persistencia.repositorios.repositorio_grupos_estados_sqlalchemy import (  # noqa: E501
    RepositorioGruposEstadosSqlAlchemy,
)
from gestor_tareas.interfaces.api.dependencias import obtener_sesion
from gestor_tareas.interfaces.api.respuestas_error import (
    RESPUESTA_CONFLICTO,
    RESPUESTA_CUERPO_MALFORMADO,
    RESPUESTA_NO_ENCONTRADO,
)
from gestor_tareas.interfaces.api.v1.esquemas.grupo_estados import (
    EstadoGrupoEsquema,
    GrupoEstadosEsquema,
    GrupoEstadosSalidaEsquema,
    OrdenEstadosEsquema,
)

enrutador = APIRouter(prefix="/grupos-estados", tags=["Grupos de estados"])


def _a_esquema(grupo: GrupoEstados) -> GrupoEstadosSalidaEsquema:
    return GrupoEstadosSalidaEsquema(**asdict(grupo))


def _repositorio(sesion: Session) -> RepositorioGruposEstadosSqlAlchemy:
    return RepositorioGruposEstadosSqlAlchemy(sesion)


@enrutador.get("", response_model=list[GrupoEstadosSalidaEsquema])
def listar(sesion: Session = Depends(obtener_sesion)) -> list[GrupoEstadosSalidaEsquema]:
    """Devuelve los grupos de estados por nombre (sin distinguir mayúsculas), cada uno
    con sus estados por posición y el número de tareas del grupo y de cada estado."""
    return [_a_esquema(g) for g in ListarGruposEstados(_repositorio(sesion)).ejecutar()]


@enrutador.post(
    "",
    response_model=GrupoEstadosSalidaEsquema,
    status_code=status.HTTP_201_CREATED,
    responses={**RESPUESTA_CONFLICTO, **RESPUESTA_CUERPO_MALFORMADO},
)
def crear(
    datos: GrupoEstadosEsquema, sesion: Session = Depends(obtener_sesion)
) -> GrupoEstadosSalidaEsquema:
    """Crea un grupo de estados sin estados. El nombre es obligatorio (1–50 caracteres
    sin contar los espacios de los extremos) y único sin distinguir mayúsculas (409)."""
    return _a_esquema(CrearGrupoEstados(_repositorio(sesion)).ejecutar(datos.nombre))


@enrutador.put(
    "/{id_grupo:int}",
    response_model=GrupoEstadosSalidaEsquema,
    responses={**RESPUESTA_NO_ENCONTRADO, **RESPUESTA_CONFLICTO, **RESPUESTA_CUERPO_MALFORMADO},
)
def renombrar(
    id_grupo: int, datos: GrupoEstadosEsquema, sesion: Session = Depends(obtener_sesion)
) -> GrupoEstadosSalidaEsquema:
    """Cambia el nombre del grupo (mismas reglas que en el alta); sus estados y sus
    tareas no cambian. 404 si el grupo no existe."""
    grupo = RenombrarGrupoEstados(_repositorio(sesion)).ejecutar(id_grupo, datos.nombre)
    return _a_esquema(grupo)


@enrutador.delete(
    "/{id_grupo:int}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    responses={**RESPUESTA_NO_ENCONTRADO},
)
def eliminar(id_grupo: int, sesion: Session = Depends(obtener_sesion)) -> Response:
    """Elimina el grupo con sus estados; sus tareas quedan sin grupo ni estado (el
    número de tareas afectadas es el `tareas` del grupo). 404 si no existe."""
    EliminarGrupoEstados(_repositorio(sesion)).ejecutar(id_grupo)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@enrutador.post(
    "/{id_grupo:int}/estados",
    response_model=GrupoEstadosSalidaEsquema,
    status_code=status.HTTP_201_CREATED,
    responses={**RESPUESTA_NO_ENCONTRADO, **RESPUESTA_CONFLICTO, **RESPUESTA_CUERPO_MALFORMADO},
)
def anadir_estado(
    id_grupo: int, datos: EstadoGrupoEsquema, sesion: Session = Depends(obtener_sesion)
) -> GrupoEstadosSalidaEsquema:
    """Añade un estado al final del grupo y devuelve el grupo. El nombre es obligatorio
    (1–50 caracteres sin contar los espacios de los extremos) y único dentro del grupo
    sin distinguir mayúsculas (409). 404 si el grupo no existe."""
    grupo = AnadirEstado(_repositorio(sesion)).ejecutar(id_grupo, datos.nombre)
    return _a_esquema(grupo)


@enrutador.put(
    "/{id_grupo:int}/estados/{id_estado:int}",
    response_model=GrupoEstadosSalidaEsquema,
    responses={**RESPUESTA_NO_ENCONTRADO, **RESPUESTA_CONFLICTO, **RESPUESTA_CUERPO_MALFORMADO},
)
def renombrar_estado(
    id_grupo: int,
    id_estado: int,
    datos: EstadoGrupoEsquema,
    sesion: Session = Depends(obtener_sesion),
) -> GrupoEstadosSalidaEsquema:
    """Cambia el nombre del estado (mismas reglas que en el alta) y devuelve el grupo;
    su posición no cambia. 404 si el grupo no existe o el estado no es suyo."""
    grupo = RenombrarEstado(_repositorio(sesion)).ejecutar(id_grupo, id_estado, datos.nombre)
    return _a_esquema(grupo)


@enrutador.delete(
    "/{id_grupo:int}/estados/{id_estado:int}",
    response_model=GrupoEstadosSalidaEsquema,
    responses={**RESPUESTA_NO_ENCONTRADO, **RESPUESTA_CONFLICTO},
)
def eliminar_estado(
    id_grupo: int,
    id_estado: int,
    mover_a: int | None = Query(
        default=None,
        description=(
            "Otro estado del mismo grupo al que pasan antes las tareas del estado. "
            "Obligatorio si el estado tiene tareas; si falta en ese caso, o no es otro "
            "estado del grupo, 409 y no cambia nada."
        ),
    ),
    sesion: Session = Depends(obtener_sesion),
) -> GrupoEstadosSalidaEsquema:
    """Elimina el estado, renumera los siguientes (1..n) y devuelve el grupo. Si el
    estado tiene tareas, pasan antes al estado `mover_a`, en la misma operación. 404
    si el grupo no existe o el estado no es suyo."""
    grupo = EliminarEstado(_repositorio(sesion)).ejecutar(id_grupo, id_estado, mover_a)
    return _a_esquema(grupo)


@enrutador.put(
    "/{id_grupo:int}/orden",
    response_model=GrupoEstadosSalidaEsquema,
    responses={**RESPUESTA_NO_ENCONTRADO, **RESPUESTA_CUERPO_MALFORMADO},
)
def reordenar_estados(
    id_grupo: int, datos: OrdenEstadosEsquema, sesion: Session = Depends(obtener_sesion)
) -> GrupoEstadosSalidaEsquema:
    """Reordena los estados del grupo: el primer id pasa a la posición 1, el segundo a
    la 2, etc. Devuelve el grupo. `ids` debe incluir cada estado del grupo exactamente
    una vez; si falta alguno, se repite o no es del grupo, 422 y no cambia nada. 404 si
    el grupo no existe."""
    try:
        grupo = ReordenarEstados(_repositorio(sesion)).ejecutar(id_grupo, datos.ids)
    except OrdenDeEstadosInvalidoError as error:
        # Mismo formato que el resto de errores de validación del cuerpo, que es el
        # que publica el contrato para el 422.
        raise RequestValidationError(
            [{"type": "value_error", "loc": ("body", "ids"), "msg": str(error), "input": datos.ids}]
        ) from error
    return _a_esquema(grupo)
