"""Bloque opcional ``axas_ms3`` de la configuración local del alta."""

import json
from pathlib import Path

import pytest

from gestor_tareas.aplicacion.oportunidad.puertos import ConfiguracionAltaInvalidaError
from gestor_tareas.dominio.oportunidad.entidades import Asignacion
from gestor_tareas.infraestructura.automatizacion.configuracion_json import (
    LectorConfiguracionJson,
)

EJEMPLO = Path(__file__).parents[4] / "config" / "alta_oportunidad.ejemplo.json"


def _ejemplo() -> dict:
    return json.loads(EJEMPLO.read_text(encoding="utf-8"))


def _cargar(directorio: Path, datos: object):
    ruta = directorio / "alta_oportunidad.json"
    ruta.write_text(json.dumps(datos), encoding="utf-8")
    return LectorConfiguracionJson(ruta).cargar()


def test_el_ejemplo_trae_un_bloque_axas_ms3_valido() -> None:
    bloque = LectorConfiguracionJson(EJEMPLO).cargar().axas_ms3

    assert bloque is not None
    assert bloque.nombre_menu == "Oportunidades AXAS MS3"
    assert bloque.perfil == "Persona Ms3 Ejemplo"
    assert bloque.cliente == "[CMS] Cliente Ms3 Ejemplo S.A."
    assert bloque.area_ms3 == "Desarrollo"
    assert bloque.dias_fecha_limite == 7
    assert bloque.lineas_negocio == (Asignacion("Línea Ms3 Ejemplo", "100"),)
    assert bloque.comunidades == (
        Asignacion("Comunidad Ms3 A", "80"),
        Asignacion("Comunidad Ms3 B", "20"),
    )


def test_un_archivo_solo_con_anes_sigue_cargando_igual(tmp_path: Path) -> None:
    datos = _ejemplo()
    del datos["axas_ms3"]

    sin_bloque = _cargar(tmp_path, datos)
    con_bloque = LectorConfiguracionJson(EJEMPLO).cargar()

    assert sin_bloque.axas_ms3 is None
    # Los valores de ANES no cambian por tener (o no) el bloque AXAS MS3.
    assert {**vars(sin_bloque), "axas_ms3": None} == {**vars(con_bloque), "axas_ms3": None}
    assert sin_bloque.perfil == "Persona Ejemplo"
    assert sin_bloque.nombre_menu == "Oportunidades Ejemplo"


def test_las_busquedas_opcionales_y_el_nombre_del_menu_tienen_valor_por_defecto(
    tmp_path: Path,
) -> None:
    datos = _ejemplo()
    for clave in ("responsable_busqueda", "responsable_tecnico_busqueda", "nombre_menu"):
        datos["axas_ms3"].pop(clave, None)

    bloque = _cargar(tmp_path, datos).axas_ms3

    assert bloque is not None
    assert bloque.responsable_busqueda is None
    assert bloque.responsable_tecnico_busqueda is None
    assert bloque.nombre_menu == "Oportunidades AXAS MS3"


def test_un_campo_del_bloque_que_falta_o_sobra_se_nombra_en_el_error(tmp_path: Path) -> None:
    datos = _ejemplo()
    del datos["axas_ms3"]["perfil"]
    datos["axas_ms3"]["inventado"] = "x"

    with pytest.raises(ConfiguracionAltaInvalidaError) as error:
        _cargar(tmp_path, datos)

    mensaje = str(error.value)
    assert "falta el campo 'axas_ms3.perfil'" in mensaje
    assert "el campo 'axas_ms3.inventado' no se reconoce" in mensaje
