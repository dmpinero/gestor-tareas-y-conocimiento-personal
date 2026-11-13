from dataclasses import asdict

from fastapi import APIRouter, Depends, Response, status
from fastapi.exceptions import RequestValidationError
from sqlalchemy.orm import Session

from gestor_tareas.aplicacion.workflow.casos_uso import (
    AnadirPaso,
    CrearWorkflow,
    EliminarPaso,
    EliminarWorkflow,
    ListarWorkflows,
    RenombrarPaso,
    RenombrarWorkflow,
    ReordenarPasos,
)
from gestor_tareas.dominio.excepciones import OrdenDePasosInvalidoError
from gestor_tareas.dominio.workflow.entidades import Workflow
from gestor_tareas.infraestructura.persistencia.repositorios.repositorio_workflows_sqlalchemy import (  # noqa: E501
    RepositorioWorkflowsSqlAlchemy,
)
from gestor_tareas.interfaces.api.dependencias import obtener_sesion
from gestor_tareas.interfaces.api.respuestas_error import (
    RESPUESTA_CONFLICTO,
    RESPUESTA_CUERPO_MALFORMADO,
    RESPUESTA_NO_ENCONTRADO,
)
from gestor_tareas.interfaces.api.v1.esquemas.workflows import (
    OrdenPasosEsquema,
    PasoWorkflowEsquema,
    WorkflowEsquema,
    WorkflowSalidaEsquema,
)

enrutador = APIRouter(prefix="/workflows", tags=["Workflows"])


def _a_esquema(workflow: Workflow) -> WorkflowSalidaEsquema:
    return WorkflowSalidaEsquema(**asdict(workflow))


def _repositorio(sesion: Session) -> RepositorioWorkflowsSqlAlchemy:
    return RepositorioWorkflowsSqlAlchemy(sesion)


@enrutador.get("", response_model=list[WorkflowSalidaEsquema])
def listar(sesion: Session = Depends(obtener_sesion)) -> list[WorkflowSalidaEsquema]:
    """Devuelve los workflows por nombre (sin distinguir mayúsculas), cada uno con sus
    pasos por número."""
    return [_a_esquema(w) for w in ListarWorkflows(_repositorio(sesion)).ejecutar()]


@enrutador.post(
    "",
    response_model=WorkflowSalidaEsquema,
    status_code=status.HTTP_201_CREATED,
    responses={**RESPUESTA_CONFLICTO, **RESPUESTA_CUERPO_MALFORMADO},
)
def crear(
    datos: WorkflowEsquema, sesion: Session = Depends(obtener_sesion)
) -> WorkflowSalidaEsquema:
    """Crea un workflow sin pasos. El nombre es obligatorio (1–50 caracteres sin contar
    los espacios de los extremos) y único sin distinguir mayúsculas (409)."""
    return _a_esquema(CrearWorkflow(_repositorio(sesion)).ejecutar(datos.nombre))


@enrutador.put(
    "/{id_workflow:int}",
    response_model=WorkflowSalidaEsquema,
    responses={**RESPUESTA_NO_ENCONTRADO, **RESPUESTA_CONFLICTO, **RESPUESTA_CUERPO_MALFORMADO},
)
def renombrar(
    id_workflow: int, datos: WorkflowEsquema, sesion: Session = Depends(obtener_sesion)
) -> WorkflowSalidaEsquema:
    """Cambia el nombre del workflow (mismas reglas que en el alta); sus pasos no
    cambian. 404 si el workflow no existe."""
    workflow = RenombrarWorkflow(_repositorio(sesion)).ejecutar(id_workflow, datos.nombre)
    return _a_esquema(workflow)


@enrutador.delete(
    "/{id_workflow:int}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    responses={**RESPUESTA_NO_ENCONTRADO},
)
def eliminar(id_workflow: int, sesion: Session = Depends(obtener_sesion)) -> Response:
    """Elimina el workflow con sus pasos; sus tareas quedan sin workflow y conservan
    sus subtareas. 404 si no existe."""
    EliminarWorkflow(_repositorio(sesion)).ejecutar(id_workflow)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@enrutador.post(
    "/{id_workflow:int}/pasos",
    response_model=WorkflowSalidaEsquema,
    status_code=status.HTTP_201_CREATED,
    responses={**RESPUESTA_NO_ENCONTRADO, **RESPUESTA_CUERPO_MALFORMADO},
)
def anadir_paso(
    id_workflow: int, datos: PasoWorkflowEsquema, sesion: Session = Depends(obtener_sesion)
) -> WorkflowSalidaEsquema:
    """Añade un paso al final del workflow (su número es el del último más uno) y
    devuelve el workflow. El nombre es obligatorio (1–50 caracteres sin contar los
    espacios de los extremos). 404 si el workflow no existe."""
    workflow = AnadirPaso(_repositorio(sesion)).ejecutar(id_workflow, datos.nombre)
    return _a_esquema(workflow)


@enrutador.put(
    "/{id_workflow:int}/pasos/{id_paso:int}",
    response_model=WorkflowSalidaEsquema,
    responses={**RESPUESTA_NO_ENCONTRADO, **RESPUESTA_CUERPO_MALFORMADO},
)
def renombrar_paso(
    id_workflow: int,
    id_paso: int,
    datos: PasoWorkflowEsquema,
    sesion: Session = Depends(obtener_sesion),
) -> WorkflowSalidaEsquema:
    """Cambia el nombre del paso (mismas reglas que en el alta) y devuelve el workflow;
    su número no cambia. 404 si el workflow no existe o el paso no es suyo."""
    workflow = RenombrarPaso(_repositorio(sesion)).ejecutar(id_workflow, id_paso, datos.nombre)
    return _a_esquema(workflow)


@enrutador.delete(
    "/{id_workflow:int}/pasos/{id_paso:int}",
    response_model=WorkflowSalidaEsquema,
    responses={**RESPUESTA_NO_ENCONTRADO},
)
def eliminar_paso(
    id_workflow: int, id_paso: int, sesion: Session = Depends(obtener_sesion)
) -> WorkflowSalidaEsquema:
    """Elimina el paso, renumera los siguientes del workflow para no dejar huecos
    (1..n) y devuelve el workflow. 404 si el workflow no existe o el paso no es suyo."""
    return _a_esquema(EliminarPaso(_repositorio(sesion)).ejecutar(id_workflow, id_paso))


@enrutador.put(
    "/{id_workflow:int}/orden",
    response_model=WorkflowSalidaEsquema,
    responses={**RESPUESTA_NO_ENCONTRADO, **RESPUESTA_CUERPO_MALFORMADO},
)
def reordenar_pasos(
    id_workflow: int, datos: OrdenPasosEsquema, sesion: Session = Depends(obtener_sesion)
) -> WorkflowSalidaEsquema:
    """Reordena los pasos del workflow: el primer id pasa a ser el paso 1, el segundo
    el 2, etc. Devuelve el workflow con los pasos en el nuevo orden. `ids` debe incluir cada paso
    del workflow exactamente una vez; si falta alguno, se repite o no es del workflow,
    422 y no cambia nada. 404 si el workflow no existe."""
    try:
        workflow = ReordenarPasos(_repositorio(sesion)).ejecutar(id_workflow, datos.ids)
    except OrdenDePasosInvalidoError as error:
        # Mismo formato que el resto de errores de validación del cuerpo, que es el
        # que publica el contrato para el 422.
        raise RequestValidationError(
            [{"type": "value_error", "loc": ("body", "ids"), "msg": str(error), "input": datos.ids}]
        ) from error
    return _a_esquema(workflow)
