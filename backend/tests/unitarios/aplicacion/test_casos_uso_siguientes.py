"""Casos de uso de la cola de siguientes tareas (S2-S4) y de las sugerencias elegidas
(S12): dos listas, y una entrada está como mucho en una de ellas. Subtareas en
Siguientes (S4): una entrada es una tarea entera o una subtarea suya."""

from datetime import UTC, datetime

import pytest

from gestor_tareas.aplicacion.foco.casos_uso import FijarFoco
from gestor_tareas.aplicacion.siguientes.casos_uso import (
    AnadirASiguientes,
    AnadirASugerencias,
    ListarSiguientes,
    ListarSugerencias,
    QuitarDeSiguientes,
    QuitarDeSugerencias,
    ReordenarSiguientes,
)
from gestor_tareas.dominio.excepciones import (
    ConflictoDeConcurrenciaError,
    EntidadNoEncontradaError,
)
from gestor_tareas.dominio.siguientes.entidades import ClaveDeEntrada, Lista, TareaSiguiente
from gestor_tareas.dominio.siguientes.reglas import (
    OrdenDeLaColaInvalidoError,
    SubtareaResueltaEnLaColaError,
    TareaCompletadaEnLaColaError,
)
from gestor_tareas.dominio.tarea.entidades import Subtarea, Tarea
from tests.unitarios.aplicacion.dobles import (
    RepositorioFocoFalso,
    RepositorioSiguientesFalso,
    RepositorioTareasFalso,
)

_FECHA = datetime(2026, 11, 10, 9, 0, 0)


def _repos(*nombres: str) -> tuple[RepositorioTareasFalso, RepositorioSiguientesFalso, list[int]]:
    tareas = RepositorioTareasFalso()
    ids = []
    for nombre in nombres:
        tarea = tareas.crear(
            Tarea(
                nombre=nombre,
                descripcion="d",
                fecha_creacion=_FECHA,
                subtareas=[Subtarea(nombre=f"Sub de {nombre}")],
            )
        )
        assert tarea.id is not None
        ids.append(tarea.id)
    return tareas, RepositorioSiguientesFalso(tareas), ids


def _claves(*ids: int) -> list[ClaveDeEntrada]:
    return [ClaveDeEntrada(i) for i in ids]


def _nombres(cola: list[TareaSiguiente]) -> list[str]:
    return [t.tarea_nombre for t in cola]


def test_la_cola_empieza_vacia() -> None:
    _, siguientes, _ = _repos("A")

    assert ListarSiguientes(siguientes).ejecutar() == []


def test_anadir_va_al_final_y_devuelve_la_cola_con_los_nombres() -> None:
    _, siguientes, (a, b) = _repos("A", "B")

    AnadirASiguientes(siguientes).ejecutar(b)
    cola = AnadirASiguientes(siguientes).ejecutar(a)

    assert cola == [TareaSiguiente(b, "B"), TareaSiguiente(a, "A")]
    assert ListarSiguientes(siguientes).ejecutar() == cola


def test_anadir_una_que_ya_esta_no_cambia_nada() -> None:
    _, siguientes, (a, b) = _repos("A", "B")
    AnadirASiguientes(siguientes).ejecutar(a)
    AnadirASiguientes(siguientes).ejecutar(b)

    assert _nombres(AnadirASiguientes(siguientes).ejecutar(a)) == ["A", "B"]


def test_anadir_una_tarea_que_no_existe_falla_sin_cambiar_la_cola() -> None:
    _, siguientes, (a,) = _repos("A")
    AnadirASiguientes(siguientes).ejecutar(a)

    with pytest.raises(EntidadNoEncontradaError):
        AnadirASiguientes(siguientes).ejecutar(999)
    assert _nombres(ListarSiguientes(siguientes).ejecutar()) == ["A"]


def test_anadir_una_tarea_completada_falla() -> None:
    tareas, siguientes, (a,) = _repos("A")
    tareas.cambiar_completada(a, True, datetime.now(UTC))

    with pytest.raises(TareaCompletadaEnLaColaError):
        AnadirASiguientes(siguientes).ejecutar(a)
    assert siguientes.ids == []


def test_las_completadas_no_se_ven_y_al_reabrirlas_vuelven_a_su_sitio() -> None:
    tareas, siguientes, (a, b, c) = _repos("A", "B", "C")
    for id_tarea in (a, b, c):
        AnadirASiguientes(siguientes).ejecutar(id_tarea)

    tareas.cambiar_completada(b, True, datetime.now(UTC))
    assert _nombres(ListarSiguientes(siguientes).ejecutar()) == ["A", "C"]

    tareas.cambiar_completada(b, False, datetime.now(UTC))
    assert _nombres(ListarSiguientes(siguientes).ejecutar()) == ["A", "B", "C"]


def test_reordenar_devuelve_la_cola_en_el_nuevo_orden() -> None:
    _, siguientes, (a, b, c) = _repos("A", "B", "C")
    for id_tarea in (a, b, c):
        AnadirASiguientes(siguientes).ejecutar(id_tarea)

    assert _nombres(ReordenarSiguientes(siguientes).ejecutar(_claves(c, a, b))) == ["C", "A", "B"]


def test_reordenar_con_ids_que_no_son_la_cola_falla_sin_cambiarla() -> None:
    _, siguientes, (a, b) = _repos("A", "B")
    AnadirASiguientes(siguientes).ejecutar(a)
    AnadirASiguientes(siguientes).ejecutar(b)

    with pytest.raises(OrdenDeLaColaInvalidoError):
        ReordenarSiguientes(siguientes).ejecutar(_claves(b))
    assert _nombres(ListarSiguientes(siguientes).ejecutar()) == ["A", "B"]


def test_quitar_saca_la_tarea_y_si_no_estaba_no_cambia_nada() -> None:
    _, siguientes, (a, b) = _repos("A", "B")
    AnadirASiguientes(siguientes).ejecutar(a)
    AnadirASiguientes(siguientes).ejecutar(b)

    assert _nombres(QuitarDeSiguientes(siguientes).ejecutar(a)) == ["B"]
    assert _nombres(QuitarDeSiguientes(siguientes).ejecutar(a)) == ["B"]


def test_fijar_el_foco_en_una_tarea_o_en_una_subtarea_suya_la_saca_de_la_cola() -> None:
    tareas, siguientes, (a, b, c) = _repos("A", "B", "C")
    for id_tarea in (a, b, c):
        AnadirASiguientes(siguientes).ejecutar(id_tarea)
    foco = RepositorioFocoFalso(tareas, siguientes)
    subtarea_de_c = tareas.obtener_por_id(c).subtareas[0].id  # type: ignore[union-attr]

    FijarFoco(foco, tareas).ejecutar(a, None)
    FijarFoco(foco, tareas).ejecutar(c, subtarea_de_c)

    assert _nombres(ListarSiguientes(siguientes).ejecutar()) == ["B"]


class _ConUnConflicto(RepositorioSiguientesFalso):
    """Choca una vez con otra petición simultánea en cada escritura."""

    def __init__(self, tareas: RepositorioTareasFalso) -> None:
        super().__init__(tareas)
        self.conflictos = 0

    def _chocar_la_primera_vez(self) -> None:
        self.conflictos += 1
        if self.conflictos % 2 == 1:
            raise ConflictoDeConcurrenciaError("choque")

    def anadir(self, id_tarea, lista=Lista.SIGUIENTES, id_subtarea=None) -> list[TareaSiguiente]:
        self._chocar_la_primera_vez()
        return super().anadir(id_tarea, lista, id_subtarea)

    def reordenar(self, claves, lista: Lista = Lista.SIGUIENTES) -> list[TareaSiguiente]:
        self._chocar_la_primera_vez()
        return super().reordenar(claves, lista)

    def quitar(self, id_tarea, lista=Lista.SIGUIENTES, id_subtarea=None) -> list[TareaSiguiente]:
        self._chocar_la_primera_vez()
        return super().quitar(id_tarea, lista, id_subtarea)


def test_las_escrituras_se_repiten_si_chocan_con_otra_peticion() -> None:
    tareas, _, (a, b) = _repos("A", "B")
    siguientes = _ConUnConflicto(tareas)

    AnadirASiguientes(siguientes).ejecutar(a)
    AnadirASiguientes(siguientes).ejecutar(b)
    assert _nombres(ReordenarSiguientes(siguientes).ejecutar(_claves(b, a))) == ["B", "A"]
    assert _nombres(QuitarDeSiguientes(siguientes).ejecutar(b)) == ["A"]
    assert siguientes.conflictos == 8


def test_las_escrituras_en_sugerencias_tambien_se_repiten_si_chocan() -> None:
    tareas, _, (a, b) = _repos("A", "B")
    siguientes = _ConUnConflicto(tareas)

    AnadirASugerencias(siguientes).ejecutar(a)
    assert _nombres(AnadirASugerencias(siguientes).ejecutar(b)) == ["A", "B"]
    assert _nombres(QuitarDeSugerencias(siguientes).ejecutar(a)) == ["B"]
    assert siguientes.conflictos == 6


# S12: sugerencias elegidas, una segunda lista con las mismas reglas.


def test_las_sugerencias_empiezan_vacias() -> None:
    _, siguientes, _ = _repos("A")

    assert ListarSugerencias(siguientes).ejecutar() == []


def test_anadir_a_sugerencias_va_al_final_y_no_toca_la_cola() -> None:
    _, siguientes, (a, b, c) = _repos("A", "B", "C")
    AnadirASiguientes(siguientes).ejecutar(c)

    AnadirASugerencias(siguientes).ejecutar(b)
    sugerencias = AnadirASugerencias(siguientes).ejecutar(a)

    assert sugerencias == [TareaSiguiente(b, "B"), TareaSiguiente(a, "A")]
    assert ListarSugerencias(siguientes).ejecutar() == sugerencias
    assert _nombres(ListarSiguientes(siguientes).ejecutar()) == ["C"]


def test_anadir_a_sugerencias_una_que_ya_esta_no_cambia_nada() -> None:
    _, siguientes, (a, b) = _repos("A", "B")
    AnadirASugerencias(siguientes).ejecutar(a)
    AnadirASugerencias(siguientes).ejecutar(b)

    assert _nombres(AnadirASugerencias(siguientes).ejecutar(a)) == ["A", "B"]


def test_anadir_a_sugerencias_una_de_la_cola_la_mueve_al_final() -> None:
    _, siguientes, (a, b, c) = _repos("A", "B", "C")
    AnadirASiguientes(siguientes).ejecutar(a)
    AnadirASiguientes(siguientes).ejecutar(b)
    AnadirASugerencias(siguientes).ejecutar(c)

    assert _nombres(AnadirASugerencias(siguientes).ejecutar(a)) == ["C", "A"]
    assert _nombres(ListarSiguientes(siguientes).ejecutar()) == ["B"]


def test_anadir_a_la_cola_una_de_sugerencias_la_mueve_al_final() -> None:
    _, siguientes, (a, b, c) = _repos("A", "B", "C")
    AnadirASugerencias(siguientes).ejecutar(a)
    AnadirASugerencias(siguientes).ejecutar(b)
    AnadirASiguientes(siguientes).ejecutar(c)

    assert _nombres(AnadirASiguientes(siguientes).ejecutar(a)) == ["C", "A"]
    assert _nombres(ListarSugerencias(siguientes).ejecutar()) == ["B"]


def test_anadir_a_sugerencias_una_que_no_existe_o_completada_falla_sin_cambiar_nada() -> None:
    tareas, siguientes, (a, b) = _repos("A", "B")
    AnadirASiguientes(siguientes).ejecutar(a)
    tareas.cambiar_completada(b, True, datetime.now(UTC))

    with pytest.raises(EntidadNoEncontradaError):
        AnadirASugerencias(siguientes).ejecutar(999)
    with pytest.raises(TareaCompletadaEnLaColaError):
        AnadirASugerencias(siguientes).ejecutar(b)
    assert ListarSugerencias(siguientes).ejecutar() == []
    assert _nombres(ListarSiguientes(siguientes).ejecutar()) == ["A"]


def test_las_completadas_no_se_ven_en_sugerencias_y_al_reabrirlas_vuelven() -> None:
    tareas, siguientes, (a, b, c) = _repos("A", "B", "C")
    for id_tarea in (a, b, c):
        AnadirASugerencias(siguientes).ejecutar(id_tarea)

    tareas.cambiar_completada(b, True, datetime.now(UTC))
    assert _nombres(ListarSugerencias(siguientes).ejecutar()) == ["A", "C"]

    tareas.cambiar_completada(b, False, datetime.now(UTC))
    assert _nombres(ListarSugerencias(siguientes).ejecutar()) == ["A", "B", "C"]


def test_quitar_de_una_lista_no_toca_la_otra() -> None:
    _, siguientes, (a, b) = _repos("A", "B")
    AnadirASiguientes(siguientes).ejecutar(a)
    AnadirASugerencias(siguientes).ejecutar(b)

    assert _nombres(QuitarDeSiguientes(siguientes).ejecutar(b)) == ["A"]
    assert _nombres(QuitarDeSugerencias(siguientes).ejecutar(a)) == ["B"]
    assert _nombres(ListarSugerencias(siguientes).ejecutar()) == ["B"]

    assert _nombres(QuitarDeSugerencias(siguientes).ejecutar(b)) == []
    assert _nombres(QuitarDeSugerencias(siguientes).ejecutar(b)) == []
    assert _nombres(ListarSiguientes(siguientes).ejecutar()) == ["A"]


def test_reordenar_la_cola_no_admite_las_de_sugerencias() -> None:
    _, siguientes, (a, b) = _repos("A", "B")
    AnadirASiguientes(siguientes).ejecutar(a)
    AnadirASugerencias(siguientes).ejecutar(b)

    with pytest.raises(OrdenDeLaColaInvalidoError):
        ReordenarSiguientes(siguientes).ejecutar(_claves(b, a))
    assert _nombres(ReordenarSiguientes(siguientes).ejecutar(_claves(a))) == ["A"]
    assert _nombres(ListarSugerencias(siguientes).ejecutar()) == ["B"]


def test_fijar_el_foco_saca_la_tarea_de_cualquiera_de_las_dos_listas() -> None:
    tareas, siguientes, (a, b, c) = _repos("A", "B", "C")
    AnadirASiguientes(siguientes).ejecutar(a)
    AnadirASugerencias(siguientes).ejecutar(b)
    AnadirASugerencias(siguientes).ejecutar(c)
    foco = RepositorioFocoFalso(tareas, siguientes)
    subtarea_de_c = tareas.obtener_por_id(c).subtareas[0].id  # type: ignore[union-attr]

    FijarFoco(foco, tareas).ejecutar(b, None)
    FijarFoco(foco, tareas).ejecutar(c, subtarea_de_c)

    assert _nombres(ListarSiguientes(siguientes).ejecutar()) == ["A"]
    assert ListarSugerencias(siguientes).ejecutar() == []


# Subtareas en Siguientes (S4): una entrada es una tarea entera o una subtarea suya.


def _sub(tareas: RepositorioTareasFalso, id_tarea: int) -> int:
    tarea = tareas.obtener_por_id(id_tarea)
    assert tarea is not None and tarea.subtareas[0].id is not None
    return tarea.subtareas[0].id


def test_anadir_una_subtarea_a_cada_lista_con_los_nombres() -> None:
    tareas, siguientes, (a, b) = _repos("A", "B")
    sa, sb = _sub(tareas, a), _sub(tareas, b)

    cola = AnadirASiguientes(siguientes).ejecutar(a, sa)
    sugerencias = AnadirASugerencias(siguientes).ejecutar(b, sb)

    assert cola == [TareaSiguiente(a, "A", sa, "Sub de A")]
    assert sugerencias == [TareaSiguiente(b, "B", sb, "Sub de B")]


def test_anadir_una_subtarea_que_no_es_de_la_tarea_falla_sin_cambiar_nada() -> None:
    tareas, siguientes, (a, b) = _repos("A", "B")

    with pytest.raises(EntidadNoEncontradaError, match="subtarea"):
        AnadirASiguientes(siguientes).ejecutar(a, _sub(tareas, b))
    with pytest.raises(EntidadNoEncontradaError, match="subtarea"):
        AnadirASugerencias(siguientes).ejecutar(a, 999)
    assert siguientes.listas == {lista: [] for lista in Lista}


def test_anadir_una_subtarea_resuelta_o_de_una_tarea_completada_falla() -> None:
    tareas, siguientes, (a, b) = _repos("A", "B")
    tareas.cambiar_resuelta_subtarea(a, _sub(tareas, a), True)
    tareas.cambiar_completada(b, True, datetime.now(UTC))

    with pytest.raises(SubtareaResueltaEnLaColaError):
        AnadirASiguientes(siguientes).ejecutar(a, _sub(tareas, a))
    with pytest.raises(TareaCompletadaEnLaColaError):
        AnadirASugerencias(siguientes).ejecutar(b, _sub(tareas, b))
    assert siguientes.listas == {lista: [] for lista in Lista}


def test_una_tarea_y_su_subtarea_son_entradas_distintas_y_cada_una_esta_una_vez() -> None:
    tareas, siguientes, (a,) = _repos("A")
    sa = _sub(tareas, a)

    AnadirASiguientes(siguientes).ejecutar(a)
    AnadirASiguientes(siguientes).ejecutar(a, sa)
    cola = AnadirASiguientes(siguientes).ejecutar(a, sa)

    assert cola == [TareaSiguiente(a, "A"), TareaSiguiente(a, "A", sa, "Sub de A")]


def test_anadir_una_subtarea_a_la_otra_lista_la_mueve_y_deja_su_tarea() -> None:
    tareas, siguientes, (a,) = _repos("A")
    sa = _sub(tareas, a)
    AnadirASiguientes(siguientes).ejecutar(a)
    AnadirASiguientes(siguientes).ejecutar(a, sa)

    sugerencias = AnadirASugerencias(siguientes).ejecutar(a, sa)

    assert sugerencias == [TareaSiguiente(a, "A", sa, "Sub de A")]
    assert ListarSiguientes(siguientes).ejecutar() == [TareaSiguiente(a, "A")]


def test_reordenar_con_una_tarea_y_su_subtarea() -> None:
    tareas, siguientes, (a, b) = _repos("A", "B")
    sa = _sub(tareas, a)
    for id_tarea, id_subtarea in ((a, None), (b, None), (a, sa)):
        AnadirASiguientes(siguientes).ejecutar(id_tarea, id_subtarea)

    cola = ReordenarSiguientes(siguientes).ejecutar(
        [ClaveDeEntrada(a, sa), ClaveDeEntrada(b), ClaveDeEntrada(a)]
    )

    assert [(t.tarea_id, t.subtarea_id) for t in cola] == [(a, sa), (b, None), (a, None)]
    with pytest.raises(OrdenDeLaColaInvalidoError):
        ReordenarSiguientes(siguientes).ejecutar(_claves(a, b))


def test_quitar_con_o_sin_subtarea_saca_solo_esa_entrada() -> None:
    tareas, siguientes, (a,) = _repos("A")
    sa = _sub(tareas, a)
    AnadirASugerencias(siguientes).ejecutar(a)
    AnadirASugerencias(siguientes).ejecutar(a, sa)

    assert QuitarDeSugerencias(siguientes).ejecutar(a) == [TareaSiguiente(a, "A", sa, "Sub de A")]
    assert QuitarDeSugerencias(siguientes).ejecutar(a) == [TareaSiguiente(a, "A", sa, "Sub de A")]
    assert QuitarDeSugerencias(siguientes).ejecutar(a, sa) == []


def test_las_subtareas_resueltas_o_de_tareas_completadas_no_se_ven_y_vuelven() -> None:
    tareas, siguientes, (a, b) = _repos("A", "B")
    sa, sb = _sub(tareas, a), _sub(tareas, b)
    for id_tarea, id_subtarea in ((a, sa), (b, sb), (b, None)):
        AnadirASiguientes(siguientes).ejecutar(id_tarea, id_subtarea)

    tareas.cambiar_resuelta_subtarea(a, sa, True)
    tareas.cambiar_completada(b, True, datetime.now(UTC))
    assert ListarSiguientes(siguientes).ejecutar() == []

    tareas.cambiar_resuelta_subtarea(a, sa, False)
    tareas.cambiar_completada(b, False, datetime.now(UTC))
    assert [(t.tarea_id, t.subtarea_id) for t in ListarSiguientes(siguientes).ejecutar()] == [
        (a, sa),
        (b, sb),
        (b, None),
    ]


def test_borrar_una_subtarea_quita_su_entrada() -> None:
    tareas, siguientes, (a,) = _repos("A")
    sa = _sub(tareas, a)
    AnadirASiguientes(siguientes).ejecutar(a)
    AnadirASiguientes(siguientes).ejecutar(a, sa)

    tareas.eliminar_subtarea(a, sa)

    assert ListarSiguientes(siguientes).ejecutar() == [TareaSiguiente(a, "A")]


def test_foco_en_una_subtarea_quita_su_entrada_y_la_de_su_tarea() -> None:
    tareas, siguientes, (a, b) = _repos("A", "B")
    sa, sb = _sub(tareas, a), _sub(tareas, b)
    AnadirASiguientes(siguientes).ejecutar(a)
    AnadirASugerencias(siguientes).ejecutar(a, sa)
    AnadirASiguientes(siguientes).ejecutar(b, sb)
    foco = RepositorioFocoFalso(tareas, siguientes)

    FijarFoco(foco, tareas).ejecutar(a, sa)

    assert ListarSiguientes(siguientes).ejecutar() == [TareaSiguiente(b, "B", sb, "Sub de B")]
    assert ListarSugerencias(siguientes).ejecutar() == []


def test_foco_en_una_tarea_entera_quita_solo_su_entrada() -> None:
    tareas, siguientes, (a,) = _repos("A")
    sa = _sub(tareas, a)
    AnadirASiguientes(siguientes).ejecutar(a)
    AnadirASiguientes(siguientes).ejecutar(a, sa)
    foco = RepositorioFocoFalso(tareas, siguientes)

    FijarFoco(foco, tareas).ejecutar(a, None)

    assert ListarSiguientes(siguientes).ejecutar() == [TareaSiguiente(a, "A", sa, "Sub de A")]
