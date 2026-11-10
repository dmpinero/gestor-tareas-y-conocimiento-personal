import pytest
from sqlalchemy import select

from gestor_tareas.dominio.excepciones import OrdenDePasosInvalidoError
from gestor_tareas.dominio.workflow_oportunidades.entidades import PasoWorkflowOportunidad
from gestor_tareas.infraestructura.persistencia.modelos import PasoWorkflowOportunidadModelo
from gestor_tareas.infraestructura.persistencia.repositorios.repositorio_workflow_oportunidades_sqlalchemy import (  # noqa: E501
    RepositorioWorkflowOportunidadesSqlAlchemy,
)
from gestor_tareas.infraestructura.persistencia.sesion import FabricaSesiones


def _filas() -> list[tuple[int, int, str]]:
    """(numero, id, nombre) de las filas guardadas, leídas en una sesión nueva."""
    sesion = FabricaSesiones()
    try:
        modelo = PasoWorkflowOportunidadModelo
        consulta = select(modelo.numero, modelo.id, modelo.nombre).order_by(modelo.numero)
        return [tuple(fila) for fila in sesion.execute(consulta)]
    finally:
        sesion.close()


def _con_pasos(sesion_bd, *nombres: str) -> list[PasoWorkflowOportunidad]:
    repositorio = RepositorioWorkflowOportunidadesSqlAlchemy(sesion_bd)
    return [repositorio.anadir_paso(nombre) for nombre in nombres]


def test_sin_pasos_el_listado_esta_vacio(sesion_bd) -> None:
    assert RepositorioWorkflowOportunidadesSqlAlchemy(sesion_bd).listar_pasos() == []


def test_cada_paso_nuevo_va_al_final_con_el_numero_siguiente(sesion_bd) -> None:
    a, b, c = _con_pasos(sesion_bd, "Contacto", "Propuesta", "Cierre")

    assert [(a.numero, a.nombre), (b.numero, b.nombre), (c.numero, c.nombre)] == [
        (1, "Contacto"),
        (2, "Propuesta"),
        (3, "Cierre"),
    ]
    assert len({a.id, b.id, c.id}) == 3
    assert _filas() == [(1, a.id, "Contacto"), (2, b.id, "Propuesta"), (3, c.id, "Cierre")]


def test_el_listado_va_ordenado_por_numero(sesion_bd) -> None:
    a, b, c = _con_pasos(sesion_bd, "A", "B", "C")
    repositorio = RepositorioWorkflowOportunidadesSqlAlchemy(sesion_bd)
    repositorio.reordenar_pasos([c.id, a.id, b.id])

    assert repositorio.listar_pasos() == [
        PasoWorkflowOportunidad(id=c.id, numero=1, nombre="C"),
        PasoWorkflowOportunidad(id=a.id, numero=2, nombre="A"),
        PasoWorkflowOportunidad(id=b.id, numero=3, nombre="B"),
    ]


def test_renombrar_solo_cambia_el_nombre(sesion_bd) -> None:
    a, b = _con_pasos(sesion_bd, "A", "B")

    renombrado = RepositorioWorkflowOportunidadesSqlAlchemy(sesion_bd).renombrar_paso(b.id, "Nuevo")

    assert renombrado == PasoWorkflowOportunidad(id=b.id, numero=2, nombre="Nuevo")
    assert _filas() == [(1, a.id, "A"), (2, b.id, "Nuevo")]


def test_renombrar_un_paso_que_no_existe_devuelve_none(sesion_bd) -> None:
    (a,) = _con_pasos(sesion_bd, "A")

    assert (
        RepositorioWorkflowOportunidadesSqlAlchemy(sesion_bd).renombrar_paso(a.id + 1, "X") is None
    )
    assert _filas() == [(1, a.id, "A")]


@pytest.mark.parametrize("posicion", [0, 1, 2, 3])
def test_eliminar_renumera_los_pasos_siguientes(sesion_bd, posicion) -> None:
    pasos = _con_pasos(sesion_bd, "A", "B", "C", "D")

    eliminado = RepositorioWorkflowOportunidadesSqlAlchemy(sesion_bd).eliminar_paso(
        pasos[posicion].id
    )

    assert eliminado is True
    quedan = [p for i, p in enumerate(pasos) if i != posicion]
    assert _filas() == [(n, p.id, p.nombre) for n, p in enumerate(quedan, start=1)]


def test_eliminar_un_paso_que_no_existe_devuelve_false(sesion_bd) -> None:
    a, b = _con_pasos(sesion_bd, "A", "B")

    assert RepositorioWorkflowOportunidadesSqlAlchemy(sesion_bd).eliminar_paso(b.id + 1) is False
    assert _filas() == [(1, a.id, "A"), (2, b.id, "B")]


def test_tras_eliminar_el_paso_nuevo_sigue_al_ultimo(sesion_bd) -> None:
    a, b, c = _con_pasos(sesion_bd, "A", "B", "C")
    repositorio = RepositorioWorkflowOportunidadesSqlAlchemy(sesion_bd)
    repositorio.eliminar_paso(a.id)

    d = repositorio.anadir_paso("D")

    assert d.numero == 3
    assert _filas() == [(1, b.id, "B"), (2, c.id, "C"), (3, d.id, "D")]


def test_reordenar_asigna_los_numeros_segun_el_orden_recibido(sesion_bd) -> None:
    a, b, c, d = _con_pasos(sesion_bd, "A", "B", "C", "D")

    pasos = RepositorioWorkflowOportunidadesSqlAlchemy(sesion_bd).reordenar_pasos(
        [d.id, b.id, a.id, c.id]
    )

    assert [(p.numero, p.id, p.nombre) for p in pasos] == [
        (1, d.id, "D"),
        (2, b.id, "B"),
        (3, a.id, "A"),
        (4, c.id, "C"),
    ]
    assert _filas() == [(1, d.id, "D"), (2, b.id, "B"), (3, a.id, "A"), (4, c.id, "C")]


def test_reordenar_sin_pasos_con_la_lista_vacia_devuelve_la_lista_vacia(sesion_bd) -> None:
    assert RepositorioWorkflowOportunidadesSqlAlchemy(sesion_bd).reordenar_pasos([]) == []


@pytest.mark.parametrize("orden", ["repetido", "falta", "desconocido", "vacio"], ids=lambda o: o)
def test_reordenar_con_un_orden_invalido_no_cambia_nada(sesion_bd, orden) -> None:
    a, b, c = _con_pasos(sesion_bd, "A", "B", "C")
    ids = {
        "repetido": [c.id, c.id, a.id, b.id],
        "falta": [c.id, a.id],
        "desconocido": [c.id, a.id, b.id, c.id + 1],
        "vacio": [],
    }[orden]
    repositorio = RepositorioWorkflowOportunidadesSqlAlchemy(sesion_bd)

    with pytest.raises(OrdenDePasosInvalidoError):
        repositorio.reordenar_pasos(ids)

    assert _filas() == [(1, a.id, "A"), (2, b.id, "B"), (3, c.id, "C")]
    # La sesión queda lista para otra operación.
    assert repositorio.anadir_paso("D").numero == 4
