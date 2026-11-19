import json
from pathlib import Path

import pytest

from gestor_tareas.aplicacion.oportunidad.puertos import ConfiguracionAltaInvalidaError
from gestor_tareas.dominio.oportunidad.entidades import Asignacion
from gestor_tareas.infraestructura.automatizacion.configuracion_json import (
    LectorConfiguracionJson,
)

EJEMPLO = Path(__file__).parents[4] / "config" / "alta_oportunidad.ejemplo.json"


def _escribir(directorio: Path, datos: object) -> Path:
    ruta = directorio / "alta_oportunidad.json"
    ruta.write_text(json.dumps(datos), encoding="utf-8")
    return ruta


def test_el_ejemplo_del_repositorio_es_una_configuracion_valida() -> None:
    configuracion = LectorConfiguracionJson(EJEMPLO).cargar()

    assert configuracion.url_digital_desktop.endswith(".invalid/")
    assert configuracion.perfil == "Persona Ejemplo"
    assert configuracion.dias_fecha_limite == 7
    assert configuracion.lineas_negocio == (Asignacion("Línea Ejemplo", "100"),)


def test_sin_archivo_explica_como_crearlo(tmp_path: Path) -> None:
    ruta = tmp_path / "no-existe.json"

    with pytest.raises(ConfiguracionAltaInvalidaError) as error:
        LectorConfiguracionJson(ruta).cargar()

    assert str(error.value) == (
        f"No existe el archivo de configuración {ruta}. Créalo a partir de "
        "config/alta_oportunidad.ejemplo.json (consulta el README)."
    )


def test_un_json_mal_formado_se_rechaza(tmp_path: Path) -> None:
    ruta = tmp_path / "alta_oportunidad.json"
    ruta.write_text("{ no es json", encoding="utf-8")

    with pytest.raises(ConfiguracionAltaInvalidaError) as error:
        LectorConfiguracionJson(ruta).cargar()

    assert str(error.value).startswith(f"No se pudo leer el archivo de configuración {ruta}:")


def test_un_campo_que_falta_se_nombra_en_el_error(tmp_path: Path) -> None:
    datos = json.loads(EJEMPLO.read_text(encoding="utf-8"))
    del datos["perfil"]
    datos["comunidades"] = []

    with pytest.raises(ConfiguracionAltaInvalidaError) as error:
        LectorConfiguracionJson(_escribir(tmp_path, datos)).cargar()

    mensaje = str(error.value)
    assert "falta el campo 'perfil'" in mensaje
    assert "el campo 'comunidades' no es válido" in mensaje
