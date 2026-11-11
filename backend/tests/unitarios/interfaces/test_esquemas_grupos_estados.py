import pytest
from pydantic import ValidationError

from gestor_tareas.interfaces.api.v1.esquemas.grupo_estados import (
    EstadoGrupoEsquema,
    GrupoEstadosEsquema,
    OrdenEstadosEsquema,
    TareaEstadoEsquema,
)
from gestor_tareas.interfaces.api.v1.esquemas.tarea import TareaCrearEsquema

_TAREA = {"nombre": "T", "descripcion": "d", "fecha_creacion": "2026-11-11T10:00:00"}


@pytest.mark.parametrize("esquema", [GrupoEstadosEsquema, EstadoGrupoEsquema])
def test_el_nombre_se_guarda_sin_los_espacios_de_los_extremos(esquema) -> None:
    assert esquema(nombre="  En curso  ").nombre == "En curso"


@pytest.mark.parametrize("esquema", [GrupoEstadosEsquema, EstadoGrupoEsquema])
@pytest.mark.parametrize("nombre", ["", "   ", " ", "　﻿", "n" * 51, 5, None])
def test_se_rechaza_un_nombre_vacio_largo_o_que_no_es_texto(esquema, nombre) -> None:
    with pytest.raises(ValidationError):
        esquema(nombre=nombre)


@pytest.mark.parametrize("esquema", [GrupoEstadosEsquema, EstadoGrupoEsquema])
def test_se_admite_un_nombre_de_50_caracteres(esquema) -> None:
    assert esquema(nombre="n" * 50).nombre == "n" * 50


@pytest.mark.parametrize("esquema", [GrupoEstadosEsquema, EstadoGrupoEsquema])
def test_el_contrato_publica_los_limites_del_nombre(esquema) -> None:
    propiedad = esquema.model_json_schema()["properties"]["nombre"]
    assert (propiedad["minLength"], propiedad["maxLength"], propiedad["pattern"]) == (1, 50, r"\S")


def test_el_orden_admite_enteros_y_enteros_con_decimal_cero() -> None:
    assert OrdenEstadosEsquema(ids=[3, 1.0, 2]).ids == [3, 1, 2]


@pytest.mark.parametrize("ids", [[1, 1], ["1"], [True], [1.5], None])
def test_el_orden_rechaza_repetidos_y_no_enteros(ids) -> None:
    with pytest.raises(ValidationError):
        OrdenEstadosEsquema(ids=ids)


def test_el_cambio_de_estado_admite_un_id_entero() -> None:
    assert TareaEstadoEsquema(estado_id=4).estado_id == 4
    assert TareaEstadoEsquema(estado_id=4.0).estado_id == 4


@pytest.mark.parametrize("valor", ["4", True, 4.5, None])
def test_el_cambio_de_estado_rechaza_lo_que_no_es_un_id_entero(valor) -> None:
    with pytest.raises(ValidationError):
        TareaEstadoEsquema(estado_id=valor)


def test_el_cambio_de_estado_exige_el_estado() -> None:
    with pytest.raises(ValidationError):
        TareaEstadoEsquema()


def test_el_grupo_de_la_tarea_es_opcional_y_por_defecto_null() -> None:
    assert TareaCrearEsquema(**_TAREA).grupo_estados_id is None
    assert TareaCrearEsquema(**_TAREA, grupo_estados_id=None).grupo_estados_id is None
    assert TareaCrearEsquema(**_TAREA, grupo_estados_id=7).grupo_estados_id == 7


@pytest.mark.parametrize("valor", ["7", True, 7.5])
def test_el_grupo_de_la_tarea_debe_ser_un_id_entero(valor) -> None:
    with pytest.raises(ValidationError):
        TareaCrearEsquema(**_TAREA, grupo_estados_id=valor)
