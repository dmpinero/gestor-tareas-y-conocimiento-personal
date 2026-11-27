from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


@dataclass(frozen=True)
class PaginaNotion:
    """Una página (o entrada de una base de datos) compartida con la integración de
    Notion. ``editada_en`` es su ``last_edited_time``, en UTC."""

    id: str
    titulo: str
    url: str
    editada_en: datetime


@dataclass(frozen=True)
class FragmentoEncontrado:
    """Un trozo del texto de una página del índice, con los datos de su página.
    ``orden`` es su posición dentro de la página (0 el primero)."""

    pagina_id: str
    titulo: str
    url: str
    texto: str
    orden: int


@dataclass(frozen=True)
class EstadoDelIndice:
    """Cuántas páginas y trozos hay en el índice y cuándo terminó la última
    sincronización (``None`` si nunca)."""

    paginas: int
    fragmentos: int
    ultima_sincronizacion: datetime | None


@dataclass(frozen=True)
class ResumenSincronizacion:
    """Resultado de una sincronización: el índice tras ella y qué cambió."""

    paginas: int
    fragmentos: int
    nuevas: int
    actualizadas: int
    eliminadas: int
    ultima_sincronizacion: datetime


class Rol(StrEnum):
    """Quién escribió un mensaje de la conversación."""

    USUARIO = "usuario"
    ASISTENTE = "asistente"


@dataclass(frozen=True)
class MensajeChat:
    """Un mensaje de la conversación de Conocimiento."""

    rol: Rol
    texto: str


@dataclass(frozen=True)
class Fuente:
    """Una página citada en una respuesta."""

    pagina_id: str
    titulo: str
    url: str


@dataclass(frozen=True)
class EventoFuentes:
    """Primer evento de una respuesta: las páginas en las que se basa."""

    fuentes: list[Fuente]


@dataclass(frozen=True)
class EventoTexto:
    """Un trozo más del texto de la respuesta."""

    delta: str


@dataclass(frozen=True)
class EventoFin:
    """La respuesta ha terminado bien."""


@dataclass(frozen=True)
class EventoError:
    """La respuesta no se ha podido completar; ``detalle`` lo explica al usuario."""

    detalle: str


EventoRespuesta = EventoFuentes | EventoTexto | EventoFin | EventoError
