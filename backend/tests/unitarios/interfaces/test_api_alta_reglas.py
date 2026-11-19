"""Regresión de las reglas del alta a través de la API (pruebas del verificador, T2):
mensaje del código PRJ, fechas, configuración ausente o inválida y cantidades no finitas.
"""

import json
import shutil
from pathlib import Path

import pytest

from gestor_tareas.infraestructura.automatizacion.configuracion_json import (
    LectorConfiguracionJson,
)
from tests.unitarios.interfaces.alta_oportunidades_dobles import RUTA, montar_cliente

MENSAJE_PRJ = "El código debe tener el formato PRJ-XXXXX (5 dígitos)."
EJEMPLO = Path(__file__).parents[4] / "config" / "alta_oportunidad.ejemplo.json"


def _lector_del_ejemplo(directorio: Path) -> LectorConfiguracionJson:
    ruta = directorio / "alta_oportunidad.json"
    shutil.copyfile(EJEMPLO, ruta)
    return LectorConfiguracionJson(ruta)


def test_un_prj_invalido_da_422_con_el_mensaje_exacto(tmp_path: Path) -> None:
    cliente, navegadores, _ = montar_cliente(fuente=_lector_del_ejemplo(tmp_path))
    with cliente:
        respuesta = cliente.post(
            f"{RUTA}/ejecucion", json={"prj": "PRJ-1", "duracion": 1, "importe": 1, "coste": 1}
        )

        assert respuesta.status_code == 422
        assert respuesta.json() == {"detalle": MENSAJE_PRJ}
        assert navegadores == []


def test_el_resumen_del_ejemplo_calcula_las_fechas_y_no_expone_las_urls(tmp_path: Path) -> None:
    cliente, _, _ = montar_cliente(fuente=_lector_del_ejemplo(tmp_path))
    with cliente:
        resumen = cliente.get(f"{RUTA}/configuracion").json()

        assert resumen["fecha_limite"] == "07/02/2026"
        assert resumen["fecha_inicio"] == "28/02/2026"
        assert "url" not in json.dumps(resumen["valores"]).lower()


@pytest.mark.parametrize("contenido", [None, "", "{", "[]", '{"url_notion": "x"}'])
def test_sin_configuracion_valida_no_se_lanza_ningun_alta(
    tmp_path: Path, contenido: str | None
) -> None:
    ruta = tmp_path / "alta_oportunidad.json"
    if contenido is not None:
        ruta.write_text(contenido, encoding="utf-8")
    cliente, navegadores, _ = montar_cliente(fuente=LectorConfiguracionJson(ruta))
    with cliente:
        resumen = cliente.get(f"{RUTA}/configuracion")
        lanzada = cliente.post(
            f"{RUTA}/ejecucion", json={"prj": "PRJ-00001", "duracion": 1, "importe": 1, "coste": 1}
        )

        assert resumen.status_code == 200
        assert resumen.json()["error"]
        assert resumen.json()["valores"] is None
        assert lanzada.status_code == 503
        assert lanzada.json()["detalle"].startswith("No se puede lanzar el alta:")
        assert cliente.get(f"{RUTA}/ejecucion").status_code == 404
        assert navegadores == []


@pytest.mark.parametrize(
    "cuerpo",
    [
        {"prj": "PRJ-00001", "duracion": 0, "importe": 1, "coste": 1},
        {"prj": "PRJ-00001", "duracion": 1, "importe": -1, "coste": 1},
        {"prj": "PRJ-00001", "duracion": 1, "importe": "NaN", "coste": 1},
        {"prj": "PRJ-00001", "duracion": 1, "importe": "Infinity", "coste": 1},
        {"prj": "PRJ-00001", "duracion": 1, "importe": 1, "coste": "-Infinity"},
        {"prj": "PRJ-00001", "duracion": 1, "importe": 1},
    ],
)
def test_cantidades_invalidas_o_no_finitas_dan_422_sin_lanzar(tmp_path: Path, cuerpo: dict) -> None:
    cliente, navegadores, _ = montar_cliente(fuente=_lector_del_ejemplo(tmp_path))
    with cliente:
        respuesta = cliente.post(f"{RUTA}/ejecucion", json=cuerpo)

        assert respuesta.status_code == 422, respuesta.text
        assert cliente.get(f"{RUTA}/ejecucion").status_code == 404
        assert navegadores == []


def test_el_resumen_trae_el_nombre_del_menu_de_la_configuracion(tmp_path: Path) -> None:
    cliente, _, _ = montar_cliente(fuente=_lector_del_ejemplo(tmp_path))
    with cliente:
        resumen = cliente.get(f"{RUTA}/configuracion").json()

        assert resumen["nombre_menu"] == "Oportunidades Ejemplo"


def test_sin_nombre_del_menu_en_la_configuracion_se_usa_el_predeterminado(
    tmp_path: Path,
) -> None:
    datos = json.loads(EJEMPLO.read_text(encoding="utf-8"))
    del datos["nombre_menu"]
    ruta = tmp_path / "alta_oportunidad.json"
    ruta.write_text(json.dumps(datos), encoding="utf-8")
    cliente, _, _ = montar_cliente(fuente=LectorConfiguracionJson(ruta))
    with cliente:
        resumen = cliente.get(f"{RUTA}/configuracion").json()

        assert resumen["error"] is None
        assert resumen["nombre_menu"] == "Alta de oportunidades"


def test_con_la_configuracion_invalida_el_menu_usa_el_nombre_predeterminado(
    tmp_path: Path,
) -> None:
    cliente, _, _ = montar_cliente(fuente=LectorConfiguracionJson(tmp_path / "no-existe.json"))
    with cliente:
        resumen = cliente.get(f"{RUTA}/configuracion").json()

        assert resumen["valores"] is None
        assert resumen["nombre_menu"] == "Alta de oportunidades"
