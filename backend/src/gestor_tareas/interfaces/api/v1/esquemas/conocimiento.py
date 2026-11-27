from pydantic import BaseModel, Field, field_validator

from gestor_tareas.dominio.conocimiento.entidades import Rol
from gestor_tareas.interfaces.api.v1.esquemas.comentario import InstanteUtc
from gestor_tareas.interfaces.api.v1.esquemas.texto import PATRON_NO_VACIO, TextoObligatorio

LONGITUD_MAXIMA_MENSAJE = 4000
MENSAJES_MAXIMOS = 20
LONGITUD_MAXIMA_BUSQUEDA = 200
RESULTADOS_POR_DEFECTO = 20
RESULTADOS_MAXIMOS = 50


class ConfiguradoEsquema(BaseModel):
    """Qué credenciales del backend están configuradas (nunca sus valores)."""

    notion: bool = Field(description="Hay `NOTION_TOKEN` en el backend.")
    anthropic: bool = Field(description="Hay `ANTHROPIC_API_KEY` en el backend.")


class EstadoConocimientoEsquema(BaseModel):
    """Estado de Conocimiento: credenciales y contenido del índice local de Notion."""

    configurado: ConfiguradoEsquema
    paginas: int = Field(description="Páginas de Notion en el índice.")
    fragmentos: int = Field(description="Trozos de texto en el índice.")
    ultima_sincronizacion: InstanteUtc | None = Field(
        description="Cuándo terminó la última sincronización completa; null si nunca."
    )


class ResumenSincronizacionEsquema(BaseModel):
    """Resultado de sincronizar con Notion."""

    paginas: int = Field(description="Páginas en el índice tras sincronizar.")
    fragmentos: int = Field(description="Trozos de texto en el índice tras sincronizar.")
    nuevas: int = Field(description="Páginas añadidas al índice.")
    actualizadas: int = Field(description="Páginas editadas en Notion que se han vuelto a bajar.")
    eliminadas: int = Field(description="Páginas que ya no están compartidas y se han quitado.")
    ultima_sincronizacion: InstanteUtc = Field(description="Cuándo ha terminado.")


class MensajeEsquema(BaseModel):
    """Un mensaje de la conversación."""

    rol: Rol = Field(description="Quién lo escribió: `usuario` o `asistente`.")
    texto: TextoObligatorio = Field(
        min_length=1, max_length=LONGITUD_MAXIMA_MENSAJE, json_schema_extra=PATRON_NO_VACIO
    )


class PreguntaEsquema(BaseModel):
    """Cuerpo de una pregunta: la conversación hasta ahora, terminada en la pregunta."""

    mensajes: list[MensajeEsquema] = Field(
        min_length=1,
        max_length=MENSAJES_MAXIMOS,
        description=(
            f"De 1 a {MENSAJES_MAXIMOS} mensajes, en orden. El último debe ser del "
            "`usuario` (si no, 422): es la pregunta que se responde."
        ),
    )

    @field_validator("mensajes")
    @classmethod
    def _termina_en_una_pregunta(cls, mensajes: list[MensajeEsquema]) -> list[MensajeEsquema]:
        if mensajes[-1].rol is not Rol.USUARIO:
            raise ValueError("El último mensaje debe ser del usuario.")
        return mensajes


class ResultadoBusquedaEsquema(BaseModel):
    """Un trozo de una página de Notion que coincide con la búsqueda."""

    pagina_id: str = Field(description="Id de la página en Notion.")
    titulo: str = Field(description="Título de la página.")
    url: str = Field(description="Enlace a la página en Notion.")
    fragmento: str = Field(description="Texto del trozo encontrado.")
    orden: int = Field(description="Posición del trozo dentro de su página (0 el primero).")


class ErrorConocimientoEsquema(BaseModel):
    """Error de Conocimiento, con un mensaje para el usuario."""

    detalle: str
