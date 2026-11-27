from functools import lru_cache

from pydantic import SecretStr, field_validator
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

    # Servicio "automatizador" (alta de oportunidades): la configuración con los
    # datos corporativos es un JSON local que nunca se versiona, montado aquí.
    ruta_configuracion_alta_oportunidad: str = "/config/alta_oportunidad.json"
    directorio_perfil_navegador: str = "/perfil-navegador"

    # Conocimiento (chat con las notas de Notion). Sin ellas, la sección lo explica y
    # no sincroniza ni responde. Son secretos: nunca se registran ni se devuelven.
    notion_token: SecretStr | None = None
    anthropic_api_key: SecretStr | None = None

    @field_validator("notion_token", "anthropic_api_key", mode="before")
    @classmethod
    def _vacia_es_sin_configurar(cls, valor: object) -> object:
        if isinstance(valor, str) and not valor.strip():
            return None
        return valor.strip() if isinstance(valor, str) else valor


@lru_cache
def obtener_configuracion() -> Configuracion:
    return Configuracion()
