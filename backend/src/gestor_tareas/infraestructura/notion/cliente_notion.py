"""Adaptador de ``FuenteNotion`` sobre la API REST de Notion (versión 2022-06-28).

Las páginas se listan con ``POST /v1/search`` (también las entradas de bases de
datos, que son páginas) y su texto se saca de ``GET /v1/blocks/{id}/children``,
bajando por los bloques con hijos. Ambas respuestas vienen paginadas con
``start_cursor``. Si Notion limita las peticiones (429) se espera lo que pide
``Retry-After`` y se reintenta unas pocas veces.

El token solo viaja en la cabecera ``Authorization``: nunca se incluye en los
mensajes de error ni en los registros.
"""

import time
from collections.abc import Callable, Iterator
from datetime import datetime
from typing import Any

import httpx

from gestor_tareas.dominio.conocimiento.entidades import PaginaNotion
from gestor_tareas.dominio.conocimiento.errores import NotionNoDisponibleError

VERSION_API = "2022-06-28"
_TAMANO_PAGINA = 100
_MAX_REINTENTOS = 3
_ESPERA_MAXIMA = 30.0
_TITULO_POR_DEFECTO = "Sin título"

# Bloques cuyo texto está en ``rich_text`` (el prefijo marca el tipo en el texto).
_PREFIJOS = {
    "paragraph": "",
    "heading_1": "",
    "heading_2": "",
    "heading_3": "",
    "quote": "",
    "callout": "",
    "toggle": "",
    "code": "",
    "bulleted_list_item": "- ",
    "numbered_list_item": "- ",
}
# Bloques con hijos que son páginas aparte (ya salen en la búsqueda): no se bajan.
_HIJOS_QUE_SON_PAGINAS = frozenset({"child_page", "child_database"})


def _texto_enriquecido(partes: list[dict[str, Any]]) -> str:
    return "".join(parte.get("plain_text", "") for parte in partes)


def _texto_del_bloque(bloque: dict[str, Any]) -> str:
    tipo = bloque.get("type", "")
    contenido = bloque.get(tipo) or {}
    if tipo in _PREFIJOS:
        texto = _texto_enriquecido(contenido.get("rich_text", []))
        return f"{_PREFIJOS[tipo]}{texto}" if texto.strip() else ""
    if tipo == "to_do":
        texto = _texto_enriquecido(contenido.get("rich_text", []))
        marca = "[x]" if contenido.get("checked") else "[ ]"
        return f"{marca} {texto}" if texto.strip() else ""
    if tipo == "table_row":
        return " | ".join(_texto_enriquecido(celda) for celda in contenido.get("cells", []))
    if tipo == "equation":
        return contenido.get("expression", "")
    # Imágenes, archivos, vídeos, enlaces, separadores...: no tienen texto útil.
    return ""


def _titulo(pagina: dict[str, Any]) -> str:
    for propiedad in pagina.get("properties", {}).values():
        if propiedad.get("type") == "title":
            titulo = _texto_enriquecido(propiedad.get("title", [])).strip()
            return titulo or _TITULO_POR_DEFECTO
    return _TITULO_POR_DEFECTO


class ClienteNotion:
    """Cliente de Notion con el token de una integración interna."""

    URL_BASE = "https://api.notion.com"

    def __init__(
        self,
        token: str,
        cliente_http: httpx.Client | None = None,
        esperar: Callable[[float], None] | None = None,
    ) -> None:
        self._http = cliente_http or httpx.Client(
            base_url=self.URL_BASE, timeout=httpx.Timeout(30.0, connect=10.0)
        )
        self._cabeceras = {
            "Authorization": f"Bearer {token}",
            "Notion-Version": VERSION_API,
        }
        self._esperar = esperar or time.sleep

    def cerrar(self) -> None:
        self._http.close()

    def listar_paginas(self) -> list[PaginaNotion]:
        paginas = []
        for pagina in self._recorrer("POST", "/v1/search"):
            if pagina.get("object") != "page" or pagina.get("archived") or pagina.get("in_trash"):
                continue
            paginas.append(
                PaginaNotion(
                    id=pagina["id"],
                    titulo=_titulo(pagina),
                    url=pagina.get("url", ""),
                    editada_en=datetime.fromisoformat(pagina["last_edited_time"]),
                )
            )
        return paginas

    def texto_de_pagina(self, pagina_id: str) -> str:
        return "\n".join(self._lineas_de_los_hijos(pagina_id))

    def _lineas_de_los_hijos(self, bloque_id: str) -> Iterator[str]:
        for bloque in self._recorrer("GET", f"/v1/blocks/{bloque_id}/children"):
            texto = _texto_del_bloque(bloque)
            if texto:
                yield texto
            if bloque.get("has_children") and bloque.get("type") not in _HIJOS_QUE_SON_PAGINAS:
                yield from self._lineas_de_los_hijos(bloque["id"])

    def _recorrer(self, metodo: str, ruta: str) -> Iterator[dict[str, Any]]:
        """Los resultados de todas las páginas de una lista paginada de Notion."""
        cursor: str | None = None
        while True:
            if metodo == "POST":
                cuerpo: dict[str, Any] = {
                    "filter": {"property": "object", "value": "page"},
                    "page_size": _TAMANO_PAGINA,
                }
                if cursor:
                    cuerpo["start_cursor"] = cursor
                datos = self._pedir(metodo, ruta, json=cuerpo)
            else:
                parametros: dict[str, Any] = {"page_size": _TAMANO_PAGINA}
                if cursor:
                    parametros["start_cursor"] = cursor
                datos = self._pedir(metodo, ruta, params=parametros)
            yield from datos.get("results", [])
            cursor = datos.get("next_cursor")
            if not datos.get("has_more") or not cursor:
                return

    def _pedir(self, metodo: str, ruta: str, **opciones: Any) -> dict[str, Any]:
        for intento in range(_MAX_REINTENTOS + 1):
            try:
                respuesta = self._http.request(metodo, ruta, headers=self._cabeceras, **opciones)
            except httpx.HTTPError as error:
                raise NotionNoDisponibleError("No se ha podido conectar con Notion.") from error
            if respuesta.status_code == 429:
                if intento == _MAX_REINTENTOS:
                    break
                self._esperar(_segundos_de_espera(respuesta))
                continue
            if respuesta.status_code == 401:
                raise NotionNoDisponibleError(
                    "Notion ha rechazado NOTION_TOKEN: revisa que sea el token de tu "
                    "integración interna."
                )
            if not respuesta.is_success:
                raise NotionNoDisponibleError(
                    f"Notion ha respondido con un error ({respuesta.status_code})."
                )
            return respuesta.json()
        raise NotionNoDisponibleError(
            "Notion ha recibido demasiadas peticiones; inténtalo de nuevo en un rato."
        )


def _segundos_de_espera(respuesta: httpx.Response) -> float:
    try:
        segundos = float(respuesta.headers.get("Retry-After", "1"))
    except ValueError:
        segundos = 1.0
    return min(max(segundos, 0.0), _ESPERA_MAXIMA)
