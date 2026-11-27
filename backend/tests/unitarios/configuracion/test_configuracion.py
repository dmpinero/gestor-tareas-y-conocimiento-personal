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


def test_sin_credenciales_de_conocimiento_no_hay_ni_token_de_notion_ni_clave_de_claude(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("NOTION_TOKEN", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    configuracion = Configuracion(_env_file=None)

    assert configuracion.notion_token is None
    assert configuracion.anthropic_api_key is None


def test_las_credenciales_de_conocimiento_se_leen_del_entorno_y_no_se_muestran(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("NOTION_TOKEN", "ntn_secreto")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-secreto")

    configuracion = Configuracion(_env_file=None)

    assert configuracion.notion_token.get_secret_value() == "ntn_secreto"
    assert configuracion.anthropic_api_key.get_secret_value() == "sk-ant-secreto"
    assert "secreto" not in repr(configuracion)
    assert "secreto" not in str(configuracion.model_dump())


def test_una_credencial_vacia_cuenta_como_sin_configurar(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NOTION_TOKEN", "  ")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "")

    configuracion = Configuracion(_env_file=None)

    assert configuracion.notion_token is None
    assert configuracion.anthropic_api_key is None
