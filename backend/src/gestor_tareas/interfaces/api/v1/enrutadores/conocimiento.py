"""API de Conocimiento: el índice local de las notas de Notion y el chat sobre él."""

import json
import logging
from collections.abc import Iterator
from dataclasses import asdict
from functools import lru_cache

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from gestor_tareas.aplicacion.conocimiento.casos_uso import ObtenerEstado, Preguntar, Sincronizar
from gestor_tareas.configuracion import obtener_configuracion
from gestor_tareas.dominio.conocimiento.entidades import (
    EventoError,
    EventoFin,
    EventoFuentes,
    EventoRespuesta,
    EventoTexto,
    MensajeChat,
)
from gestor_tareas.dominio.conocimiento.errores import ConocimientoSinConfigurarError
from gestor_tareas.dominio.conocimiento.puertos import (
    FuenteNotion,
    ModeloLenguaje,
    RepositorioConocimiento,
)
from gestor_tareas.infraestructura.llm.modelo_anthropic import ModeloAnthropic
from gestor_tareas.infraestructura.notion.cliente_notion import ClienteNotion
from gestor_tareas.infraestructura.persistencia.repositorios.repositorio_conocimiento_sqlalchemy import (  # noqa: E501
    RepositorioConocimientoSqlAlchemy,
)
from gestor_tareas.interfaces.api.dependencias import obtener_sesion
from gestor_tareas.interfaces.api.respuestas_error import RESPUESTA_CUERPO_MALFORMADO
from gestor_tareas.interfaces.api.v1.esquemas.conocimiento import (
    ConfiguradoEsquema,
    ErrorConocimientoEsquema,
    EstadoConocimientoEsquema,
    PreguntaEsquema,
    ResumenSincronizacionEsquema,
)

enrutador = APIRouter(prefix="/conocimiento", tags=["Conocimiento"])

_registro = logging.getLogger(__name__)

SIN_NOTION = "Falta configurar NOTION_TOKEN en backend/.env"
SIN_ANTHROPIC = "Falta configurar ANTHROPIC_API_KEY en backend/.env"
_ERROR_INESPERADO = "Ha ocurrido un error inesperado al preparar la respuesta."

_ERRORES_SINCRONIZAR: dict[int | str, dict] = {
    409: {"model": ErrorConocimientoEsquema, "description": "Ya hay una sincronización en curso"},
    502: {"model": ErrorConocimientoEsquema, "description": "Notion no responde o da un error"},
    503: {"model": ErrorConocimientoEsquema, "description": "Falta configurar NOTION_TOKEN"},
}
_RESPUESTAS_PREGUNTAR: dict[int | str, dict] = {
    200: {
        "description": (
            "Respuesta en streaming (Server-Sent Events). Eventos, en este orden: "
            '`fuentes` (data: `[{"pagina_id", "titulo", "url"}]`, las páginas citadas), '
            'varios `texto` (data: `{"delta": "..."}`) y `fin` (data: `{}`); o, si la '
            'respuesta no puede completarse, `error` (data: `{"detalle": "..."}`) en '
            "lugar de `fin`."
        ),
        # Esquema de cada evento del flujo (como lo valida el contrato): su nombre y su
        # `data`, que es el JSON descrito arriba en una sola línea.
        "content": {
            "text/event-stream": {
                "schema": {
                    "type": "object",
                    "required": ["event", "data"],
                    "properties": {
                        "event": {"type": "string", "enum": ["fuentes", "texto", "fin", "error"]},
                        "data": {"type": "string", "description": "JSON del evento."},
                    },
                }
            }
        },
    },
    503: {"model": ErrorConocimientoEsquema, "description": "Falta configurar ANTHROPIC_API_KEY"},
    **RESPUESTA_CUERPO_MALFORMADO,
}


def obtener_repositorio_conocimiento(
    sesion: Session = Depends(obtener_sesion),
) -> RepositorioConocimiento:
    return RepositorioConocimientoSqlAlchemy(sesion)


def obtener_fuente_notion() -> Iterator[FuenteNotion | None]:
    """El cliente de Notion con el token de la configuración (``None`` sin él),
    cerrado al terminar la petición."""
    token = obtener_configuracion().notion_token
    if token is None:
        yield None
        return
    cliente = ClienteNotion(token.get_secret_value())
    try:
        yield cliente
    finally:
        cliente.cerrar()


@lru_cache
def _modelo_para(clave: str) -> ModeloAnthropic:
    return ModeloAnthropic.crear(clave)


def obtener_modelo_lenguaje() -> ModeloLenguaje | None:
    """Claude con la clave de la configuración (``None`` sin ella)."""
    clave = obtener_configuracion().anthropic_api_key
    return None if clave is None else _modelo_para(clave.get_secret_value())


@enrutador.get("/estado", response_model=EstadoConocimientoEsquema)
def estado(
    repositorio: RepositorioConocimiento = Depends(obtener_repositorio_conocimiento),
    fuente: FuenteNotion | None = Depends(obtener_fuente_notion),
    modelo: ModeloLenguaje | None = Depends(obtener_modelo_lenguaje),
) -> EstadoConocimientoEsquema:
    """Qué credenciales del backend están configuradas (sin sus valores), cuántas
    páginas y trozos de Notion hay en el índice local y cuándo terminó la última
    sincronización."""
    indice = ObtenerEstado(repositorio).ejecutar()
    return EstadoConocimientoEsquema(
        configurado=ConfiguradoEsquema(notion=fuente is not None, anthropic=modelo is not None),
        paginas=indice.paginas,
        fragmentos=indice.fragmentos,
        ultima_sincronizacion=indice.ultima_sincronizacion,
    )


@enrutador.post(
    "/sincronizar", response_model=ResumenSincronizacionEsquema, responses=_ERRORES_SINCRONIZAR
)
def sincronizar(
    repositorio: RepositorioConocimiento = Depends(obtener_repositorio_conocimiento),
    fuente: FuenteNotion | None = Depends(obtener_fuente_notion),
) -> ResumenSincronizacionEsquema:
    """Pone el índice local al día con las páginas (y entradas de bases de datos)
    compartidas con la integración de Notion: baja solo las nuevas y las editadas
    desde la última vez y quita las que ya no están compartidas. 503 sin
    `NOTION_TOKEN`, 502 si Notion falla (lo ya bajado se conserva) y 409 si ya hay
    otra sincronización en curso."""
    if fuente is None:
        raise ConocimientoSinConfigurarError(SIN_NOTION)
    resumen = Sincronizar(fuente, repositorio).ejecutar()
    return ResumenSincronizacionEsquema(**asdict(resumen))


@enrutador.post("/preguntar", response_class=StreamingResponse, responses=_RESPUESTAS_PREGUNTAR)
def preguntar(
    datos: PreguntaEsquema,
    repositorio: RepositorioConocimiento = Depends(obtener_repositorio_conocimiento),
    modelo: ModeloLenguaje | None = Depends(obtener_modelo_lenguaje),
) -> StreamingResponse:
    """Responde a la última pregunta de la conversación con las notas de Notion del
    índice local, en streaming (ver la respuesta 200). La respuesta es en español,
    se basa solo en los trozos encontrados y cita sus páginas; si no encuentra nada
    relevante lo dice en lugar de inventar. 503 sin `ANTHROPIC_API_KEY`."""
    if modelo is None:
        raise ConocimientoSinConfigurarError(SIN_ANTHROPIC)
    mensajes = [MensajeChat(rol=m.rol, texto=m.texto) for m in datos.mensajes]
    eventos = Preguntar(repositorio, modelo).ejecutar(mensajes)
    return StreamingResponse(
        _flujo_sse(eventos),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


def _flujo_sse(eventos: Iterator[EventoRespuesta]) -> Iterator[str]:
    try:
        for evento in eventos:
            yield _a_sse(evento)
    except Exception:
        # La respuesta ya empezó (200): el fallo solo puede contarse como evento.
        _registro.exception("Fallo inesperado al responder una pregunta de Conocimiento")
        yield _a_sse(EventoError(_ERROR_INESPERADO))


def _a_sse(evento: EventoRespuesta) -> str:
    match evento:
        case EventoFuentes(fuentes=fuentes):
            nombre, datos = "fuentes", [asdict(f) for f in fuentes]
        case EventoTexto(delta=delta):
            nombre, datos = "texto", {"delta": delta}
        case EventoFin():
            nombre, datos = "fin", {}
        case EventoError(detalle=detalle):
            nombre, datos = "error", {"detalle": detalle}
    return f"event: {nombre}\ndata: {json.dumps(datos, ensure_ascii=False)}\n\n"
