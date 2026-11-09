import sentry_sdk

from gestor_tareas.configuracion import Configuracion


def inicializar_sentry(configuracion: Configuracion) -> None:
    """Inicializa Sentry para la captura de errores si hay un DSN configurado."""
    if not configuracion.sentry_dsn:
        return

    sentry_sdk.init(
        dsn=configuracion.sentry_dsn,
        environment=configuracion.entorno,
        traces_sample_rate=1.0,
    )
