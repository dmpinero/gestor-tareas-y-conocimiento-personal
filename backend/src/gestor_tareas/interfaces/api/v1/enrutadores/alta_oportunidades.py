"""API del alta automática de oportunidades (servicio "automatizador")."""

from functools import lru_cache
from pathlib import Path

from fastapi import APIRouter, Depends, FastAPI, Request, Response, status
from fastapi.responses import JSONResponse

from gestor_tareas.aplicacion.oportunidad.ejecucion import (
    OpcionNoValidaError,
    SinPreguntaPendienteError,
)
from gestor_tareas.aplicacion.oportunidad.servicio import (
    AltaEnCursoError,
    ConfiguracionNoDisponibleError,
    ServicioAltaOportunidades,
    SinEjecucionError,
)
from gestor_tareas.configuracion import obtener_configuracion
from gestor_tareas.dominio.oportunidad.entidades import SolicitudAltaOportunidad
from gestor_tareas.dominio.oportunidad.errores import SolicitudAltaOportunidadInvalidaError
from gestor_tareas.infraestructura.automatizacion.configuracion_json import (
    LectorConfiguracionJson,
)
from gestor_tareas.infraestructura.automatizacion.navegador_playwright import (
    fabrica_navegador_playwright,
)
from gestor_tareas.interfaces.api.v1.esquemas.alta_oportunidad import (
    EjecucionEsquema,
    RespuestaPreguntaEsquema,
    ResumenConfiguracionEsquema,
    SolicitudAltaEsquema,
)

enrutador = APIRouter(prefix="/alta-oportunidades", tags=["Alta de oportunidades"])

_SIN_EJECUCION = {404: {"description": "Todavía no se ha lanzado ningún alta"}}


@lru_cache
def obtener_servicio() -> ServicioAltaOportunidades:
    """Servicio único del proceso: guarda la ejecución en curso en memoria."""
    configuracion = obtener_configuracion()
    return ServicioAltaOportunidades(
        LectorConfiguracionJson(Path(configuracion.ruta_configuracion_alta_oportunidad)),
        fabrica_navegador_playwright(Path(configuracion.directorio_perfil_navegador)),
    )


@enrutador.get("/salud")
def comprobar_salud() -> dict[str, str]:
    """Comprueba que el servicio está vivo (no abre el navegador ni lee la configuración)."""
    return {"estado": "ok"}


@enrutador.get("/configuracion", response_model=ResumenConfiguracionEsquema)
def resumen_configuracion(
    servicio: ServicioAltaOportunidades = Depends(obtener_servicio),
) -> ResumenConfiguracionEsquema:
    """Valores fijos de la configuración local y fechas calculadas para hoy, o el
    motivo por el que la configuración no es válida."""
    return ResumenConfiguracionEsquema.desde(servicio.resumen_configuracion())


@enrutador.post(
    "/ejecucion",
    response_model=EjecucionEsquema,
    status_code=status.HTTP_201_CREATED,
    responses={
        409: {"description": "Ya hay un alta en curso"},
        422: {"description": "Algún campo variable no es válido"},
        503: {"description": "La configuración local falta o no es válida"},
    },
)
def lanzar(
    cuerpo: SolicitudAltaEsquema,
    servicio: ServicioAltaOportunidades = Depends(obtener_servicio),
) -> EjecucionEsquema:
    """Lanza el alta en el navegador. Nunca guarda sin un «Guardar» explícito."""
    solicitud = SolicitudAltaOportunidad.crear(
        cuerpo.prj, cuerpo.descripcion, cuerpo.duracion, cuerpo.importe, cuerpo.coste
    )
    return EjecucionEsquema.desde(servicio.iniciar(solicitud))


@enrutador.get("/ejecucion", response_model=EjecucionEsquema, responses=_SIN_EJECUCION)
def estado(servicio: ServicioAltaOportunidades = Depends(obtener_servicio)) -> EjecucionEsquema:
    """Estado del último alta: pasos, pregunta pendiente y resultado."""
    return EjecucionEsquema.desde(servicio.estado())


@enrutador.post(
    "/ejecucion/respuesta",
    response_model=EjecucionEsquema,
    responses={
        **_SIN_EJECUCION,
        409: {"description": "La pregunta ya no está pendiente o no admite respuesta"},
        422: {"description": "La respuesta no es una de las opciones"},
    },
)
def responder(
    cuerpo: RespuestaPreguntaEsquema,
    servicio: ServicioAltaOportunidades = Depends(obtener_servicio),
) -> EjecucionEsquema:
    """Responde a la pregunta pendiente del alta en curso."""
    return EjecucionEsquema.desde(servicio.responder(cuerpo.id_pregunta, cuerpo.valor))


@enrutador.get(
    "/ejecucion/captura",
    response_class=Response,
    responses={
        200: {"content": {"image/png": {}}, "description": "Captura del resultado guardado"},
        404: {"description": "No hay captura del resultado"},
    },
)
def captura(servicio: ServicioAltaOportunidades = Depends(obtener_servicio)) -> Response:
    """Captura PNG de la pantalla tras pulsar «Guardar»."""
    return Response(
        content=servicio.captura(),
        media_type="image/png",
        headers={"Cache-Control": "no-store"},
    )


def registrar_manejadores_alta(aplicacion: FastAPI) -> None:
    """Traduce los errores del alta a respuestas HTTP con su mensaje en "detalle"."""
    codigos: dict[type[Exception], int] = {
        SolicitudAltaOportunidadInvalidaError: status.HTTP_422_UNPROCESSABLE_CONTENT,
        OpcionNoValidaError: status.HTTP_422_UNPROCESSABLE_CONTENT,
        AltaEnCursoError: status.HTTP_409_CONFLICT,
        SinPreguntaPendienteError: status.HTTP_409_CONFLICT,
        SinEjecucionError: status.HTTP_404_NOT_FOUND,
        ConfiguracionNoDisponibleError: status.HTTP_503_SERVICE_UNAVAILABLE,
    }

    def manejador(codigo: int):  # closure: un manejador por código
        async def _manejar(_: Request, error: Exception) -> JSONResponse:
            return JSONResponse(status_code=codigo, content={"detalle": str(error)})

        return _manejar

    for tipo, codigo in codigos.items():
        aplicacion.add_exception_handler(tipo, manejador(codigo))
