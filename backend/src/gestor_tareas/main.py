from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator

from gestor_tareas.configuracion import obtener_configuracion
from gestor_tareas.infraestructura.observabilidad.registro_logs import (
    configurar_registro_logs,
)
from gestor_tareas.infraestructura.observabilidad.sentry import inicializar_sentry
from gestor_tareas.infraestructura.observabilidad.trazas import configurar_trazas
from gestor_tareas.interfaces.api.manejadores_errores import registrar_manejadores_de_errores
from gestor_tareas.interfaces.api.middleware.cabeceras_seguridad import (
    MiddlewareCabecerasSeguridad,
)
from gestor_tareas.interfaces.api.v1.enrutadores import (
    comentarios,
    etiquetas,
    personas,
    salud,
    tareas,
    workflow_oportunidades,
)


def crear_aplicacion() -> FastAPI:
    """Factoría que construye y configura la aplicación FastAPI."""
    configuracion = obtener_configuracion()

    configurar_registro_logs()
    inicializar_sentry(configuracion)

    aplicacion = FastAPI(
        title="Gestor de Tareas y Conocimiento Personal",
        description="API para la gestión de tareas y conocimiento personal.",
        version="0.1.0",
    )

    aplicacion.add_middleware(MiddlewareCabecerasSeguridad)
    registrar_manejadores_de_errores(aplicacion)

    aplicacion.include_router(salud.enrutador, prefix="/api/v1")
    aplicacion.include_router(tareas.enrutador, prefix="/api/v1")
    aplicacion.include_router(comentarios.enrutador, prefix="/api/v1")
    aplicacion.include_router(etiquetas.enrutador, prefix="/api/v1")
    aplicacion.include_router(personas.enrutador, prefix="/api/v1")
    aplicacion.include_router(workflow_oportunidades.enrutador, prefix="/api/v1")

    Instrumentator().instrument(aplicacion).expose(
        aplicacion, endpoint="/metricas", include_in_schema=False
    )
    configurar_trazas(aplicacion, configuracion)

    return aplicacion


app = crear_aplicacion()
