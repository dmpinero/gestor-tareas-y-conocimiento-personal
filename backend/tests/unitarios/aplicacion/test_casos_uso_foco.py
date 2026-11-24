from datetime import UTC, datetime, timedelta, timezone

import pytest

from gestor_tareas.aplicacion.foco.casos_uso import FijarFoco, ObtenerFoco, QuitarFoco
from gestor_tareas.dominio.excepciones import EntidadNoEncontradaError
from gestor_tareas.dominio.foco.entidades import Foco
from gestor_tareas.dominio.tarea.entidades import Subtarea, Tarea
from tests.unitarios.aplicacion.dobles import RepositorioFocoFalso, RepositorioTareasFalso

_FECHA = datetime(2026, 11, 10, 9, 0, 0)
_AHORA = datetime(2026, 11, 24, 10, 30, 15, 123456, tzinfo=UTC)


def _repos() -> tuple[RepositorioTareasFalso, RepositorioFocoFalso, int, int]:
    tareas = RepositorioTareasFalso()
    tarea = tareas.crear(
        Tarea(
            nombre="Migración portal",
            descripcion="d",
            fecha_creacion=_FECHA,
            subtareas=[Subtarea(nombre="Copiar la base de datos")],
        )
    )
    assert tarea.id is not None and tarea.subtareas[0].id is not None
    return tareas, RepositorioFocoFalso(tareas), tarea.id, tarea.subtareas[0].id


def _fijar(tareas: RepositorioTareasFalso, foco: RepositorioFocoFalso) -> FijarFoco:
    return FijarFoco(foco, tareas, reloj=lambda: _AHORA)


def test_obtener_sin_foco_devuelve_none() -> None:
    _, foco, _, _ = _repos()

    assert ObtenerFoco(foco).ejecutar() is None


def test_fijar_una_tarea_guarda_el_instante_en_utc_sin_fraccion_de_segundo() -> None:
    tareas, foco, id_tarea, _ = _repos()

    resultado = _fijar(tareas, foco).ejecutar(id_tarea, None)

    assert resultado == Foco(
        tarea_id=id_tarea,
        tarea_nombre="Migración portal",
        subtarea_id=None,
        subtarea_nombre=None,
        desde=datetime(2026, 11, 24, 10, 30, 15, tzinfo=UTC),
    )
    assert ObtenerFoco(foco).ejecutar() == resultado


def test_fijar_con_un_reloj_en_otra_zona_lo_pasa_a_utc() -> None:
    tareas, foco, id_tarea, _ = _repos()
    madrid = timezone(timedelta(hours=1))

    resultado = FijarFoco(
        foco, tareas, reloj=lambda: datetime(2026, 11, 24, 11, 0, 0, tzinfo=madrid)
    ).ejecutar(id_tarea, None)

    assert resultado.desde == datetime(2026, 11, 24, 10, 0, 0, tzinfo=UTC)


def test_fijar_una_subtarea_de_la_tarea() -> None:
    tareas, foco, id_tarea, id_subtarea = _repos()

    resultado = _fijar(tareas, foco).ejecutar(id_tarea, id_subtarea)

    assert resultado.subtarea_id == id_subtarea
    assert resultado.subtarea_nombre == "Copiar la base de datos"


def test_fijar_una_tarea_que_no_existe_lanza_no_encontrada_y_no_fija() -> None:
    tareas, foco, id_tarea, _ = _repos()

    with pytest.raises(
        EntidadNoEncontradaError, match=f"^No existe la tarea con id {id_tarea + 9}$"
    ):
        _fijar(tareas, foco).ejecutar(id_tarea + 9, None)

    assert foco.veces_fijado == 0


def test_fijar_una_subtarea_que_no_es_de_la_tarea_lanza_no_encontrada_y_no_fija() -> None:
    tareas, foco, id_tarea, _ = _repos()
    otra = tareas.crear(
        Tarea(
            nombre="Otra",
            descripcion="d",
            fecha_creacion=_FECHA,
            subtareas=[Subtarea(nombre="Ajena")],
        )
    )
    ajena = otra.subtareas[0].id

    with pytest.raises(
        EntidadNoEncontradaError,
        match=f"^No existe la subtarea con id {ajena} en la tarea con id {id_tarea}$",
    ):
        _fijar(tareas, foco).ejecutar(id_tarea, ajena)

    assert foco.veces_fijado == 0


def test_quitar_deja_sin_foco_y_se_puede_repetir() -> None:
    tareas, foco, id_tarea, _ = _repos()
    _fijar(tareas, foco).ejecutar(id_tarea, None)

    QuitarFoco(foco).ejecutar()
    QuitarFoco(foco).ejecutar()

    assert ObtenerFoco(foco).ejecutar() is None
