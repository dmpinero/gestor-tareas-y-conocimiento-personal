"""Dobles de los puertos de Conocimiento: Notion, el modelo de lenguaje y el índice,
en memoria. Ninguno sale a la red."""

import re
from collections.abc import Iterator, Sequence
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from gestor_tareas.dominio.conocimiento.entidades import (
    EstadoDelIndice,
    FragmentoEncontrado,
    MensajeChat,
    PaginaNotion,
)
from gestor_tareas.dominio.conocimiento.errores import NotionNoDisponibleError


@dataclass
class FuenteNotionFalsa:
    """Notion con ``paginas`` y el texto de cada una en ``textos``. Si ``falla_al_listar``
    o el id está en ``fallan``, lanza ``NotionNoDisponibleError``."""

    paginas: list[PaginaNotion] = field(default_factory=list)
    textos: dict[str, str] = field(default_factory=dict)
    falla_al_listar: bool = False
    fallan: set[str] = field(default_factory=set)
    textos_pedidos: list[str] = field(default_factory=list)

    def listar_paginas(self) -> list[PaginaNotion]:
        if self.falla_al_listar:
            raise NotionNoDisponibleError("Notion ha respondido con un error (500).")
        return list(self.paginas)

    def texto_de_pagina(self, pagina_id: str) -> str:
        self.textos_pedidos.append(pagina_id)
        if pagina_id in self.fallan:
            raise NotionNoDisponibleError("Notion ha respondido con un error (500).")
        return self.textos.get(pagina_id, "")


@dataclass
class ModeloLenguajeFalso:
    """Responde con ``trozos`` y, si hay ``error``, lo lanza después de ellos."""

    trozos: list[str] = field(default_factory=lambda: ["Respuesta ", "falsa."])
    error: Exception | None = None
    llamadas: list[tuple[str, list[MensajeChat]]] = field(default_factory=list)

    def responder(self, sistema: str, mensajes: Sequence[MensajeChat]) -> Iterator[str]:
        self.llamadas.append((sistema, list(mensajes)))
        yield from self.trozos
        if self.error is not None:
            raise self.error


def _palabras(texto: str) -> set[str]:
    return {p for p in re.findall(r"\w+", texto.lower()) if len(p) >= 3}


@dataclass
class _PaginaGuardada:
    pagina: PaginaNotion
    fragmentos: list[str]


@dataclass
class RepositorioConocimientoEnMemoria:
    """Índice en memoria; ``buscar`` puntúa por palabras en común (de 3 letras o más)."""

    paginas: dict[str, _PaginaGuardada] = field(default_factory=dict)
    ultima_sincronizacion: datetime | None = None
    en_curso_desde: datetime | None = None
    busquedas: list[str] = field(default_factory=list)

    def ediciones(self) -> dict[str, datetime]:
        return {i: g.pagina.editada_en for i, g in self.paginas.items()}

    def guardar_pagina(self, pagina: PaginaNotion, fragmentos: Sequence[str]) -> None:
        self.paginas[pagina.id] = _PaginaGuardada(pagina, list(fragmentos))

    def eliminar_paginas(self, ids: Sequence[str]) -> None:
        for i in ids:
            self.paginas.pop(i, None)

    def buscar(self, consulta: str, limite: int) -> list[FragmentoEncontrado]:
        self.busquedas.append(consulta)
        buscadas = _palabras(consulta)
        puntuados = []
        for guardada in self.paginas.values():
            for orden, texto in enumerate(guardada.fragmentos):
                comunes = len(buscadas & _palabras(texto))
                if comunes:
                    p = guardada.pagina
                    encontrado = FragmentoEncontrado(p.id, p.titulo, p.url, texto, orden)
                    puntuados.append((comunes, encontrado))
        puntuados.sort(key=lambda par: -par[0])
        return [f for _, f in puntuados[:limite]]

    def estado(self) -> EstadoDelIndice:
        return EstadoDelIndice(
            paginas=len(self.paginas),
            fragmentos=sum(len(g.fragmentos) for g in self.paginas.values()),
            ultima_sincronizacion=self.ultima_sincronizacion,
        )

    def empezar_sincronizacion(self, ahora: datetime, caducidad: timedelta) -> bool:
        if self.en_curso_desde is not None and self.en_curso_desde > ahora - caducidad:
            return False
        self.en_curso_desde = ahora
        return True

    def terminar_sincronizacion(self, terminada_en: datetime | None) -> None:
        self.en_curso_desde = None
        if terminada_en is not None:
            self.ultima_sincronizacion = terminada_en
