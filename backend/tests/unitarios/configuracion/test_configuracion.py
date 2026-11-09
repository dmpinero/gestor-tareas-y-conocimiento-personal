import pytest

from gestor_tareas.configuracion import Configuracion, obtener_configuracion


def test_sin_variables_de_entorno_apunta_a_la_base_de_datos_del_proyecto(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("URL_BASE_DATOS", raising=False)

    configuracion = Configuracion(_env_file=None)

    assert configuracion.url_base_datos == (
        "mysql+pymysql://gestor:gestor@localhost:3306/gestor_tareas?charset=utf8mb4"
    )
    assert configuracion.entorno == "desarrollo"
    assert configuracion.sentry_dsn is None
    assert configuracion.otel_endpoint_exportador is None


def test_las_variables_de_entorno_sobrescriben_los_valores_por_defecto(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ENTORNO", "produccion")
    monkeypatch.setenv("MINUTOS_EXPIRACION_TOKEN", "15")

    configuracion = Configuracion(_env_file=None)

    assert configuracion.entorno == "produccion"
    assert configuracion.minutos_expiracion_token == 15


def test_no_existe_configuracion_de_adjuntos() -> None:
    assert "ruta_adjuntos" not in Configuracion.model_fields


def test_obtener_configuracion_devuelve_siempre_la_misma_instancia() -> None:
    assert obtener_configuracion() is obtener_configuracion()
