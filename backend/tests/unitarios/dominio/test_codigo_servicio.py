"""Reglas del nombre de un código de servicio (p. ej. «AXAS0024»): al menos 2
caracteres, como mucho 20 y sin espacios. El recorte de los extremos lo hace quien
recibe el texto (el esquema de la API) antes de validarlo."""

import pytest

from gestor_tareas.dominio.codigo_servicio.entidades import (
    LONGITUD_MAXIMA_CODIGO_SERVICIO,
    LONGITUD_MINIMA_CODIGO_SERVICIO,
    NombreCodigoServicioInvalidoError,
    validar_nombre_codigo_servicio,
)


def test_los_limites_son_2_y_20_caracteres() -> None:
    assert (LONGITUD_MINIMA_CODIGO_SERVICIO, LONGITUD_MAXIMA_CODIGO_SERVICIO) == (2, 20)


@pytest.mark.parametrize("nombre", ["AXAS0024", "24", "A" * 20, "axas-0025", "ÑU"])
def test_admite_los_nombres_validos_y_los_devuelve_tal_cual(nombre: str) -> None:
    assert validar_nombre_codigo_servicio(nombre) == nombre


@pytest.mark.parametrize("nombre", ["", "A"])
def test_rechaza_los_nombres_de_menos_de_2_caracteres(nombre: str) -> None:
    with pytest.raises(NombreCodigoServicioInvalidoError) as error:
        validar_nombre_codigo_servicio(nombre)

    assert str(error.value) == "El código de servicio debe tener al menos 2 caracteres."


def test_rechaza_los_nombres_de_mas_de_20_caracteres() -> None:
    with pytest.raises(NombreCodigoServicioInvalidoError) as error:
        validar_nombre_codigo_servicio("A" * 21)

    assert str(error.value) == "El código de servicio no puede superar los 20 caracteres."


@pytest.mark.parametrize("nombre", ["AX AS", "AX\tAS", "AX AS", "AX\nAS"])
def test_rechaza_los_nombres_con_espacios(nombre: str) -> None:
    with pytest.raises(NombreCodigoServicioInvalidoError) as error:
        validar_nombre_codigo_servicio(nombre)

    assert str(error.value) == "El código de servicio no puede contener espacios."


def test_el_error_es_un_value_error_para_que_lo_traduzca_la_validacion() -> None:
    assert issubclass(NombreCodigoServicioInvalidoError, ValueError)


@pytest.mark.parametrize("espacio", [" ", "　", "﻿", " "])
def test_los_espacios_son_los_de_json_schema(espacio: str) -> None:
    """Los mismos que `\\s` en el `pattern` que publica el contrato (ECMA-262)."""
    with pytest.raises(NombreCodigoServicioInvalidoError):
        validar_nombre_codigo_servicio(f"AX{espacio}AS")


@pytest.mark.parametrize("caracter", ["\x1c", "\x1e", "\x85"])
def test_los_caracteres_que_json_schema_no_considera_espacios_se_admiten(caracter: str) -> None:
    """Python los trata como espacios, pero `\\s` de JSON Schema no: si se
    rechazaran, el servidor rechazaría nombres que el contrato da por válidos."""
    assert validar_nombre_codigo_servicio(f"AX{caracter}AS") == f"AX{caracter}AS"
