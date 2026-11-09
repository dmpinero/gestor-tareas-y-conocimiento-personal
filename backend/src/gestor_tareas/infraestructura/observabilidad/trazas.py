from fastapi import FastAPI
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from gestor_tareas.configuracion import Configuracion


def configurar_trazas(aplicacion: FastAPI, configuracion: Configuracion) -> None:
    """Configura la exportación de trazas OpenTelemetry si hay un endpoint configurado."""
    if not configuracion.otel_endpoint_exportador:
        return

    proveedor = TracerProvider(resource=Resource.create({SERVICE_NAME: "gestor-tareas-api"}))
    exportador = OTLPSpanExporter(endpoint=configuracion.otel_endpoint_exportador)
    proveedor.add_span_processor(BatchSpanProcessor(exportador))
    trace.set_tracer_provider(proveedor)

    FastAPIInstrumentor.instrument_app(aplicacion, tracer_provider=proveedor)
