from datetime import datetime

import pytest

from gestor_tareas.aplicacion import reintentos
from gestor_tareas.aplicacion.reintentos import reintentar_si_hay_conflicto
from gestor_tareas.aplicacion.tarea.crear_tarea import CrearTarea
from gestor_tareas.dominio.excepciones import ConflictoDeConcurrenciaError
from tests.unitarios.aplicacion.dobles import (
    RepositorioEtiquetasFalso,
    RepositorioPersonasFalso,
    RepositorioTareasFalso,
)


@pytest.fixture(autouse=True)
def sin_esperas(monkeypatch) -> list[float]:
    esperas: list[float] = []
    monkeypatch.setattr(reintentos.time, "sleep", esperas.append)
    return esperas


class _FallaVeces:
    def __init__(self, veces: int) -> None:
        self.llamadas = 0
        self._veces = veces

    def __call__(self) -> str:
        self.llamadas += 1
        if self.llamadas <= self._veces:
            raise ConflictoDeConcurrenciaError("choque")
        return "hecho"


def test_devuelve_el_resultado_sin_reintentar_si_no_hay_conflicto(sin_esperas) -> None:
    operacion = _FallaVeces(0)

    assert reintentar_si_hay_conflicto(operacion) == "hecho"
    assert operacion.llamadas == 1
    assert sin_esperas == []


def test_repite_la_operacion_entera_tras_un_conflicto(sin_esperas) -> None:
    operacion = _FallaVeces(2)

    assert reintentar_si_hay_conflicto(operacion, intentos=3) == "hecho"
    assert operacion.llamadas == 3
    assert len(sin_esperas) == 2
    assert all(0 < espera < 1 for espera in sin_esperas)


def test_propaga_el_conflicto_al_agotar_los_intentos() -> None:
    operacion = _FallaVeces(5)

    with pytest.raises(ConflictoDeConcurrenciaError):
        reintentar_si_hay_conflicto(operacion, intentos=3)
    assert operacion.llamadas == 3


def test_no_reintenta_otros_errores() -> None:
    def falla() -> None:
        raise ValueError("otro")

    with pytest.raises(ValueError, match="otro"):
        reintentar_si_hay_conflicto(falla)


def test_rechaza_menos_de_un_intento() -> None:
    with pytest.raises(ValueError, match="al menos 1"):
        reintentar_si_hay_conflicto(lambda: None, intentos=0)


class _RepositorioTareasQueChocaUnaVez(RepositorioTareasFalso):
    def __init__(self) -> None:
        super().__init__()
        self.intentos = 0

    def crear(self, tarea):
        self.intentos += 1
        if self.intentos == 1:
            raise ConflictoDeConcurrenciaError("choque")
        return super().crear(tarea)


def test_crear_tarea_repite_el_alta_completa_si_choca_con_otra_peticion() -> None:
    tareas = _RepositorioTareasQueChocaUnaVez()

    tarea = CrearTarea(tareas, RepositorioEtiquetasFalso(), RepositorioPersonasFalso()).ejecutar(
        nombre="Uno",
        descripcion="d",
        fecha_creacion=datetime(2026, 11, 9, 10, 0, 0),
        etiquetas=["casa"],
    )

    assert tareas.intentos == 2
    assert (tarea.id, tarea.etiquetas) == (1, ["casa"])
