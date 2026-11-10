import re
from datetime import datetime

import schemathesis

from gestor_tareas.infraestructura.persistencia.repositorios.repositorio_workflow_oportunidades_sqlalchemy import (  # noqa: E501
    RepositorioWorkflowOportunidadesSqlAlchemy,
)
from gestor_tareas.infraestructura.persistencia.sesion import FabricaSesiones
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


def _ids_de_los_pasos_actuales() -> list[int]:
    sesion = FabricaSesiones()
    try:
        return [p.id for p in RepositorioWorkflowOportunidadesSqlAlchemy(sesion).listar_pasos()]
    finally:
        sesion.close()


def _reordenar_los_pasos_que_existen(case: schemathesis.Case) -> None:
    """JSON Schema no puede exigir que `ids` sea justo una permutación de los pasos
    guardados (si no, 422). En los casos que el contrato da por válidos se envían
    los ids actuales en orden inverso, para seguir probando la respuesta 200; los
    casos inválidos se envían tal cual."""
    meta = case.meta
    cuerpo = case.body
    if (
        case.path.endswith("/pasos/orden")
        and meta is not None
        and meta.generation.mode.is_positive
        and isinstance(cuerpo, dict)
    ):
        cuerpo["ids"] = _ids_de_los_pasos_actuales()[::-1]


@esquema.parametrize()
def test_la_api_cumple_su_contrato_openapi(case: schemathesis.Case) -> None:
    """Genera peticiones a partir del OpenAPI y valida que las respuestas cumplen el esquema."""
    _respetar_orden_de_las_fechas(case)
    _reordenar_los_pasos_que_existen(case)
    excluidos = _CHECKS_EXCLUIDOS_POR_RUTA.get(case.path)
    case.call_and_validate(excluded_checks=excluidos or None)
