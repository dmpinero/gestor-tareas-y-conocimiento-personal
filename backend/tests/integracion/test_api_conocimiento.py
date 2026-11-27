"""API de Conocimiento sobre la base de datos real, con Notion y Claude simulados
(nunca sale a la red)."""

import json
from collections.abc import Iterator
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from gestor_tareas.dominio.conocimiento.entidades import PaginaNotion
from gestor_tareas.interfaces.api.v1.enrutadores.conocimiento import (
    obtener_fuente_notion,
    obtener_modelo_lenguaje,
)
from gestor_tareas.main import crear_aplicacion
from tests.unitarios.aplicacion.dobles_conocimiento import FuenteNotionFalsa, ModeloLenguajeFalso

_RUTA = "/api/v1/conocimiento"


def _pagina(id_: str, titulo: str, dia: int) -> PaginaNotion:
    return PaginaNotion(id_, titulo, f"https://n.so/{id_}", datetime(2026, 11, dia, tzinfo=UTC))


@pytest.fixture
def entorno(sesion_bd: Session) -> Iterator[tuple[TestClient, FuenteNotionFalsa]]:
    fuente = FuenteNotionFalsa(
        paginas=[_pagina("receta", "Receta de paella", 20), _pagina("reunion", "Reunión", 21)],
        textos={"receta": "La paella lleva arroz bomba y azafrán.", "reunion": "Hablar con Ana."},
    )
    aplicacion = crear_aplicacion()
    aplicacion.dependency_overrides[obtener_fuente_notion] = lambda: fuente
    aplicacion.dependency_overrides[obtener_modelo_lenguaje] = lambda: ModeloLenguajeFalso(
        trozos=["Arroz ", "[Receta de paella]."]
    )
    with TestClient(aplicacion) as cliente:
        yield cliente, fuente


def _eventos(cuerpo: str) -> list[tuple[str, object]]:
    eventos = []
    for bloque in filter(str.strip, cuerpo.split("\n\n")):
        lineas = dict(linea.split(": ", 1) for linea in bloque.split("\n"))
        eventos.append((lineas["event"], json.loads(lineas["data"])))
    return eventos


def test_sincroniza_de_forma_incremental_y_responde_con_las_notas_guardadas(entorno) -> None:
    cliente, fuente = entorno

    assert cliente.get(f"{_RUTA}/estado").json()["paginas"] == 0
    primera = cliente.post(f"{_RUTA}/sincronizar").json()
    assert (primera["nuevas"], primera["actualizadas"], primera["eliminadas"]) == (2, 0, 0)

    fuente.paginas = [_pagina("receta", "Receta de paella", 25)]
    fuente.textos["receta"] = "La paella lleva arroz bomba, azafrán y gambas."
    fuente.textos_pedidos.clear()
    segunda = cliente.post(f"{_RUTA}/sincronizar").json()

    assert (segunda["nuevas"], segunda["actualizadas"], segunda["eliminadas"]) == (0, 1, 1)
    assert (segunda["paginas"], segunda["fragmentos"]) == (1, 1)
    assert fuente.textos_pedidos == ["receta"]
    estado = cliente.get(f"{_RUTA}/estado").json()
    assert estado["paginas"] == 1
    assert estado["ultima_sincronizacion"] == segunda["ultima_sincronizacion"]

    respuesta = cliente.post(
        f"{_RUTA}/preguntar",
        json={"mensajes": [{"rol": "usuario", "texto": "¿Lleva gambas la paella?"}]},
    )

    assert _eventos(respuesta.text) == [
        (
            "fuentes",
            [{"pagina_id": "receta", "titulo": "Receta de paella", "url": "https://n.so/receta"}],
        ),
        ("texto", {"delta": "Arroz "}),
        ("texto", {"delta": "[Receta de paella]."}),
        ("fin", {}),
    ]


def test_si_notion_falla_responde_502_y_se_puede_volver_a_sincronizar(entorno) -> None:
    cliente, fuente = entorno
    fuente.falla_al_listar = True

    assert cliente.post(f"{_RUTA}/sincronizar").status_code == 502

    fuente.falla_al_listar = False
    assert cliente.post(f"{_RUTA}/sincronizar").status_code == 200


def test_busca_sin_ia_en_lo_sincronizado_con_el_texto_completo_de_mysql(entorno) -> None:
    cliente, _ = entorno

    # Nunca sincronizado: no hay nada que encontrar.
    assert cliente.get(f"{_RUTA}/buscar", params={"q": "paella"}).json() == []

    cliente.post(f"{_RUTA}/sincronizar")
    # Sin distinguir tildes ni mayúsculas, y los signos sueltos no rompen la consulta.
    respuesta = cliente.get(f"{_RUTA}/buscar", params={"q": "AZAFRAN *", "limite": 5})

    assert respuesta.status_code == 200
    assert respuesta.json() == [
        {
            "pagina_id": "receta",
            "titulo": "Receta de paella",
            "url": "https://n.so/receta",
            "fragmento": "Receta de paella\nLa paella lleva arroz bomba y azafrán.",
            "orden": 0,
        }
    ]
    assert cliente.get(f"{_RUTA}/buscar", params={"q": "dentista"}).json() == []
    assert cliente.get(f"{_RUTA}/buscar", params={"q": "   "}).status_code == 422


def test_busca_sin_ia_sin_credenciales_en_lo_ya_sincronizado(entorno, sesion_bd) -> None:
    cliente, _ = entorno
    cliente.post(f"{_RUTA}/sincronizar")
    aplicacion = crear_aplicacion()
    aplicacion.dependency_overrides[obtener_fuente_notion] = lambda: None
    aplicacion.dependency_overrides[obtener_modelo_lenguaje] = lambda: None

    with TestClient(aplicacion) as sin_credenciales:
        respuesta = sin_credenciales.get(f"{_RUTA}/buscar", params={"q": "Ana"})

    assert respuesta.status_code == 200
    assert [r["pagina_id"] for r in respuesta.json()] == ["reunion"]
