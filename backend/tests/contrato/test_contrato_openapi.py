import re
from datetime import datetime

import schemathesis
from pydantic import ValidationError
from sqlalchemy import text

from gestor_tareas.dominio.excepciones import NombreDuplicadoError
from gestor_tareas.dominio.grupo_estados.entidades import GrupoEstados
from gestor_tareas.infraestructura.persistencia.repositorios.repositorio_grupos_estados_sqlalchemy import (  # noqa: E501
    RepositorioGruposEstadosSqlAlchemy,
)
from gestor_tareas.infraestructura.persistencia.repositorios.repositorio_workflows_sqlalchemy import (  # noqa: E501
    RepositorioWorkflowsSqlAlchemy,
)
from gestor_tareas.infraestructura.persistencia.sesion import FabricaSesiones
from gestor_tareas.interfaces.api.v1.esquemas.comentario import ComentarioCrearEsquema
from gestor_tareas.interfaces.api.v1.esquemas.tarea import PATRON_FECHA_HORA
from gestor_tareas.main import crear_aplicacion

esquema = schemathesis.openapi.from_asgi("/openapi.json", crear_aplicacion())

# Cuando OpenAPI/JSON Schema no pueda expresar una restricción de negocio que
# sí se valida en Pydantic, añade aquí la ruta y el check a excluir, con un
# comentario que explique el motivo (ver el historial del proyecto de
# referencia para ejemplos). De momento no hay ninguna excepción.
_CHECKS_EXCLUIDOS_POR_RUTA: dict[str, list] = {}

_FECHA_HORA = re.compile(PATRON_FECHA_HORA)


def _a_fecha(valor: object) -> datetime | None:
    if isinstance(valor, str) and _FECHA_HORA.fullmatch(valor):
        return datetime.fromisoformat(valor).replace(microsecond=0)
    return None


def _respetar_orden_de_las_fechas(case: schemathesis.Case) -> None:
    """JSON Schema no puede comparar dos campos: que `fecha_vencimiento` no sea
    anterior a `fecha_creacion` (422) no figura en el contrato. En lugar de excluir
    `positive_data_acceptance` de toda la ruta, se corrige solo ese par de fechas
    en los cuerpos generados y el resto del cuerpo se sigue probando entero."""
    cuerpo = case.body
    if not isinstance(cuerpo, dict):
        return
    creacion = _a_fecha(cuerpo.get("fecha_creacion"))
    vencimiento = _a_fecha(cuerpo.get("fecha_vencimiento"))
    if creacion is not None and vencimiento is not None and vencimiento < creacion:
        cuerpo["fecha_vencimiento"] = cuerpo["fecha_creacion"]


def _ids_de_los_pasos_actuales(id_workflow: object) -> list[int] | None:
    sesion = FabricaSesiones()
    try:
        workflows = RepositorioWorkflowsSqlAlchemy(sesion).listar()
    finally:
        sesion.close()
    workflow = next((w for w in workflows if w.id == id_workflow), None)
    return None if workflow is None else [p.id for p in workflow.pasos]


def _reordenar_los_pasos_que_existen(case: schemathesis.Case) -> None:
    """JSON Schema no puede exigir que `ids` sea justo una permutación de los pasos
    guardados (si no, 422). En los casos que el contrato da por válidos se envían
    los ids actuales del workflow en orden inverso, para seguir probando la
    respuesta 200 (si el workflow no existe, el 404 es válido); los casos inválidos
    se envían tal cual."""
    if not (case.path == "/api/v1/workflows/{id_workflow}/orden" and _es_positivo_con_cuerpo(case)):
        return
    ids = _ids_de_los_pasos_actuales((case.path_parameters or {}).get("id_workflow"))
    if ids is not None:
        case.body["ids"] = ids[::-1]


def _es_positivo_con_cuerpo(case: schemathesis.Case) -> bool:
    meta = case.meta
    return meta is not None and meta.generation.mode.is_positive and isinstance(case.body, dict)


_GRUPO_DEL_CONTRATO = "Grupo del contrato"
_WORKFLOW_DEL_CONTRATO = "Workflow del contrato"


def _id_de_un_workflow() -> int:
    """El id de un workflow guardado, creado si no existe (las peticiones generadas
    pueden haberlos borrado todos)."""
    sesion = FabricaSesiones()
    try:
        repositorio = RepositorioWorkflowsSqlAlchemy(sesion)
        workflow = next(iter(repositorio.listar()), None)
        if workflow is None:
            workflow = repositorio.crear(_WORKFLOW_DEL_CONTRATO)
        return workflow.id
    finally:
        sesion.close()


def _asignar_workflows_que_existen(case: schemathesis.Case) -> None:
    """Como con los grupos: JSON Schema no puede exigir que `workflow_id` sea un
    workflow guardado (si no, 422). En los casos válidos se envía el de uno que existe."""
    if (
        case.method in ("POST", "PUT")
        and case.path in ("/api/v1/tareas", "/api/v1/tareas/{id_tarea}")
        and _es_positivo_con_cuerpo(case)
        and case.body.get("workflow_id") is not None
    ):
        case.body["workflow_id"] = _id_de_un_workflow()


def _grupo_con_estados() -> GrupoEstados:
    """Un grupo con dos estados, creado si no existe (las peticiones generadas pueden
    haberlo renombrado o borrado, o haberle quitado los estados)."""
    sesion = FabricaSesiones()
    try:
        repositorio = RepositorioGruposEstadosSqlAlchemy(sesion)
        grupo = next((g for g in repositorio.listar() if len(g.estados) >= 2), None)
        if grupo is not None:
            return grupo
        try:
            grupo = repositorio.crear(_GRUPO_DEL_CONTRATO)
        except NombreDuplicadoError:
            grupo = next(g for g in repositorio.listar() if g.nombre == _GRUPO_DEL_CONTRATO)
        while len(grupo.estados) < 2:
            grupo = repositorio.anadir_estado(grupo.id, f"Estado {len(grupo.estados) + 1}")
        return grupo
    finally:
        sesion.close()


def _asignar_grupos_que_existen(case: schemathesis.Case) -> None:
    """JSON Schema no puede exigir que `grupo_estados_id` sea un grupo guardado y con
    estados (si no, 422). En los casos que el contrato da por válidos se envía el de un
    grupo con estados, para seguir probando el 200/201."""
    if (
        case.method in ("POST", "PUT")
        and case.path in ("/api/v1/tareas", "/api/v1/tareas/{id_tarea}")
        and _es_positivo_con_cuerpo(case)
        and case.body.get("grupo_estados_id") is not None
    ):
        case.body["grupo_estados_id"] = _grupo_con_estados().id


def _mover_a_un_estado_del_grupo_de_la_tarea(case: schemathesis.Case) -> None:
    """JSON Schema no puede exigir que `estado_id` sea un estado del grupo de la tarea
    (si no, 422). En los casos válidos, si la tarea existe se le asigna un grupo con
    estados y se pide su último estado; si no existe, el 404 es válido."""
    if not (case.path == "/api/v1/tareas/{id_tarea}/estado" and _es_positivo_con_cuerpo(case)):
        return
    id_tarea = (case.path_parameters or {}).get("id_tarea")
    grupo = _grupo_con_estados()
    sesion = FabricaSesiones()
    try:
        sesion.execute(
            text("UPDATE tareas SET grupo_estados_id = :grupo, estado_id = :estado WHERE id = :id"),
            {"grupo": grupo.id, "estado": grupo.estados[0].id, "id": id_tarea},
        )
        sesion.commit()
    finally:
        sesion.close()
    case.body["estado_id"] = grupo.estados[-1].id


def _reordenar_los_estados_que_existen(case: schemathesis.Case) -> None:
    """Como en los pasos del workflow: en los casos válidos se envían los ids de los
    estados del grupo en orden inverso (si el grupo no existe, el 404 es válido)."""
    if not (
        case.path == "/api/v1/grupos-estados/{id_grupo}/orden" and _es_positivo_con_cuerpo(case)
    ):
        return
    id_grupo = (case.path_parameters or {}).get("id_grupo")
    sesion = FabricaSesiones()
    try:
        grupos = RepositorioGruposEstadosSqlAlchemy(sesion).listar()
    finally:
        sesion.close()
    grupo = next((g for g in grupos if g.id == id_grupo), None)
    if grupo is not None:
        case.body["ids"] = [e.id for e in grupo.estados][::-1]


def _comentar_con_texto_visible_valido(case: schemathesis.Case) -> None:
    """JSON Schema no puede contar el texto visible del HTML: que tenga de 1 a 500
    caracteres sin etiquetas, y que el HTML saneado no pase de 10000 (si no, 422), no
    figura en el contrato más que en la descripción de `texto`. En los casos que el
    contrato da por válidos, si el texto generado no cumple esas reglas se envía uno
    que sí; el resto de la petición se sigue probando entera."""
    if not (
        case.method in ("POST", "PUT")
        and "/comentarios" in case.path
        and _es_positivo_con_cuerpo(case)
        and isinstance(case.body.get("texto"), str)
    ):
        return
    try:
        ComentarioCrearEsquema(texto=case.body["texto"])
    except ValidationError:
        case.body["texto"] = "Comentario del contrato"


@esquema.parametrize()
def test_la_api_cumple_su_contrato_openapi(case: schemathesis.Case) -> None:
    """Genera peticiones a partir del OpenAPI y valida que las respuestas cumplen el esquema."""
    _respetar_orden_de_las_fechas(case)
    _reordenar_los_pasos_que_existen(case)
    _asignar_grupos_que_existen(case)
    _asignar_workflows_que_existen(case)
    _mover_a_un_estado_del_grupo_de_la_tarea(case)
    _reordenar_los_estados_que_existen(case)
    _comentar_con_texto_visible_valido(case)
    excluidos = _CHECKS_EXCLUIDOS_POR_RUTA.get(case.path)
    case.call_and_validate(excluded_checks=excluidos or None)
