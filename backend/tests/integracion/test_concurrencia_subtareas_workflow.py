"""Altas de tareas con workflow simultáneas con reordenaciones de ese workflow y con
cambios en los comentarios de sus pasos.

Cada hilo simula una petición: su propia sesión y su propia transacción, con los
casos de uso y los repositorios reales sobre MySQL. Las subtareas que recibe cada
tarea deben seguir uno de los órdenes completos del workflow, nunca uno a medias, y
los comentarios que reciben, uno de los estados completos de los del paso.
"""

import itertools
import random
import threading
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

import pytest
from sqlalchemy.orm import Session

from gestor_tareas.aplicacion.comentario_paso.casos_uso import (
    AnadirComentarioPaso,
    EditarComentarioPaso,
    EliminarComentarioPaso,
)
from gestor_tareas.aplicacion.tarea.crear_tarea import CrearTarea
from gestor_tareas.aplicacion.workflow.casos_uso import AnadirPaso, CrearWorkflow, ReordenarPasos
from gestor_tareas.dominio.tarea.entidades import Oportunidad, Tarea, TipoTarea
from gestor_tareas.infraestructura.persistencia.repositorios.repositorio_comentarios_paso_sqlalchemy import (  # noqa: E501
    RepositorioComentariosPasoSqlAlchemy,
)
from gestor_tareas.infraestructura.persistencia.repositorios.repositorio_comentarios_subtarea_sqlalchemy import (  # noqa: E501
    RepositorioComentariosSubtareaSqlAlchemy,
)
from gestor_tareas.infraestructura.persistencia.repositorios.repositorio_grupos_estados_sqlalchemy import (  # noqa: E501
    RepositorioGruposEstadosSqlAlchemy,
)
from gestor_tareas.infraestructura.persistencia.repositorios.repositorio_tareas_sqlalchemy import (
    RepositorioTareasSqlAlchemy,
)
from gestor_tareas.infraestructura.persistencia.repositorios.repositorio_workflows_sqlalchemy import (  # noqa: E501
    RepositorioWorkflowsSqlAlchemy,
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


def _crear_workflow_con_pasos(nombre: str, pasos: list[str]) -> int:
    sesion = FabricaSesiones()
    try:
        repositorio = RepositorioWorkflowsSqlAlchemy(sesion)
        id_workflow = CrearWorkflow(repositorio).ejecutar(nombre).id
        for paso in pasos:
            AnadirPaso(repositorio).ejecutar(id_workflow, paso)
        return id_workflow
    finally:
        sesion.close()


def _pasos_guardados(id_workflow: int) -> list[tuple[int, str]]:
    sesion = FabricaSesiones()
    try:
        workflows = RepositorioWorkflowsSqlAlchemy(sesion).listar()
        workflow = next(w for w in workflows if w.id == id_workflow)
        return [(p.id, p.nombre) for p in workflow.pasos]
    finally:
        sesion.close()


def _crear_oportunidad(i: int, id_workflow: int) -> Tarea:
    sesion = FabricaSesiones()
    try:
        return CrearTarea(
            RepositorioTareasSqlAlchemy(sesion),
            RepositorioEtiquetasSqlAlchemy(sesion),
            RepositorioPersonasSqlAlchemy(sesion),
            RepositorioWorkflowsSqlAlchemy(sesion),
            RepositorioGruposEstadosSqlAlchemy(sesion),
        ).ejecutar(
            nombre=f"Oportunidad {i}",
            descripcion="d",
            fecha_creacion=datetime(2026, 11, 10, 9, 0, 0),
            etiquetas=[f"etiqueta {i % 2}"],
            tipo=TipoTarea.OPORTUNIDAD,
            oportunidad=Oportunidad(codigo=f"OP-{i}"),
            workflow_id=id_workflow,
        )
    finally:
        sesion.close()


def _reordenar(id_workflow: int, ids: list[int]) -> list[str]:
    sesion = FabricaSesiones()
    try:
        workflow = ReordenarPasos(RepositorioWorkflowsSqlAlchemy(sesion)).ejecutar(id_workflow, ids)
        return [p.nombre for p in workflow.pasos]
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
    id_workflow = _crear_workflow_con_pasos(
        f"Workflow {ronda}", [f"Paso {i}" for i in range(_PASOS)]
    )
    por_id = dict(_pasos_guardados(id_workflow))
    ordenes = [list(por_id)]
    for semilla in range(_REORDENACIONES):
        orden = list(por_id)
        random.Random(ronda * 100 + semilla).shuffle(orden)
        ordenes.append(orden)
    nombres_validos = [[por_id[i] for i in orden] for orden in ordenes]

    operaciones: list[Callable[[], object]] = [
        *[lambda i=i: _crear_oportunidad(i, id_workflow) for i in range(_ALTAS)],
        *[lambda o=o: _reordenar(id_workflow, o) for o in ordenes[1:]],
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
    id_workflow = _crear_workflow_con_pasos("Workflow de la copia", ["A", "B", "C"])
    ids = [id_paso for id_paso, _ in _pasos_guardados(id_workflow)]

    lectora = FabricaSesiones()
    try:
        leido = RepositorioWorkflowsSqlAlchemy(lectora).leer_para_copiar(id_workflow)
        assert leido is not None
        assert [p.nombre for p in leido.pasos] == ["A", "B", "C"]
        hilo = threading.Thread(target=_reordenar, args=(id_workflow, ids[::-1]))
        hilo.start()
        hilo.join(timeout=1.5)
        assert hilo.is_alive(), "La reordenación no esperó a la copia en curso"
        lectora.commit()
        hilo.join(timeout=15)
        assert not hilo.is_alive()
    finally:
        lectora.close()

    assert [nombre for _, nombre in _pasos_guardados(id_workflow)] == ["C", "B", "A"]


# --- Comentarios de los pasos ---------------------------------------------------------


def _en_sesion(operacion: Callable[[Session], object]) -> object:
    sesion = FabricaSesiones()
    try:
        return operacion(sesion)
    finally:
        sesion.close()


def _comentarios_paso(id_workflow: int, id_paso: int) -> list:
    return _en_sesion(
        lambda s: RepositorioComentariosPasoSqlAlchemy(s).listar_de_paso(id_workflow, id_paso)
    )


def _comentar_paso(id_workflow: int, id_paso: int, texto: str) -> object:
    return _en_sesion(
        lambda s: AnadirComentarioPaso(RepositorioComentariosPasoSqlAlchemy(s)).ejecutar(
            id_workflow, id_paso, texto
        )
    )


def _editar_comentario_paso(id_workflow: int, id_paso: int, id_c: int, texto: str) -> object:
    return _en_sesion(
        lambda s: EditarComentarioPaso(RepositorioComentariosPasoSqlAlchemy(s)).ejecutar(
            id_workflow, id_paso, id_c, texto
        )
    )


def _eliminar_comentario_paso(id_workflow: int, id_paso: int, id_c: int) -> object:
    return _en_sesion(
        lambda s: EliminarComentarioPaso(RepositorioComentariosPasoSqlAlchemy(s)).ejecutar(
            id_workflow, id_paso, id_c
        )
    )


def _copiados(tarea: Tarea, indice: int) -> list:
    subtarea = tarea.subtareas[indice]
    return _en_sesion(
        lambda s: RepositorioComentariosSubtareaSqlAlchemy(s).listar_de_subtarea(
            tarea.id, subtarea.id
        )
    )


def _estados_validos(textos: list[str], paso: int) -> list[list[str]]:
    """Los estados completos de los comentarios del paso: los de aplicar cualquier
    subconjunto de sus tres cambios (editar el primero, borrar el segundo y añadir
    uno al final), que son independientes entre sí."""
    estados = []
    for editar, borrar, anadir in itertools.product((False, True), repeat=3):
        estado = list(textos)
        if editar:
            estado[0] = f"{textos[0]} editado"
        if borrar:
            del estado[1]
        if anadir:
            estado.append(f"Nuevo {paso}")
        estados.append(estado)
    return estados


@pytest.mark.usefixtures("sesion_bd")
@pytest.mark.parametrize("ronda", range(_RONDAS))
def test_las_altas_copian_los_comentarios_de_cada_paso_completos_aunque_cambien_a_la_vez(
    ronda,
) -> None:
    id_workflow = _crear_workflow_con_pasos(f"Workflow {ronda}", ["P0", "P1", "P2"])
    ids_pasos = [id_paso for id_paso, _ in _pasos_guardados(id_workflow)]
    textos = {}
    for paso, id_paso in enumerate(ids_pasos):
        textos[id_paso] = [f"C{paso}.{i}" for i in range(3)]
        for texto in textos[id_paso]:
            _comentar_paso(id_workflow, id_paso, texto)

    cambios: list[Callable[[], object]] = []
    for paso, id_paso in enumerate(ids_pasos):
        primero, segundo, _ = _comentarios_paso(id_workflow, id_paso)
        cambios += [
            lambda p=id_paso, c=primero: _editar_comentario_paso(
                id_workflow, p, c.id, f"{c.texto} editado"
            ),
            lambda p=id_paso, c=segundo: _eliminar_comentario_paso(id_workflow, p, c.id),
            lambda p=id_paso, n=paso: _comentar_paso(id_workflow, p, f"Nuevo {n}"),
        ]
    random.Random(ronda).shuffle(cambios)
    altas = [lambda i=i: _crear_oportunidad(i, id_workflow) for i in range(_ALTAS)]
    resultados = _a_la_vez([*altas, *cambios])

    tareas = [r for r in resultados if isinstance(r, Tarea)]
    assert len(tareas) == _ALTAS
    for tarea in tareas:
        for paso, id_paso in enumerate(ids_pasos):
            copiados = _copiados(tarea, paso)
            assert [c.texto for c in copiados] in _estados_validos(textos[id_paso], paso)
            assert tarea.subtareas[paso].comentarios == len(copiados)
            assert all(c.editado is None for c in copiados)
            assert len({c.creado for c in copiados}) <= 1
    # Al final el paso tiene todos los cambios aplicados.
    for paso, id_paso in enumerate(ids_pasos):
        finales = [c.texto for c in _comentarios_paso(id_workflow, id_paso)]
        assert finales == _estados_validos(textos[id_paso], paso)[-1]


@pytest.mark.usefixtures("sesion_bd")
@pytest.mark.parametrize("cambio", ["anadir", "editar", "eliminar"])
def test_un_cambio_en_los_comentarios_del_paso_espera_a_que_termine_la_copia_en_curso(
    cambio,
) -> None:
    """Mientras una transacción ha leído el workflow para copiarlo, un alta, una
    edición o un borrado de un comentario de sus pasos no puede confirmarse."""
    id_workflow = _crear_workflow_con_pasos("Workflow de la copia", ["A"])
    (id_paso,) = [id_paso for id_paso, _ in _pasos_guardados(id_workflow)]
    comentario = _comentar_paso(id_workflow, id_paso, "Uno")
    operacion = {
        "anadir": lambda: _comentar_paso(id_workflow, id_paso, "Dos"),
        "editar": lambda: _editar_comentario_paso(id_workflow, id_paso, comentario.id, "Otro"),
        "eliminar": lambda: _eliminar_comentario_paso(id_workflow, id_paso, comentario.id),
    }[cambio]

    lectora = FabricaSesiones()
    try:
        leido = RepositorioWorkflowsSqlAlchemy(lectora).leer_para_copiar(id_workflow)
        assert leido.pasos[0].comentarios_para_copiar == ["Uno"]
        hilo = threading.Thread(target=operacion)
        hilo.start()
        hilo.join(timeout=1.5)
        assert hilo.is_alive(), "El cambio en los comentarios no esperó a la copia en curso"
        lectora.commit()
        hilo.join(timeout=15)
        assert not hilo.is_alive()
    finally:
        lectora.close()

    esperados = {"anadir": ["Uno", "Dos"], "editar": ["Otro"], "eliminar": []}[cambio]
    assert [c.texto for c in _comentarios_paso(id_workflow, id_paso)] == esperados
