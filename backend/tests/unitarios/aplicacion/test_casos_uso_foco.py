from datetime import UTC, datetime, timedelta, timezone

import pytest

from gestor_tareas.aplicacion.foco.casos_uso import (
    FijarFoco,
    ListarHistorialFoco,
    ObtenerFoco,
    QuitarFoco,
)
from gestor_tareas.aplicacion.tarea.eliminar_subtarea import EliminarSubtarea
from gestor_tareas.aplicacion.tarea.eliminar_tarea import EliminarTarea
from gestor_tareas.dominio.excepciones import EntidadNoEncontradaError, FiltroDeListadoInvalidoError
from gestor_tareas.dominio.foco.entidades import Foco, PeriodoDeFoco
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

    QuitarFoco(foco, reloj=lambda: _AHORA).ejecutar()
    QuitarFoco(foco, reloj=lambda: _AHORA).ejecutar()

    assert ObtenerFoco(foco).ejecutar() is None


_DESPUES = datetime(2026, 11, 24, 11, 45, 0, 999, tzinfo=UTC)
_DESPUES_SIN_FRACCION = datetime(2026, 11, 24, 11, 45, 0, tzinfo=UTC)
_DESDE = datetime(2026, 11, 24, 10, 30, 15, tzinfo=UTC)


def _periodo(id_tarea: int, hasta: datetime | None, **cambios) -> PeriodoDeFoco:
    valores = {
        "id": 1,
        "tarea_id": id_tarea,
        "tarea_nombre": "Migración portal",
        "subtarea_id": None,
        "subtarea_nombre": None,
        "desde": _DESDE,
        "hasta": hasta,
    }
    return PeriodoDeFoco(**{**valores, **cambios})


def test_fijar_abre_un_periodo_en_curso_en_el_historial() -> None:
    tareas, foco, id_tarea, _ = _repos()

    _fijar(tareas, foco).ejecutar(id_tarea, None)

    assert foco.historial == [_periodo(id_tarea, None)]


def test_fijar_otra_cierra_el_periodo_anterior_al_mismo_instante() -> None:
    tareas, foco, id_tarea, id_subtarea = _repos()
    _fijar(tareas, foco).ejecutar(id_tarea, None)

    FijarFoco(foco, tareas, reloj=lambda: _DESPUES).ejecutar(id_tarea, id_subtarea)

    assert foco.historial == [
        _periodo(id_tarea, _DESPUES_SIN_FRACCION),
        _periodo(
            id_tarea,
            None,
            id=2,
            subtarea_id=id_subtarea,
            subtarea_nombre="Copiar la base de datos",
            desde=_DESPUES_SIN_FRACCION,
        ),
    ]


def test_un_fijar_rechazado_no_toca_el_historial() -> None:
    tareas, foco, id_tarea, _ = _repos()
    _fijar(tareas, foco).ejecutar(id_tarea, None)

    with pytest.raises(EntidadNoEncontradaError):
        _fijar(tareas, foco).ejecutar(id_tarea + 9, None)

    assert foco.historial == [_periodo(id_tarea, None)]


def test_quitar_cierra_el_periodo_en_curso_ahora() -> None:
    tareas, foco, id_tarea, _ = _repos()
    _fijar(tareas, foco).ejecutar(id_tarea, None)

    QuitarFoco(foco, reloj=lambda: _DESPUES).ejecutar()

    assert foco.historial == [_periodo(id_tarea, _DESPUES_SIN_FRACCION)]


def test_quitar_sin_foco_no_anade_nada_al_historial() -> None:
    _, foco, _, _ = _repos()

    QuitarFoco(foco, reloj=lambda: _DESPUES).ejecutar()

    assert foco.historial == []


def test_borrar_la_tarea_en_foco_cierra_su_periodo() -> None:
    tareas, foco, id_tarea, id_subtarea = _repos()
    _fijar(tareas, foco).ejecutar(id_tarea, id_subtarea)

    EliminarTarea(tareas, foco, reloj=lambda: _DESPUES).ejecutar(id_tarea)

    assert foco.historial[0].hasta == _DESPUES_SIN_FRACCION
    assert tareas.obtener_por_id(id_tarea) is None


def test_borrar_otra_tarea_no_toca_el_historial() -> None:
    tareas, foco, id_tarea, _ = _repos()
    otra = tareas.crear(Tarea(nombre="Otra", descripcion="d", fecha_creacion=_FECHA))
    assert otra.id is not None
    _fijar(tareas, foco).ejecutar(id_tarea, None)

    EliminarTarea(tareas, foco, reloj=lambda: _DESPUES).ejecutar(otra.id)

    assert foco.historial == [_periodo(id_tarea, None)]


def test_borrar_una_tarea_que_no_existe_sigue_lanzando_no_encontrada() -> None:
    tareas, foco, id_tarea, _ = _repos()
    _fijar(tareas, foco).ejecutar(id_tarea, None)

    with pytest.raises(
        EntidadNoEncontradaError, match=f"^No existe la tarea con id {id_tarea + 9}$"
    ):
        EliminarTarea(tareas, foco).ejecutar(id_tarea + 9)

    assert foco.historial == [_periodo(id_tarea, None)]


def test_borrar_la_subtarea_en_foco_cierra_su_periodo() -> None:
    tareas, foco, id_tarea, id_subtarea = _repos()
    _fijar(tareas, foco).ejecutar(id_tarea, id_subtarea)

    tarea = EliminarSubtarea(tareas, foco, reloj=lambda: _DESPUES).ejecutar(id_tarea, id_subtarea)

    assert tarea.subtareas == []
    assert foco.historial[0].hasta == _DESPUES_SIN_FRACCION


def test_borrar_una_subtarea_con_el_foco_en_la_tarea_no_toca_el_historial() -> None:
    tareas, foco, id_tarea, id_subtarea = _repos()
    _fijar(tareas, foco).ejecutar(id_tarea, None)

    EliminarSubtarea(tareas, foco, reloj=lambda: _DESPUES).ejecutar(id_tarea, id_subtarea)

    assert foco.historial == [_periodo(id_tarea, None)]


def test_listar_el_historial_pasa_los_limites_a_utc() -> None:
    tareas, foco, id_tarea, _ = _repos()
    _fijar(tareas, foco).ejecutar(id_tarea, None)
    madrid = timezone(timedelta(hours=1))

    periodos = ListarHistorialFoco(foco).ejecutar(
        datetime(2026, 11, 24, 0, 0, 0, tzinfo=madrid),
        datetime(2026, 11, 25, 0, 0, 0, tzinfo=madrid),
    )

    assert periodos == [_periodo(id_tarea, None)]
    assert foco.consultas_historial == [
        (datetime(2026, 11, 23, 23, 0, 0, tzinfo=UTC), datetime(2026, 11, 24, 23, 0, 0, tzinfo=UTC))
    ]
    assert all(limite.tzinfo is UTC for limite in foco.consultas_historial[0])


def test_listar_el_historial_sin_limites() -> None:
    _, foco, _, _ = _repos()

    assert ListarHistorialFoco(foco).ejecutar(None, None) == []
    assert foco.consultas_historial == [(None, None)]


@pytest.mark.parametrize("hasta", [_DESDE, _DESDE - timedelta(seconds=1)])
def test_listar_el_historial_con_desde_no_anterior_a_hasta_lanza_filtro_invalido(
    hasta: datetime,
) -> None:
    _, foco, _, _ = _repos()

    with pytest.raises(FiltroDeListadoInvalidoError, match="^desde debe ser anterior a hasta$"):
        ListarHistorialFoco(foco).ejecutar(_DESDE, hasta)

    assert foco.consultas_historial == []
