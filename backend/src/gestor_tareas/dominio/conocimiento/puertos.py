from collections.abc import Iterator, Sequence
from datetime import datetime, timedelta
from typing import Protocol

from gestor_tareas.dominio.conocimiento.entidades import (
    EstadoDelIndice,
    FragmentoEncontrado,
    MensajeChat,
    PaginaNotion,
)


class FuenteNotion(Protocol):
    """Puerto de lectura de Notion. Los dos métodos lanzan
    ``NotionNoDisponibleError`` si Notion falla."""

    def listar_paginas(self) -> list[PaginaNotion]:
        """Todas las páginas (y entradas de bases de datos) compartidas con la
        integración, sin las archivadas ni las de la papelera."""
        ...

    def texto_de_pagina(self, pagina_id: str) -> str:
        """El texto de los bloques de la página, en orden, un bloque por línea
        (sin imágenes ni archivos, y sin las subpáginas, que son páginas aparte)."""
        ...


class ModeloLenguaje(Protocol):
    """Puerto del modelo de lenguaje que redacta las respuestas."""

    def responder(self, sistema: str, mensajes: Sequence[MensajeChat]) -> Iterator[str]:
        """Genera la respuesta a ``mensajes`` (el último, del usuario) siguiendo las
        instrucciones ``sistema``, en trozos según llegan.

        Mientras se itera puede lanzar ``RespuestaRechazadaError`` si el modelo se
        niega a responder y ``ModeloNoDisponibleError`` si no puede hacerlo."""
        ...


class RepositorioConocimiento(Protocol):
    """Puerto de persistencia del índice local de Notion. Las operaciones que
    escriben confirman."""

    def ediciones(self) -> dict[str, datetime]:
        """El ``editada_en`` de cada página del índice, por su id."""
        ...

    def guardar_pagina(self, pagina: PaginaNotion, fragmentos: Sequence[str]) -> None:
        """Crea o sustituye la página con sus trozos (en ese orden)."""
        ...

    def eliminar_paginas(self, ids: Sequence[str]) -> None:
        """Quita del índice esas páginas y sus trozos (las que no estén, se ignoran)."""
        ...

    def buscar(self, consulta: str, limite: int) -> list[FragmentoEncontrado]:
        """Los ``limite`` trozos más relevantes para ``consulta`` (búsqueda de texto
        completo), del más al menos relevante; ninguno si nada coincide."""
        ...

    def estado(self) -> EstadoDelIndice:
        """Páginas y trozos del índice y la última sincronización terminada."""
        ...

    def empezar_sincronizacion(self, ahora: datetime, caducidad: timedelta) -> bool:
        """Marca que empieza una sincronización y devuelve ``True``; si ya hay otra
        en curso desde hace menos de ``caducidad``, no cambia nada y devuelve
        ``False``. (Una marcada hace más se da por abandonada.)"""
        ...

    def terminar_sincronizacion(self, terminada_en: datetime | None) -> None:
        """Quita la marca de sincronización en curso; si ``terminada_en`` no es
        ``None``, la guarda como última sincronización."""
        ...
