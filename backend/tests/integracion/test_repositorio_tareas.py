import pytest
from sqlalchemy import select
from sqlalchemy.exc import DBAPIError

from gestor_tareas.dominio.tarea.entidades import Tarea
from gestor_tareas.infraestructura.persistencia.modelos import TareaModelo
from gestor_tareas.infraestructura.persistencia.repositorios.repositorio_tareas_sqlalchemy import (
    RepositorioTareasSqlAlchemy,
)


def test_crear_persiste_la_tarea_y_le_asigna_id(sesion_bd) -> None:
    repositorio = RepositorioTareasSqlAlchemy(sesion_bd)

    creada = repositorio.crear(
        Tarea(nombre="Preparar informe", prioridad=2, descripcion="Informe trimestral")
    )

    assert creada.id is not None
    fila = sesion_bd.scalar(select(TareaModelo).where(TareaModelo.id == creada.id))
    assert (fila.nombre, fila.prioridad, fila.descripcion) == (
        "Preparar informe",
        2,
        "Informe trimestral",
    )


def test_crear_admite_prioridad_nula(sesion_bd) -> None:
    repositorio = RepositorioTareasSqlAlchemy(sesion_bd)

    creada = repositorio.crear(Tarea(nombre="Leer", prioridad=None, descripcion="Un libro"))

    assert sesion_bd.get(TareaModelo, creada.id).prioridad is None


def test_listar_devuelve_las_tareas_ordenadas_por_id(sesion_bd) -> None:
    repositorio = RepositorioTareasSqlAlchemy(sesion_bd)
    primera = repositorio.crear(Tarea(nombre="Uno", prioridad=1, descripcion="Primera"))
    segunda = repositorio.crear(Tarea(nombre="Dos", prioridad=None, descripcion="Segunda"))

    assert repositorio.listar() == [primera, segunda]


def test_listar_sin_tareas_devuelve_lista_vacia(sesion_bd) -> None:
    assert RepositorioTareasSqlAlchemy(sesion_bd).listar() == []


@pytest.mark.parametrize("prioridad", [0, 6])
def test_la_base_de_datos_rechaza_prioridad_fuera_de_rango(sesion_bd, prioridad: int) -> None:
    sesion_bd.add(TareaModelo(nombre="Tarea", prioridad=prioridad, descripcion="Texto"))

    # MySQL señala la violación de un CHECK como OperationalError (3819), no como
    # IntegrityError; ambos derivan de DBAPIError.
    with pytest.raises(DBAPIError, match="ck_tareas_prioridad_rango"):
        sesion_bd.commit()
    sesion_bd.rollback()
