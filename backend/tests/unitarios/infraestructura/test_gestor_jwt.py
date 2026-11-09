import pytest

from gestor_tareas.infraestructura.seguridad.gestor_jwt import (
    TokenInvalidoError,
    crear_token_acceso,
    decodificar_token_acceso,
)


def test_un_token_creado_se_decodifica_con_los_mismos_datos() -> None:
    token = crear_token_acceso({"sub": "usuario-1"})

    payload = decodificar_token_acceso(token)

    assert payload["sub"] == "usuario-1"


def test_un_token_manipulado_lanza_error() -> None:
    token_invalido = crear_token_acceso({"sub": "usuario-1"}) + "manipulado"

    with pytest.raises(TokenInvalidoError):
        decodificar_token_acceso(token_invalido)
