"""Altas y ediciones simultáneas de tareas que comparten nombres nuevos del catálogo.

Cada hilo simula una petición: su propia sesión y su propia transacción, con
los repositorios reales sobre MySQL. Una barrera hace que todos empiecen a la
vez para provocar las carreras entre la búsqueda, el alta y el enlace.
"""

import threading
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

import pytest
from sqlalchemy import func, select

from gestor_tareas.aplicacion.tarea.actualizar_tarea import ActualizarTarea
from gestor_tareas.aplicacion.tarea.crear_tarea import CrearTarea
from gestor_tareas.dominio.excepciones import ConflictoDeConcurrenciaError
from gestor_tareas.dominio.tarea.entidades import Tarea
from gestor_tareas.infraestructura.persistencia.modelos import EtiquetaModelo, PersonaModelo
from gestor_tareas.infraestructura.persistencia.repositorios.repositorio_grupos_estados_sqlalchemy import (  # noqa: E501
    RepositorioGruposEstadosSqlAlchemy,
)
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

_FECHA_CREACION = datetime(2026, 11, 9, 10, 0, 0)
_HILOS = 8
_RONDAS = 6


def _crear(etiquetas: list[str], asignados: list[str]) -> Tarea:
    sesion = FabricaSesiones()
    try:
        return CrearTarea(
            RepositorioTareasSqlAlchemy(sesion),
            RepositorioEtiquetasSqlAlchemy(sesion),
            RepositorioPersonasSqlAlchemy(sesion),
            RepositorioWorkflowOportunidadesSqlAlchemy(sesion),
            RepositorioGruposEstadosSqlAlchemy(sesion),
        ).ejecutar(
            nombre="C",
            descripcion="d",
            fecha_creacion=_FECHA_CREACION,
            etiquetas=etiquetas,
            asignados=asignados,
        )
    finally:
        sesion.close()


def _actualizar(id_tarea: int, etiquetas: list[str], asignados: list[str]) -> Tarea:
    sesion = FabricaSesiones()
    try:
        return ActualizarTarea(
            RepositorioTareasSqlAlchemy(sesion),
            RepositorioEtiquetasSqlAlchemy(sesion),
            RepositorioPersonasSqlAlchemy(sesion),
            RepositorioGruposEstadosSqlAlchemy(sesion),
        ).ejecutar(
            id_tarea,
            nombre="C",
            descripcion="d",
            fecha_creacion=_FECHA_CREACION,
            etiquetas=etiquetas,
            asignados=asignados,
        )
    finally:
        sesion.close()


def _a_la_vez(operaciones: list[Callable[[], Tarea]]) -> list[Tarea]:
    """Lanza todas las operaciones en paralelo y devuelve sus resultados en orden.

    Si alguna falla, ``result()`` relanza su excepción y el test falla.
    """
    barrera = threading.Barrier(len(operaciones))

    def tras_la_barrera(operacion: Callable[[], Tarea]) -> Tarea:
        barrera.wait()
        return operacion()

    with ThreadPoolExecutor(max_workers=len(operaciones)) as ejecutor:
        futuros = [ejecutor.submit(tras_la_barrera, op) for op in operaciones]
        return [futuro.result() for futuro in futuros]


def _filas_por_nombre(sesion_bd, modelo, nombres: list[str]) -> int:
    sesion_bd.rollback()  # Instantánea nueva para ver lo confirmado por los hilos.
    return sesion_bd.scalar(
        select(func.count()).select_from(modelo).where(modelo.nombre.in_(nombres))
    )


def _combinaciones(ronda: int) -> list[tuple[list[str], list[str]]]:
    """Mitad de los hilos con los nombres en un orden y mitad en el inverso."""
    etiquetas = [f"X{ronda}", f"Y{ronda}", f"Z{ronda}"]
    asignados = [f"Ana{ronda}", f"Bea{ronda}"]
    return [
        (etiquetas, asignados) if i % 2 else (etiquetas[::-1], [n.upper() for n in asignados[::-1]])
        for i in range(_HILOS)
    ]


def _comprobar_listas(tareas: list[Tarea], etiquetas: list[str], asignados: list[str]) -> None:
    """Todas las tareas enlazan los mismos nombres, con la grafía del primer alta."""
    for tarea in tareas:
        assert tarea.id is not None
        assert tarea.etiquetas == etiquetas
        assert [n.casefold() for n in tarea.asignados] == [n.casefold() for n in asignados]
        assert tarea.asignados == tareas[0].asignados


@pytest.mark.parametrize("ronda", range(_RONDAS))
def test_altas_simultaneas_con_nombres_nuevos_compartidos(sesion_bd, ronda) -> None:
    combinaciones = _combinaciones(ronda)

    tareas = _a_la_vez([lambda e=e, a=a: _crear(e, a) for e, a in combinaciones])

    etiquetas, asignados = combinaciones[1]
    _comprobar_listas(tareas, etiquetas, asignados)
    assert len({t.id for t in tareas}) == _HILOS
    assert _filas_por_nombre(sesion_bd, EtiquetaModelo, etiquetas) == len(etiquetas)
    assert _filas_por_nombre(sesion_bd, PersonaModelo, asignados) == len(asignados)


@pytest.mark.parametrize("ronda", range(_RONDAS))
def test_ediciones_simultaneas_con_nombres_nuevos_compartidos(sesion_bd, ronda) -> None:
    ids = [_crear([], []).id for _ in range(_HILOS)]
    combinaciones = _combinaciones(ronda)

    tareas = _a_la_vez(
        [
            lambda i=i, e=e, a=a: _actualizar(i, e, a)
            for i, (e, a) in zip(ids, combinaciones, strict=True)
        ]
    )

    etiquetas, asignados = combinaciones[1]
    assert [t.id for t in tareas] == ids
    _comprobar_listas(tareas, etiquetas, asignados)
    assert _filas_por_nombre(sesion_bd, EtiquetaModelo, etiquetas) == len(etiquetas)
    assert _filas_por_nombre(sesion_bd, PersonaModelo, asignados) == len(asignados)


def test_un_interbloqueo_en_el_catalogo_se_traduce_en_conflicto_y_deshace_la_transaccion(
    sesion_bd,
) -> None:
    """A y B dan de alta X e Y en orden cruzado dentro de un SAVEPOINT.

    MySQL elige una víctima, deshace toda su transacción y la vuelta al SAVEPOINT
    falla; el repositorio debe avisar con ``ConflictoDeConcurrenciaError``, dejar
    la sesión lista para reintentar y no reutilizar el alta deshecha.
    """
    sesion_a, sesion_b = FabricaSesiones(), FabricaSesiones()
    try:
        RepositorioEtiquetasSqlAlchemy(sesion_a).obtener_o_crear(["X"])
        RepositorioEtiquetasSqlAlchemy(sesion_b).obtener_o_crear(["Y"])

        def cruzar(sesion, nombre: str) -> BaseException | None:
            try:
                RepositorioEtiquetasSqlAlchemy(sesion).obtener_o_crear([nombre])
            except ConflictoDeConcurrenciaError as error:
                return error
            sesion.commit()
            return None

        with ThreadPoolExecutor(max_workers=2) as ejecutor:
            espera_a = ejecutor.submit(cruzar, sesion_a, "Y")
            threading.Event().wait(0.3)  # A queda esperando el bloqueo de Y.
            espera_b = ejecutor.submit(cruzar, sesion_b, "X")
            errores = [espera_a.result(), espera_b.result()]

        [victima] = [s for s, e in zip((sesion_a, sesion_b), errores, strict=True) if e]
        [error] = [e for e in errores if e]
        assert "1213" in repr(error.__cause__) or "1213" in repr(error.__cause__.__context__)

        # La víctima reintenta en una transacción nueva y enlaza filas que existen.
        reintento = RepositorioEtiquetasSqlAlchemy(victima).obtener_o_crear(["X", "Y"])
        tarea = RepositorioTareasSqlAlchemy(victima).crear(
            Tarea(
                nombre="C",
                descripcion="d",
                fecha_creacion=_FECHA_CREACION,
                etiquetas=[e.nombre for e in reintento],
            )
        )
    finally:
        sesion_a.close()
        sesion_b.close()

    assert tarea.etiquetas == ["X", "Y"]
    assert _filas_por_nombre(sesion_bd, EtiquetaModelo, ["X", "Y"]) == 2
