from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Configuracion(BaseSettings):
    """Configuración de la aplicación, cargada desde variables de entorno."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    entorno: str = "desarrollo"

    # PyMySQL usa "latin1" como charset por defecto si no se indica lo contrario,
    # lo que corrompe caracteres Unicode de 4 bytes (emoji, ciertos alfabetos).
    url_base_datos: str = (
        "mysql+pymysql://gestor:gestor@localhost:3306/gestor_tareas?charset=utf8mb4"
    )

    clave_secreta_jwt: str = "cambia-esta-clave-en-produccion"
    algoritmo_jwt: str = "HS256"
    minutos_expiracion_token: int = 60

    sentry_dsn: str | None = None
    otel_endpoint_exportador: str | None = None


@lru_cache
def obtener_configuracion() -> Configuracion:
    return Configuracion()
