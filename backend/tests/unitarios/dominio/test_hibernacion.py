"""Hibernación de una tarea: hibernar la marca desde un instante y reanudarla corre su
vencimiento exactamente lo que ha estado hibernada."""

from datetime import UTC, datetime

import pytest

from gestor_tareas.dominio.tarea.entidades import Tarea
from gestor_tareas.dominio.tarea.hibernacion import EstadoDeHibernacionInvalidoError

_HIBERNADA = datetime(2026, 11, 20, 8, 0, 0, tzinfo=UTC)
_REANUDADA = datetime(2026, 11, 22, 10, 30, 15, tzinfo=UTC)


def _tarea(fecha_vencimiento: datetime | None = datetime(2026, 12, 1, 10)) -> Tarea:
    return Tarea(
        id=7,
        nombre="Migración portal",
        descripcion="d",
        fecha_creacion=datetime(2026, 11, 10, 9),
        fecha_vencimiento=fecha_vencimiento,
    )


def test_hibernar_guarda_el_instante_sin_tocar_el_vencimiento_ni_la_congelacion() -> None:
    tarea = _tarea()

    tarea.hibernar(_HIBERNADA)

    assert tarea.hibernada_desde == _HIBERNADA
    assert tarea.fecha_vencimiento == datetime(2026, 12, 1, 10)
    assert tarea.congelada_en is None


def test_hibernar_una_tarea_ya_hibernada_falla_sin_cambiarla() -> None:
    tarea = _tarea()
    tarea.hibernar(_HIBERNADA)

    with pytest.raises(EstadoDeHibernacionInvalidoError, match="La tarea con id 7 ya está"):
        tarea.hibernar(_REANUDADA)
    assert tarea.hibernada_desde == _HIBERNADA


def test_reanudar_corre_el_vencimiento_el_tiempo_hibernado() -> None:
    tarea = _tarea()
    tarea.hibernar(_HIBERNADA)

    tarea.reanudar(_REANUDADA)

    # 2 días, 2 horas, 30 minutos y 15 segundos hibernada.
    assert tarea.fecha_vencimiento == datetime(2026, 12, 3, 12, 30, 15)
    assert tarea.hibernada_desde is None


def test_reanudar_sin_vencimiento_solo_quita_la_hibernacion() -> None:
    tarea = _tarea(fecha_vencimiento=None)
    tarea.hibernar(_HIBERNADA)

    tarea.reanudar(_REANUDADA)

    assert tarea.fecha_vencimiento is None
    assert tarea.hibernada_desde is None


def test_reanudar_una_tarea_no_hibernada_falla_sin_cambiarla() -> None:
    tarea = _tarea()

    with pytest.raises(EstadoDeHibernacionInvalidoError, match="La tarea con id 7 no está"):
        tarea.reanudar(_REANUDADA)
    assert tarea.fecha_vencimiento == datetime(2026, 12, 1, 10)
