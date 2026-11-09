import pytest
from pydantic import ValidationError

from gestor_tareas.interfaces.api.v1.esquemas.tarea import TareaCrearEsquema, TareaSalidaEsquema


def _datos(**cambios) -> dict:
    datos = {"nombre": "Tarea", "prioridad": 3, "descripcion": "Descripción"}
    datos.update(cambios)
    return datos


def test_acepta_nombre_de_200_caracteres() -> None:
    assert TareaCrearEsquema(**_datos(nombre="n" * 200)).nombre == "n" * 200


def test_rechaza_nombre_de_201_caracteres() -> None:
    with pytest.raises(ValidationError):
        TareaCrearEsquema(**_datos(nombre="n" * 201))


@pytest.mark.parametrize("nombre", ["", "   "])
def test_rechaza_nombre_vacio_o_solo_espacios(nombre: str) -> None:
    with pytest.raises(ValidationError):
        TareaCrearEsquema(**_datos(nombre=nombre))


def test_nombre_es_obligatorio() -> None:
    datos = _datos()
    del datos["nombre"]
    with pytest.raises(ValidationError):
        TareaCrearEsquema(**datos)


def test_recorta_espacios_de_nombre_y_descripcion() -> None:
    esquema = TareaCrearEsquema(**_datos(nombre="  Tarea  ", descripcion="  Texto  "))

    assert esquema.nombre == "Tarea"
    assert esquema.descripcion == "Texto"


def test_acepta_descripcion_de_500_caracteres() -> None:
    assert TareaCrearEsquema(**_datos(descripcion="d" * 500)).descripcion == "d" * 500


def test_rechaza_descripcion_de_501_caracteres() -> None:
    with pytest.raises(ValidationError):
        TareaCrearEsquema(**_datos(descripcion="d" * 501))


@pytest.mark.parametrize("descripcion", ["", "   "])
def test_rechaza_descripcion_vacia_o_solo_espacios(descripcion: str) -> None:
    with pytest.raises(ValidationError):
        TareaCrearEsquema(**_datos(descripcion=descripcion))


def test_descripcion_es_obligatoria() -> None:
    datos = _datos()
    del datos["descripcion"]
    with pytest.raises(ValidationError):
        TareaCrearEsquema(**datos)


@pytest.mark.parametrize("prioridad", [1, 5])
def test_acepta_prioridad_en_los_limites(prioridad: int) -> None:
    assert TareaCrearEsquema(**_datos(prioridad=prioridad)).prioridad == prioridad


@pytest.mark.parametrize("prioridad", [0, 6])
def test_rechaza_prioridad_fuera_de_rango(prioridad: int) -> None:
    with pytest.raises(ValidationError):
        TareaCrearEsquema(**_datos(prioridad=prioridad))


def test_prioridad_es_opcional() -> None:
    datos = _datos()
    del datos["prioridad"]

    assert TareaCrearEsquema(**datos).prioridad is None
    assert TareaCrearEsquema(**_datos(prioridad=None)).prioridad is None


def test_salida_expone_exactamente_los_campos_del_contrato() -> None:
    salida = TareaSalidaEsquema(id=1, nombre="Tarea", prioridad=None, descripcion="Texto")

    assert salida.model_dump() == {
        "id": 1,
        "nombre": "Tarea",
        "prioridad": None,
        "descripcion": "Texto",
    }
