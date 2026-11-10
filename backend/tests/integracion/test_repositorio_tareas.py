from datetime import datetime

import pytest
from sqlalchemy import delete, select
from sqlalchemy.exc import DBAPIError

from gestor_tareas.dominio.tarea.entidades import Tarea
from gestor_tareas.infraestructura.persistencia.modelos import (
    EtiquetaModelo,
    PersonaModelo,
    TareaModelo,
    tarea_etiquetas,
    tarea_personas,
)
from gestor_tareas.infraestructura.persistencia.repositorios.repositorio_tareas_sqlalchemy import (
    RepositorioTareasSqlAlchemy,
)
from gestor_tareas.infraestructura.persistencia.repositorios.repositorios_catalogos_sqlalchemy import (  # noqa: E501
    RepositorioEtiquetasSqlAlchemy,
    RepositorioPersonasSqlAlchemy,
)

_FECHA_CREACION = datetime(2026, 11, 9, 10, 30, 0)


def test_crear_persiste_la_tarea_y_le_asigna_id(sesion_bd) -> None:
    repositorio = RepositorioTareasSqlAlchemy(sesion_bd)

    creada = repositorio.crear(
        Tarea(
            nombre="Preparar informe",
            prioridad=2,
            descripcion="Informe trimestral",
            fecha_creacion=_FECHA_CREACION,
        )
    )

    assert creada.id is not None
    assert creada.fecha_creacion == _FECHA_CREACION
    fila = sesion_bd.scalar(select(TareaModelo).where(TareaModelo.id == creada.id))
    assert (fila.nombre, fila.prioridad, fila.descripcion, fila.fecha_creacion) == (
        "Preparar informe",
        2,
        "Informe trimestral",
        _FECHA_CREACION,
    )


def test_crear_admite_prioridad_nula(sesion_bd) -> None:
    repositorio = RepositorioTareasSqlAlchemy(sesion_bd)

    creada = repositorio.crear(
        Tarea(nombre="Leer", prioridad=None, descripcion="Un libro", fecha_creacion=_FECHA_CREACION)
    )

    assert sesion_bd.get(TareaModelo, creada.id).prioridad is None


def test_listar_devuelve_las_tareas_ordenadas_por_id(sesion_bd) -> None:
    repositorio = RepositorioTareasSqlAlchemy(sesion_bd)
    primera = repositorio.crear(
        Tarea(nombre="Uno", prioridad=1, descripcion="Primera", fecha_creacion=_FECHA_CREACION)
    )
    segunda = repositorio.crear(
        Tarea(nombre="Dos", prioridad=None, descripcion="Segunda", fecha_creacion=_FECHA_CREACION)
    )

    assert repositorio.listar() == [primera, segunda]


def test_listar_sin_tareas_devuelve_lista_vacia(sesion_bd) -> None:
    assert RepositorioTareasSqlAlchemy(sesion_bd).listar() == []


def test_obtener_por_id_devuelve_la_tarea_o_none(sesion_bd) -> None:
    repositorio = RepositorioTareasSqlAlchemy(sesion_bd)
    creada = repositorio.crear(
        Tarea(nombre="Uno", prioridad=1, descripcion="Primera", fecha_creacion=_FECHA_CREACION)
    )

    assert repositorio.obtener_por_id(creada.id) == creada
    assert repositorio.obtener_por_id(creada.id + 1) is None


def test_actualizar_persiste_todos_los_campos(sesion_bd) -> None:
    repositorio = RepositorioTareasSqlAlchemy(sesion_bd)
    creada = repositorio.crear(
        Tarea(nombre="Uno", prioridad=1, descripcion="Primera", fecha_creacion=_FECHA_CREACION)
    )
    otra = repositorio.crear(
        Tarea(nombre="Dos", prioridad=2, descripcion="Segunda", fecha_creacion=_FECHA_CREACION)
    )
    nueva_fecha = datetime(2026, 12, 1, 8, 15, 45)

    actualizada = repositorio.actualizar(
        Tarea(
            id=creada.id,
            nombre="Uno editada",
            prioridad=None,
            descripcion="Primera editada",
            fecha_creacion=nueva_fecha,
        )
    )

    assert actualizada.id == creada.id
    sesion_bd.expire_all()
    fila = sesion_bd.get(TareaModelo, creada.id)
    assert (fila.nombre, fila.prioridad, fila.descripcion, fila.fecha_creacion) == (
        "Uno editada",
        None,
        "Primera editada",
        nueva_fecha,
    )
    assert repositorio.listar() == [actualizada, otra]


@pytest.mark.parametrize("prioridad", [0, 6])
def test_la_base_de_datos_rechaza_prioridad_fuera_de_rango(sesion_bd, prioridad: int) -> None:
    sesion_bd.add(
        TareaModelo(
            nombre="Tarea", prioridad=prioridad, descripcion="Texto", fecha_creacion=_FECHA_CREACION
        )
    )

    # MySQL señala la violación de un CHECK como OperationalError (3819), no como
    # IntegrityError; ambos derivan de DBAPIError.
    with pytest.raises(DBAPIError, match="ck_tareas_prioridad_rango"):
        sesion_bd.commit()
    sesion_bd.rollback()


def test_la_base_de_datos_exige_fecha_creacion(sesion_bd) -> None:
    sesion_bd.add(TareaModelo(nombre="Tarea", prioridad=None, descripcion="Texto"))

    with pytest.raises(DBAPIError, match="fecha_creacion"):
        sesion_bd.commit()
    sesion_bd.rollback()


def test_crear_persiste_la_fecha_de_vencimiento_opcional(sesion_bd) -> None:
    repositorio = RepositorioTareasSqlAlchemy(sesion_bd)
    vencimiento = datetime(2026, 11, 20, 18, 0, 0)

    con_vencimiento = repositorio.crear(
        Tarea(
            nombre="Uno",
            descripcion="Primera",
            fecha_creacion=_FECHA_CREACION,
            fecha_vencimiento=vencimiento,
        )
    )
    sin_vencimiento = repositorio.crear(
        Tarea(nombre="Dos", descripcion="Segunda", fecha_creacion=_FECHA_CREACION)
    )

    assert con_vencimiento.fecha_vencimiento == vencimiento
    sesion_bd.expire_all()
    assert sesion_bd.get(TareaModelo, con_vencimiento.id).fecha_vencimiento == vencimiento
    assert sesion_bd.get(TareaModelo, sin_vencimiento.id).fecha_vencimiento is None


def _nombres_enlazados(sesion_bd, tabla_union, modelo, columna, id_tarea: int) -> list[str]:
    consulta = (
        select(modelo.nombre)
        .join(tabla_union, getattr(tabla_union.c, columna) == modelo.id)
        .where(tabla_union.c.tarea_id == id_tarea)
    )
    return sorted(sesion_bd.scalars(consulta).all())


def test_crear_enlaza_etiquetas_y_asignados_y_los_devuelve_ordenados(sesion_bd) -> None:
    repositorio = RepositorioTareasSqlAlchemy(sesion_bd)
    RepositorioEtiquetasSqlAlchemy(sesion_bd).obtener_o_crear(["urgente", "Casa"])
    RepositorioPersonasSqlAlchemy(sesion_bd).obtener_o_crear(["Lucía", "ana"])

    creada = repositorio.crear(
        Tarea(
            nombre="Uno",
            descripcion="Primera",
            fecha_creacion=_FECHA_CREACION,
            etiquetas=["urgente", "Casa"],
            asignados=["Lucía", "ana"],
        )
    )

    assert (creada.etiquetas, creada.asignados) == (["Casa", "urgente"], ["ana", "Lucía"])
    assert _nombres_enlazados(
        sesion_bd, tarea_etiquetas, EtiquetaModelo, "etiqueta_id", creada.id
    ) == ["Casa", "urgente"]
    assert _nombres_enlazados(
        sesion_bd, tarea_personas, PersonaModelo, "persona_id", creada.id
    ) == ["Lucía", "ana"]
    assert repositorio.listar() == [creada]


def test_actualizar_sustituye_el_conjunto_de_etiquetas_y_asignados(sesion_bd) -> None:
    repositorio = RepositorioTareasSqlAlchemy(sesion_bd)
    RepositorioEtiquetasSqlAlchemy(sesion_bd).obtener_o_crear(["casa", "urgente", "trabajo"])
    RepositorioPersonasSqlAlchemy(sesion_bd).obtener_o_crear(["Ana"])
    creada = repositorio.crear(
        Tarea(
            nombre="Uno",
            descripcion="Primera",
            fecha_creacion=_FECHA_CREACION,
            etiquetas=["casa", "urgente"],
            asignados=["Ana"],
        )
    )

    actualizada = repositorio.actualizar(
        Tarea(
            id=creada.id,
            nombre="Uno",
            descripcion="Primera",
            fecha_creacion=_FECHA_CREACION,
            etiquetas=["trabajo", "casa"],
            asignados=[],
        )
    )

    assert (actualizada.etiquetas, actualizada.asignados) == (["casa", "trabajo"], [])
    sesion_bd.expire_all()
    assert _nombres_enlazados(
        sesion_bd, tarea_etiquetas, EtiquetaModelo, "etiqueta_id", creada.id
    ) == ["casa", "trabajo"]
    assert (
        _nombres_enlazados(sesion_bd, tarea_personas, PersonaModelo, "persona_id", creada.id) == []
    )
    # El catálogo no pierde la etiqueta que ya no usa la tarea.
    assert sesion_bd.scalar(select(EtiquetaModelo).where(EtiquetaModelo.nombre == "urgente"))


def test_borrar_una_tarea_borra_sus_enlaces_en_cascada(sesion_bd) -> None:
    repositorio = RepositorioTareasSqlAlchemy(sesion_bd)
    RepositorioEtiquetasSqlAlchemy(sesion_bd).obtener_o_crear(["casa"])
    RepositorioPersonasSqlAlchemy(sesion_bd).obtener_o_crear(["Ana"])
    creada = repositorio.crear(
        Tarea(
            nombre="Uno",
            descripcion="Primera",
            fecha_creacion=_FECHA_CREACION,
            etiquetas=["casa"],
            asignados=["Ana"],
        )
    )

    # Borrado directo en SQL: comprueba el ON DELETE CASCADE de la base de datos.
    sesion_bd.execute(delete(TareaModelo.__table__).where(TareaModelo.id == creada.id))
    sesion_bd.commit()

    assert sesion_bd.execute(select(tarea_etiquetas)).all() == []
    assert sesion_bd.execute(select(tarea_personas)).all() == []
