"""Editar o completar una tarea que otra petición acaba de borrar.

Regresión: la edición y el cambio de completada leían la tarea sin bloqueo; si un
borrado se confirmaba entre la lectura y la escritura, el UPDATE no encontraba la
fila y la API respondía 500 en lugar de 404.
"""

from datetime import datetime

import pytest

from gestor_tareas.dominio.excepciones import EntidadNoEncontradaError
from gestor_tareas.dominio.tarea.entidades import Tarea
from gestor_tareas.infraestructura.persistencia.repositorios.repositorio_tareas_sqlalchemy import (
    RepositorioTareasSqlAlchemy,
)
from gestor_tareas.infraestructura.persistencia.sesion import FabricaSesiones


def _tarea_creada(sesion) -> Tarea:
    return RepositorioTareasSqlAlchemy(sesion).crear(
        Tarea(nombre="Borrable", descripcion="d", fecha_creacion=datetime(2026, 11, 11, 9, 0, 0))
    )


def _borrar_en_otra_sesion(id_tarea: int) -> None:
    otra = FabricaSesiones()
    try:
        assert RepositorioTareasSqlAlchemy(otra).eliminar(id_tarea) is True
    finally:
        otra.close()


def test_editar_una_tarea_borrada_tras_leerla_indica_que_no_existe(sesion_bd) -> None:
    id_tarea = _tarea_creada(sesion_bd).id
    sesion_bd.rollback()
    repositorio = RepositorioTareasSqlAlchemy(sesion_bd)
    tarea = repositorio.obtener_por_id(id_tarea)  # Como el caso de uso: leer y luego guardar.
    assert tarea is not None
    _borrar_en_otra_sesion(id_tarea)

    tarea.nombre = "Cambiada"
    with pytest.raises(EntidadNoEncontradaError, match=f"No existe la tarea con id {id_tarea}"):
        repositorio.actualizar(tarea)


def test_completar_una_tarea_borrada_tras_leerla_indica_que_no_existe(sesion_bd) -> None:
    id_tarea = _tarea_creada(sesion_bd).id
    sesion_bd.rollback()
    repositorio = RepositorioTareasSqlAlchemy(sesion_bd)
    assert repositorio.obtener_por_id(id_tarea) is not None
    _borrar_en_otra_sesion(id_tarea)

    assert repositorio.cambiar_completada(id_tarea, True) is None
