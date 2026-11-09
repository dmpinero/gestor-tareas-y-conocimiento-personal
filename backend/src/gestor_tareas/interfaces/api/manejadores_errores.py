import traceback

from fastapi import FastAPI, Request, status
from fastapi.exception_handlers import http_exception_handler
from fastapi.responses import JSONResponse, Response
from starlette.exceptions import HTTPException as HTTPExceptionDeStarlette
from starlette.routing import compile_path

from gestor_tareas.dominio.excepciones import (
    EntidadConDependenciasError,
    EntidadNoEncontradaError,
    FiltroDeListadoInvalidoError,
    NombreDuplicadoError,
)

_METODOS_HTTP = {"get", "put", "post", "delete", "options", "head", "patch", "trace"}


def _respuesta(codigo: int, error: Exception) -> JSONResponse:
    return JSONResponse(status_code=codigo, content={"detalle": str(error)})


def _metodos_permitidos(request: Request) -> set[str]:
    """Métodos HTTP documentados en el esquema OpenAPI para el path de la
    petición, en mayúsculas (p. ej. {"GET", "POST"}).

    Se usa el propio esquema OpenAPI —ya generado por FastAPI, fuente de
    verdad pública y estable— en vez de inspeccionar los objetos internos
    de ruteo (Starlette registra cada verbo HTTP de un mismo path como una
    Route independiente y, al construir un 405, solo tiene en cuenta los
    métodos de la PRIMERA ruta que coincide parcialmente con el path,
    dejando fuera a las demás: es un bug conocido de Starlette, y además
    la forma exacta de esos objetos internos —p. ej. _IncludedRouter en
    FastAPI— puede cambiar entre versiones).

    Varias plantillas pueden coincidir con el mismo path (p. ej.
    "/tareas/{id_tarea}" también matchea literalmente
    "/tareas/pendientes", ya que el parámetro no lleva convertidor
    de tipo): se prioriza la plantilla con menos parámetros —más
    específica—, igual que ya prioriza el propio enrutador al registrar
    primero las rutas literales y después las genéricas.
    """
    esquema = request.app.openapi()
    candidatas: list[tuple[int, dict]] = []
    for plantilla, operaciones in esquema.get("paths", {}).items():
        patron, _, _ = compile_path(plantilla)
        if patron.match(request.url.path):
            candidatas.append((plantilla.count("{"), operaciones))
    if not candidatas:
        return set()
    _, operaciones_mas_especificas = min(candidatas, key=lambda c: c[0])
    return {metodo.upper() for metodo in operaciones_mas_especificas if metodo in _METODOS_HTTP}


def registrar_manejadores_de_errores(aplicacion: FastAPI) -> None:
    """Traduce las excepciones de dominio a respuestas HTTP consistentes."""

    @aplicacion.exception_handler(HTTPExceptionDeStarlette)
    async def _http_exception(request: Request, error: HTTPExceptionDeStarlette) -> Response:
        if error.status_code == status.HTTP_405_METHOD_NOT_ALLOWED:
            metodos = _metodos_permitidos(request)
            if metodos:
                headers = dict(error.headers or {})
                headers["Allow"] = ", ".join(sorted(metodos))
                return JSONResponse(
                    status_code=error.status_code,
                    content={"detalle": error.detail},
                    headers=headers,
                )
        if error.status_code == status.HTTP_400_BAD_REQUEST:
            # Starlette traduce un multipart/form-data malformado a un 400 con
            # `MultiPartException` (ver `Request._get_form`); en este proyecto
            # ningún código propio lanza `HTTPException` manualmente, así que
            # cualquier 400 que llegue aquí es ese caso. Se remapea a 422 para
            # ser consistente con el resto de errores de entrada inválida.
            return _respuesta(status.HTTP_422_UNPROCESSABLE_CONTENT, Exception(error.detail))
        return await http_exception_handler(request, error)

    @aplicacion.exception_handler(EntidadNoEncontradaError)
    async def _no_encontrada(_: Request, error: EntidadNoEncontradaError) -> JSONResponse:
        return _respuesta(status.HTTP_404_NOT_FOUND, error)

    @aplicacion.exception_handler(NombreDuplicadoError)
    async def _nombre_duplicado(_: Request, error: NombreDuplicadoError) -> JSONResponse:
        return _respuesta(status.HTTP_409_CONFLICT, error)

    @aplicacion.exception_handler(EntidadConDependenciasError)
    async def _con_dependencias(_: Request, error: EntidadConDependenciasError) -> JSONResponse:
        return _respuesta(status.HTTP_409_CONFLICT, error)

    @aplicacion.exception_handler(FiltroDeListadoInvalidoError)
    async def _filtro_invalido(_: Request, error: FiltroDeListadoInvalidoError) -> JSONResponse:
        return _respuesta(status.HTTP_422_UNPROCESSABLE_CONTENT, error)

    @aplicacion.exception_handler(Exception)
    async def _error_no_controlado(_: Request, error: Exception) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detalle": str(error), "traza": traceback.format_exc()},
        )
