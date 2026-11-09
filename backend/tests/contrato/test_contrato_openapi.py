import schemathesis

from gestor_tareas.main import crear_aplicacion

esquema = schemathesis.openapi.from_asgi("/openapi.json", crear_aplicacion())

# Cuando OpenAPI/JSON Schema no pueda expresar una restricción de negocio que
# sí se valida en Pydantic, añade aquí la ruta y el check a excluir, con un
# comentario que explique el motivo (ver el historial del proyecto de
# referencia para ejemplos). De momento no hay ninguna excepción.
_CHECKS_EXCLUIDOS_POR_RUTA: dict[str, list] = {}


@esquema.parametrize()
def test_la_api_cumple_su_contrato_openapi(case: schemathesis.Case) -> None:
    """Genera peticiones a partir del OpenAPI y valida que las respuestas cumplen el esquema."""
    excluidos = _CHECKS_EXCLUIDOS_POR_RUTA.get(case.path)
    case.call_and_validate(excluded_checks=excluidos or None)
