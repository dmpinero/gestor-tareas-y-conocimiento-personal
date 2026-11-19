"""Aplicación del servicio "automatizador": el alta automática de oportunidades.

Va aparte del backend principal porque necesita Playwright, un navegador con
ventana (WSLg) y la configuración local; no usa la base de datos.
"""

from fastapi import FastAPI

from gestor_tareas.infraestructura.observabilidad.registro_logs import (
    configurar_registro_logs,
)
from gestor_tareas.interfaces.api.manejadores_errores import registrar_manejadores_de_errores
from gestor_tareas.interfaces.api.middleware.cabeceras_seguridad import (
    MiddlewareCabecerasSeguridad,
)
from gestor_tareas.interfaces.api.v1.enrutadores import alta_oportunidades


def crear_aplicacion_automatizador() -> FastAPI:
    configurar_registro_logs()

    aplicacion = FastAPI(
        title="Automatizador de altas de oportunidades",
        description="Lanza y sigue el alta de oportunidades en el navegador.",
        version="0.1.0",
        # Bajo el mismo prefijo que proxifica el frontend hacia este servicio.
        openapi_url="/api/v1/alta-oportunidades/openapi.json",
        docs_url=None,
        redoc_url=None,
    )
    aplicacion.add_middleware(MiddlewareCabecerasSeguridad)
    registrar_manejadores_de_errores(aplicacion)
    alta_oportunidades.registrar_manejadores_alta(aplicacion)
    aplicacion.include_router(alta_oportunidades.enrutador, prefix="/api/v1")
    return aplicacion


app = crear_aplicacion_automatizador()
