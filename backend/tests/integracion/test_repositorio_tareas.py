from datetime import datetime

import pytest
from sqlalchemy import select
from sqlalchemy.exc import DBAPIError

from gestor_tareas.dominio.tarea.entidades import Tarea
from gestor_tareas.infraestructura.persistencia.modelos import TareaModelo
from gestor_tareas.infraestructura.persistencia.repositorios.repositorio_tareas_sqlalchemy import (
    RepositorioTareasSqlAlchemy,
)

_FECHA_HORA = datetime(2026, 11, 9, 10, 30, 0)


def test_crear_persiste_la_tarea_y_le_asigna_id(sesion_bd) -> None:
    repositorio = RepositorioTareasSqlAlchemy(sesion_bd)

    creada = repositorio.crear(
        Tarea(
            nombre="Preparar informe",
            prioridad=2,
            descripcion="Informe trimestral",
            fecha_hora=_FECHA_HORA,
        )
    )

    assert creada.id is not None
    assert creada.fecha_hora == _FECHA_HORA
    fila = sesion_bd.scalar(select(TareaModelo).where(TareaModelo.id == creada.id))
    assert (fila.nombre, fila.prioridad, fila.descripcion, fila.fecha_hora) == (
        "Preparar informe",
        2,
        "Informe trimestral",
        _FECHA_HORA,
    )


def test_crear_admite_prioridad_nula(sesion_bd) -> None:
    repositorio = RepositorioTareasSqlAlchemy(sesion_bd)

    creada = repositorio.crear(
        Tarea(nombre="Leer", prioridad=None, descripcion="Un libro", fecha_hora=_FECHA_HORA)
    )

    assert sesion_bd.get(TareaModelo, creada.id).prioridad is None


def test_listar_devuelve_las_tareas_ordenadas_por_id(sesion_bd) -> None:
    repositorio = RepositorioTareasSqlAlchemy(sesion_bd)
    primera = repositorio.crear(
        Tarea(nombre="Uno", prioridad=1, descripcion="Primera", fecha_hora=_FECHA_HORA)
    )
    segunda = repositorio.crear(
        Tarea(nombre="Dos", prioridad=None, descripcion="Segunda", fecha_hora=_FECHA_HORA)
    )

    assert repositorio.listar() == [primera, segunda]


def test_listar_sin_tareas_devuelve_lista_vacia(sesion_bd) -> None:
    assert RepositorioTareasSqlAlchemy(sesion_bd).listar() == []


def test_obtener_por_id_devuelve_la_tarea_o_none(sesion_bd) -> None:
    repositorio = RepositorioTareasSqlAlchemy(sesion_bd)
    creada = repositorio.crear(
        Tarea(nombre="Uno", prioridad=1, descripcion="Primera", fecha_hora=_FECHA_HORA)
    )

    assert repositorio.obtener_por_id(creada.id) == creada
    assert repositorio.obtener_por_id(creada.id + 1) is None


def test_actualizar_persiste_todos_los_campos(sesion_bd) -> None:
    repositorio = RepositorioTareasSqlAlchemy(sesion_bd)
    creada = repositorio.crear(
        Tarea(nombre="Uno", prioridad=1, descripcion="Primera", fecha_hora=_FECHA_HORA)
    )
    otra = repositorio.crear(
        Tarea(nombre="Dos", prioridad=2, descripcion="Segunda", fecha_hora=_FECHA_HORA)
    )
    nueva_fecha_hora = datetime(2026, 12, 1, 8, 15, 45)

    actualizada = repositorio.actualizar(
        Tarea(
            id=creada.id,
            nombre="Uno editada",
            prioridad=None,
            descripcion="Primera editada",
            fecha_hora=nueva_fecha_hora,
        )
    )

    assert actualizada.id == creada.id
    sesion_bd.expire_all()
    fila = sesion_bd.get(TareaModelo, creada.id)
    assert (fila.nombre, fila.prioridad, fila.descripcion, fila.fecha_hora) == (
        "Uno editada",
        None,
        "Primera editada",
        nueva_fecha_hora,
    )
    assert repositorio.listar() == [actualizada, otra]


@pytest.mark.parametrize("prioridad", [0, 6])
def test_la_base_de_datos_rechaza_prioridad_fuera_de_rango(sesion_bd, prioridad: int) -> None:
    sesion_bd.add(
        TareaModelo(
            nombre="Tarea", prioridad=prioridad, descripcion="Texto", fecha_hora=_FECHA_HORA
        )
    )

    # MySQL señala la violación de un CHECK como OperationalError (3819), no como
    # IntegrityError; ambos derivan de DBAPIError.
    with pytest.raises(DBAPIError, match="ck_tareas_prioridad_rango"):
        sesion_bd.commit()
    sesion_bd.rollback()


def test_la_base_de_datos_exige_fecha_hora(sesion_bd) -> None:
    sesion_bd.add(TareaModelo(nombre="Tarea", prioridad=None, descripcion="Texto"))

    with pytest.raises(DBAPIError, match="fecha_hora"):
        sesion_bd.commit()
    sesion_bd.rollback()
