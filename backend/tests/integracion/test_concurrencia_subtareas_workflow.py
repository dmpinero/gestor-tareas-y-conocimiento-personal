"""Altas de oportunidades simultáneas con reordenaciones del workflow.

Cada hilo simula una petición: su propia sesión y su propia transacción, con los
casos de uso y los repositorios reales sobre MySQL. Las subtareas que recibe cada
oportunidad deben seguir uno de los órdenes completos del workflow, nunca uno a
medias.
"""

import random
import threading
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

import pytest

from gestor_tareas.aplicacion.tarea.crear_tarea import CrearTarea
from gestor_tareas.aplicacion.workflow_oportunidades.anadir_paso import AnadirPaso
from gestor_tareas.aplicacion.workflow_oportunidades.reordenar_pasos import ReordenarPasos
from gestor_tareas.dominio.tarea.entidades import Oportunidad, Tarea, TipoTarea
from gestor_tareas.infraestructura.persistencia.repositorios.repositorio_tareas_sqlalchemy import (
    RepositorioTareasSqlAlchemy,
)
from gestor_tareas.infraestructura.persistencia.repositorios.repositorio_workflow_oportunidades_sqlalchemy import (  # noqa: E501
    RepositorioWorkflowOportunidadesSqlAlchemy,
)
from gestor_tareas.infraestructura.persistencia.repositorios.repositorios_catalogos_sqlalchemy import (  # noqa: E501
    RepositorioEtiquetasSqlAlchemy,
    RepositorioPersonasSqlAlchemy,
)
from gestor_tareas.infraestructura.persistencia.sesion import FabricaSesiones

_PASOS = 6
_ALTAS = 6
_REORDENACIONES = 4
_RONDAS = 4


def _crear_oportunidad(i: int) -> Tarea:
    sesion = FabricaSesiones()
    try:
        return CrearTarea(
            RepositorioTareasSqlAlchemy(sesion),
            RepositorioEtiquetasSqlAlchemy(sesion),
            RepositorioPersonasSqlAlchemy(sesion),
            RepositorioWorkflowOportunidadesSqlAlchemy(sesion),
        ).ejecutar(
            nombre=f"Oportunidad {i}",
            descripcion="d",
            fecha_creacion=datetime(2026, 11, 10, 9, 0, 0),
            etiquetas=[f"etiqueta {i % 2}"],
            tipo=TipoTarea.OPORTUNIDAD,
            oportunidad=Oportunidad(codigo=f"OP-{i}"),
        )
    finally:
        sesion.close()


def _reordenar(ids: list[int]) -> list[str]:
    sesion = FabricaSesiones()
    try:
        pasos = ReordenarPasos(RepositorioWorkflowOportunidadesSqlAlchemy(sesion)).ejecutar(ids)
        return [p.nombre for p in pasos]
    finally:
        sesion.close()


def _guardada(id_tarea: int) -> Tarea:
    sesion = FabricaSesiones()
    try:
        return RepositorioTareasSqlAlchemy(sesion).obtener_por_id(id_tarea)
    finally:
        sesion.close()


def _a_la_vez(operaciones: list[Callable[[], object]]) -> list[object]:
    barrera = threading.Barrier(len(operaciones))

    def tras_la_barrera(operacion: Callable[[], object]) -> object:
        barrera.wait()
        return operacion()

    with ThreadPoolExecutor(max_workers=len(operaciones)) as ejecutor:
        futuros = [ejecutor.submit(tras_la_barrera, op) for op in operaciones]
        return [futuro.result() for futuro in futuros]


@pytest.mark.usefixtures("sesion_bd")
@pytest.mark.parametrize("ronda", range(_RONDAS))
def test_las_altas_crean_las_subtareas_en_un_orden_completo_aunque_se_reordene_a_la_vez(
    ronda,
) -> None:
    sesion = FabricaSesiones()
    try:
        workflow = RepositorioWorkflowOportunidadesSqlAlchemy(sesion)
        iniciales = [AnadirPaso(workflow).ejecutar(f"Paso {i}") for i in range(_PASOS)]
    finally:
        sesion.close()
    por_id = {p.id: p.nombre for p in iniciales}
    ordenes = [list(por_id)]
    for semilla in range(_REORDENACIONES):
        orden = list(por_id)
        random.Random(ronda * 100 + semilla).shuffle(orden)
        ordenes.append(orden)
    nombres_validos = [[por_id[i] for i in orden] for orden in ordenes]

    operaciones: list[Callable[[], object]] = [
        *[lambda i=i: _crear_oportunidad(i) for i in range(_ALTAS)],
        *[lambda o=o: _reordenar(o) for o in ordenes[1:]],
    ]
    resultados = _a_la_vez(operaciones)

    tareas = [r for r in resultados if isinstance(r, Tarea)]
    assert len(tareas) == _ALTAS
    for tarea in tareas:
        assert [s.nombre for s in tarea.subtareas] in nombres_validos
        assert not any(s.resuelta for s in tarea.subtareas)
        assert all(s.asignado is None and s.prioridad is None for s in tarea.subtareas)
        ids = [s.id for s in tarea.subtareas]
        assert ids == sorted(ids)
        assert _guardada(tarea.id).subtareas == tarea.subtareas


@pytest.mark.usefixtures("sesion_bd")
def test_una_reordenacion_espera_a_que_termine_la_copia_en_curso() -> None:
    """Mientras una transacción ha leído el workflow para copiarlo, una reordenación
    no puede confirmarse: espera a que esa transacción termine."""
    sesion = FabricaSesiones()
    try:
        workflow = RepositorioWorkflowOportunidadesSqlAlchemy(sesion)
        ids = [AnadirPaso(workflow).ejecutar(n).id for n in ("A", "B", "C")]
    finally:
        sesion.close()

    lectora = FabricaSesiones()
    try:
        leidos = RepositorioWorkflowOportunidadesSqlAlchemy(lectora).leer_pasos_para_copiar()
        assert [p.nombre for p in leidos] == ["A", "B", "C"]
        hilo = threading.Thread(target=_reordenar, args=(ids[::-1],))
        hilo.start()
        hilo.join(timeout=1.5)
        assert hilo.is_alive(), "La reordenación no esperó a la copia en curso"
        lectora.commit()
        hilo.join(timeout=15)
        assert not hilo.is_alive()
    finally:
        lectora.close()

    sesion = FabricaSesiones()
    try:
        repositorio = RepositorioWorkflowOportunidadesSqlAlchemy(sesion)
        assert [p.nombre for p in repositorio.listar_pasos()] == ["C", "B", "A"]
    finally:
        sesion.close()
