from dataclasses import asdict

from fastapi import APIRouter, Depends, Response, status
from fastapi.exceptions import RequestValidationError
from sqlalchemy.orm import Session

from gestor_tareas.aplicacion.workflow_oportunidades.anadir_paso import AnadirPaso
from gestor_tareas.aplicacion.workflow_oportunidades.eliminar_paso import EliminarPaso
from gestor_tareas.aplicacion.workflow_oportunidades.listar_pasos import ListarPasos
from gestor_tareas.aplicacion.workflow_oportunidades.renombrar_paso import RenombrarPaso
from gestor_tareas.aplicacion.workflow_oportunidades.reordenar_pasos import ReordenarPasos
from gestor_tareas.dominio.excepciones import OrdenDePasosInvalidoError
from gestor_tareas.dominio.workflow_oportunidades.entidades import PasoWorkflowOportunidad
from gestor_tareas.infraestructura.persistencia.repositorios.repositorio_workflow_oportunidades_sqlalchemy import (  # noqa: E501
    RepositorioWorkflowOportunidadesSqlAlchemy,
)
from gestor_tareas.interfaces.api.dependencias import obtener_sesion
from gestor_tareas.interfaces.api.respuestas_error import (
    RESPUESTA_CUERPO_MALFORMADO,
    RESPUESTA_NO_ENCONTRADO,
)
from gestor_tareas.interfaces.api.v1.esquemas.workflow_oportunidades import (
    OrdenPasosEsquema,
    PasoWorkflowEsquema,
    PasoWorkflowSalidaEsquema,
)

enrutador = APIRouter(prefix="/workflow-oportunidades/pasos", tags=["Workflow de oportunidades"])


def _a_esquema(paso: PasoWorkflowOportunidad) -> PasoWorkflowSalidaEsquema:
    return PasoWorkflowSalidaEsquema(**asdict(paso))


def _repositorio(sesion: Session) -> RepositorioWorkflowOportunidadesSqlAlchemy:
    return RepositorioWorkflowOportunidadesSqlAlchemy(sesion)


@enrutador.get("", response_model=list[PasoWorkflowSalidaEsquema])
def listar(sesion: Session = Depends(obtener_sesion)) -> list[PasoWorkflowSalidaEsquema]:
    """Devuelve los pasos del workflow de las oportunidades ordenados por número."""
    return [_a_esquema(p) for p in ListarPasos(_repositorio(sesion)).ejecutar()]


@enrutador.post(
    "",
    response_model=PasoWorkflowSalidaEsquema,
    status_code=status.HTTP_201_CREATED,
    responses={**RESPUESTA_CUERPO_MALFORMADO},
)
def anadir(
    datos: PasoWorkflowEsquema, sesion: Session = Depends(obtener_sesion)
) -> PasoWorkflowSalidaEsquema:
    """Añade un paso al final del workflow: su número es el del último más uno. El
    nombre es obligatorio (1–50 caracteres sin contar los espacios de los extremos)."""
    return _a_esquema(AnadirPaso(_repositorio(sesion)).ejecutar(datos.nombre))


# Antes que `/{id_paso}`: aunque el convertidor `int` ya impide que "orden" se tome
# por un id, así queda claro qué ruta atiende cada petición.
@enrutador.put(
    "/orden",
    response_model=list[PasoWorkflowSalidaEsquema],
    responses={**RESPUESTA_CUERPO_MALFORMADO},
)
def reordenar(
    datos: OrdenPasosEsquema, sesion: Session = Depends(obtener_sesion)
) -> list[PasoWorkflowSalidaEsquema]:
    """Reordena los pasos: el primer id pasa a ser el paso 1, el segundo el 2, etc.
    Devuelve todos los pasos en el nuevo orden. `ids` debe incluir cada paso del
    workflow exactamente una vez; si falta alguno, se repite o no existe, responde
    422 y no cambia nada."""
    try:
        pasos = ReordenarPasos(_repositorio(sesion)).ejecutar(datos.ids)
    except OrdenDePasosInvalidoError as error:
        # Mismo formato que el resto de errores de validación del cuerpo, que es el
        # que publica el contrato para el 422.
        raise RequestValidationError(
            [{"type": "value_error", "loc": ("body", "ids"), "msg": str(error), "input": datos.ids}]
        ) from error
    return [_a_esquema(p) for p in pasos]


@enrutador.put(
    "/{id_paso:int}",
    response_model=PasoWorkflowSalidaEsquema,
    responses={**RESPUESTA_NO_ENCONTRADO, **RESPUESTA_CUERPO_MALFORMADO},
)
def renombrar(
    id_paso: int, datos: PasoWorkflowEsquema, sesion: Session = Depends(obtener_sesion)
) -> PasoWorkflowSalidaEsquema:
    """Cambia el nombre del paso (mismas reglas que en el alta); su número no cambia.
    404 si el id no existe."""
    return _a_esquema(RenombrarPaso(_repositorio(sesion)).ejecutar(id_paso, datos.nombre))


@enrutador.delete(
    "/{id_paso:int}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    responses={**RESPUESTA_NO_ENCONTRADO},
)
def eliminar(id_paso: int, sesion: Session = Depends(obtener_sesion)) -> Response:
    """Elimina el paso y renumera los siguientes para no dejar huecos (1..n). 404 si
    el id no existe."""
    EliminarPaso(_repositorio(sesion)).ejecutar(id_paso)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
