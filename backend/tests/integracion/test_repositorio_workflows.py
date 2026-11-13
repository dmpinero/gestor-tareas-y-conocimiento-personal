from datetime import datetime

import pytest
from sqlalchemy import select

from gestor_tareas.dominio.excepciones import (
    EntidadNoEncontradaError,
    NombreDuplicadoError,
    OrdenDePasosInvalidoError,
)
from gestor_tareas.dominio.tarea.entidades import ReferenciaWorkflow, Subtarea, Tarea
from gestor_tareas.dominio.workflow.entidades import PasoWorkflow, Workflow
from gestor_tareas.infraestructura.persistencia.modelos import (
    PasoWorkflowModelo,
    SubtareaModelo,
    TareaModelo,
    WorkflowModelo,
)
from gestor_tareas.infraestructura.persistencia.repositorios.repositorio_tareas_sqlalchemy import (
    RepositorioTareasSqlAlchemy,
)
from gestor_tareas.infraestructura.persistencia.repositorios.repositorio_workflows_sqlalchemy import (  # noqa: E501
    RepositorioWorkflowsSqlAlchemy,
)
from gestor_tareas.infraestructura.persistencia.sesion import FabricaSesiones


def _filas(id_workflow: int) -> list[tuple[int, int, str]]:
    """(numero, id, nombre) de los pasos guardados del workflow, en una sesión nueva."""
    sesion = FabricaSesiones()
    try:
        modelo = PasoWorkflowModelo
        consulta = (
            select(modelo.numero, modelo.id, modelo.nombre)
            .where(modelo.workflow_id == id_workflow)
            .order_by(modelo.numero)
        )
        return [tuple(fila) for fila in sesion.execute(consulta)]
    finally:
        sesion.close()


def _nombres_guardados() -> list[str]:
    sesion = FabricaSesiones()
    try:
        return sorted(sesion.scalars(select(WorkflowModelo.nombre)))
    finally:
        sesion.close()


def _con_pasos(sesion_bd, nombre: str, *pasos: str) -> Workflow:
    repositorio = RepositorioWorkflowsSqlAlchemy(sesion_bd)
    workflow = repositorio.crear(nombre)
    for paso in pasos:
        workflow = repositorio.anadir_paso(workflow.id, paso)
    return workflow


def _ids(workflow: Workflow) -> list[int]:
    return [p.id for p in workflow.pasos]


def test_sin_workflows_el_listado_esta_vacio(sesion_bd) -> None:
    assert RepositorioWorkflowsSqlAlchemy(sesion_bd).listar() == []


def test_crear_guarda_un_workflow_sin_pasos(sesion_bd) -> None:
    workflow = RepositorioWorkflowsSqlAlchemy(sesion_bd).crear("Ventas")

    assert workflow == Workflow(id=workflow.id, nombre="Ventas", pasos=[])
    assert _nombres_guardados() == ["Ventas"]


def test_el_listado_va_por_nombre_sin_mayusculas_con_sus_pasos_por_numero(sesion_bd) -> None:
    ventas = _con_pasos(sesion_bd, "ventas", "A", "B")
    alta = _con_pasos(sesion_bd, "Alta")
    repositorio = RepositorioWorkflowsSqlAlchemy(sesion_bd)
    a, b = _ids(ventas)
    repositorio.reordenar_pasos(ventas.id, [b, a])

    assert repositorio.listar() == [
        Workflow(id=alta.id, nombre="Alta", pasos=[]),
        Workflow(
            id=ventas.id,
            nombre="ventas",
            pasos=[
                PasoWorkflow(id=b, numero=1, nombre="B"),
                PasoWorkflow(id=a, numero=2, nombre="A"),
            ],
        ),
    ]


@pytest.mark.parametrize("repetido", ["Ventas", "VENTAS", "ventas"])
def test_no_puede_haber_dos_workflows_con_el_mismo_nombre_sin_mayusculas(
    sesion_bd, repetido
) -> None:
    repositorio = RepositorioWorkflowsSqlAlchemy(sesion_bd)
    repositorio.crear("Ventas")
    otro = repositorio.crear("Compras")

    with pytest.raises(NombreDuplicadoError, match=f"^Ya existe un workflow llamado «{repetido}»$"):
        repositorio.crear(repetido)
    with pytest.raises(NombreDuplicadoError):
        repositorio.renombrar(otro.id, repetido)

    assert _nombres_guardados() == ["Compras", "Ventas"]


def test_los_nombres_distinguen_tildes(sesion_bd) -> None:
    repositorio = RepositorioWorkflowsSqlAlchemy(sesion_bd)
    repositorio.crear("Cafe")
    repositorio.crear("Café")

    assert _nombres_guardados() == ["Cafe", "Café"]


def test_renombrar_conserva_los_pasos(sesion_bd) -> None:
    workflow = _con_pasos(sesion_bd, "Ventas", "A", "B")

    renombrado = RepositorioWorkflowsSqlAlchemy(sesion_bd).renombrar(workflow.id, "VENTAS")

    assert renombrado == Workflow(id=workflow.id, nombre="VENTAS", pasos=workflow.pasos)
    assert _nombres_guardados() == ["VENTAS"]


@pytest.mark.parametrize(
    "operacion",
    [
        lambda r: r.renombrar(999999, "X"),
        lambda r: r.eliminar(999999),
        lambda r: r.anadir_paso(999999, "X"),
        lambda r: r.reordenar_pasos(999999, []),
    ],
    ids=["renombrar", "eliminar", "anadir_paso", "reordenar"],
)
def test_un_workflow_que_no_existe_lanza_no_encontrado(sesion_bd, operacion) -> None:
    repositorio = RepositorioWorkflowsSqlAlchemy(sesion_bd)

    with pytest.raises(EntidadNoEncontradaError, match="^No existe el workflow con id 999999$"):
        operacion(repositorio)

    assert repositorio.listar() == []


def test_eliminar_borra_sus_pasos_y_deja_sus_tareas_sin_workflow_con_sus_subtareas(
    sesion_bd,
) -> None:
    ventas = _con_pasos(sesion_bd, "Ventas", "A", "B")
    compras = _con_pasos(sesion_bd, "Compras", "C")
    tareas = RepositorioTareasSqlAlchemy(sesion_bd)

    def tarea(workflow: Workflow) -> Tarea:
        return tareas.crear(
            Tarea(
                nombre="T",
                descripcion="d",
                fecha_creacion=datetime(2026, 11, 12, 9, 0, 0),
                workflow=ReferenciaWorkflow(id=workflow.id, nombre=workflow.nombre),
                subtareas=[Subtarea(nombre=p.nombre) for p in workflow.pasos],
            )
        )

    de_ventas, de_compras = tarea(ventas), tarea(compras)

    RepositorioWorkflowsSqlAlchemy(sesion_bd).eliminar(ventas.id)

    assert _nombres_guardados() == ["Compras"]
    assert _filas(ventas.id) == []
    assert _filas(compras.id) == [(1, compras.pasos[0].id, "C")]
    sesion = FabricaSesiones()
    try:
        filas = dict(sesion.execute(select(TareaModelo.id, TareaModelo.workflow_id)).all())
        assert filas == {de_ventas.id: None, de_compras.id: compras.id}
        consulta = select(SubtareaModelo.nombre).where(SubtareaModelo.tarea_id == de_ventas.id)
        assert list(sesion.scalars(consulta.order_by(SubtareaModelo.id))) == ["A", "B"]
    finally:
        sesion.close()


def test_cada_paso_nuevo_va_al_final_de_su_workflow(sesion_bd) -> None:
    ventas = _con_pasos(sesion_bd, "Ventas", "Contacto", "Propuesta", "Cierre")
    compras = _con_pasos(sesion_bd, "Compras", "Pedido")

    a, b, c = _ids(ventas)
    assert [(p.numero, p.nombre) for p in ventas.pasos] == [
        (1, "Contacto"),
        (2, "Propuesta"),
        (3, "Cierre"),
    ]
    assert _filas(ventas.id) == [(1, a, "Contacto"), (2, b, "Propuesta"), (3, c, "Cierre")]
    assert _filas(compras.id) == [(1, compras.pasos[0].id, "Pedido")]


def test_renombrar_un_paso_solo_cambia_su_nombre(sesion_bd) -> None:
    workflow = _con_pasos(sesion_bd, "Ventas", "A", "B")
    a, b = _ids(workflow)

    renombrado = RepositorioWorkflowsSqlAlchemy(sesion_bd).renombrar_paso(workflow.id, b, "Nuevo")

    assert renombrado.pasos == [
        PasoWorkflow(id=a, numero=1, nombre="A"),
        PasoWorkflow(id=b, numero=2, nombre="Nuevo"),
    ]
    assert _filas(workflow.id) == [(1, a, "A"), (2, b, "Nuevo")]


@pytest.mark.parametrize("operacion", ["renombrar", "eliminar"])
def test_un_paso_de_otro_workflow_o_que_no_existe_lanza_no_encontrado(sesion_bd, operacion) -> None:
    ventas = _con_pasos(sesion_bd, "Ventas", "A")
    compras = _con_pasos(sesion_bd, "Compras", "B")
    repositorio = RepositorioWorkflowsSqlAlchemy(sesion_bd)

    for id_paso in (compras.pasos[0].id, 999999):
        mensaje = f"^No existe el paso con id {id_paso} en el workflow con id {ventas.id}$"
        with pytest.raises(EntidadNoEncontradaError, match=mensaje):
            if operacion == "renombrar":
                repositorio.renombrar_paso(ventas.id, id_paso, "X")
            else:
                repositorio.eliminar_paso(ventas.id, id_paso)

    assert _filas(ventas.id) == [(1, ventas.pasos[0].id, "A")]
    assert _filas(compras.id) == [(1, compras.pasos[0].id, "B")]


@pytest.mark.parametrize("posicion", [0, 1, 2, 3])
def test_eliminar_un_paso_renumera_los_siguientes_de_su_workflow(sesion_bd, posicion) -> None:
    workflow = _con_pasos(sesion_bd, "Ventas", "A", "B", "C", "D")
    otro = _con_pasos(sesion_bd, "Compras", "X", "Y")

    resultado = RepositorioWorkflowsSqlAlchemy(sesion_bd).eliminar_paso(
        workflow.id, workflow.pasos[posicion].id
    )

    quedan = [p for i, p in enumerate(workflow.pasos) if i != posicion]
    esperadas = [(n, p.id, p.nombre) for n, p in enumerate(quedan, start=1)]
    assert [(p.numero, p.id, p.nombre) for p in resultado.pasos] == esperadas
    assert _filas(workflow.id) == esperadas
    assert _filas(otro.id) == [(p.numero, p.id, p.nombre) for p in otro.pasos]


def test_tras_eliminar_un_paso_el_nuevo_sigue_al_ultimo(sesion_bd) -> None:
    workflow = _con_pasos(sesion_bd, "Ventas", "A", "B", "C")
    a, b, c = _ids(workflow)
    repositorio = RepositorioWorkflowsSqlAlchemy(sesion_bd)
    repositorio.eliminar_paso(workflow.id, a)

    resultado = repositorio.anadir_paso(workflow.id, "D")

    d = resultado.pasos[-1].id
    assert _filas(workflow.id) == [(1, b, "B"), (2, c, "C"), (3, d, "D")]


def test_reordenar_asigna_los_numeros_segun_el_orden_recibido(sesion_bd) -> None:
    workflow = _con_pasos(sesion_bd, "Ventas", "A", "B", "C", "D")
    otro = _con_pasos(sesion_bd, "Compras", "X", "Y")
    a, b, c, d = _ids(workflow)

    resultado = RepositorioWorkflowsSqlAlchemy(sesion_bd).reordenar_pasos(workflow.id, [d, b, a, c])

    esperadas = [(1, d, "D"), (2, b, "B"), (3, a, "A"), (4, c, "C")]
    assert [(p.numero, p.id, p.nombre) for p in resultado.pasos] == esperadas
    assert _filas(workflow.id) == esperadas
    assert _filas(otro.id) == [(p.numero, p.id, p.nombre) for p in otro.pasos]


def test_reordenar_sin_pasos_con_la_lista_vacia(sesion_bd) -> None:
    workflow = RepositorioWorkflowsSqlAlchemy(sesion_bd).crear("Ventas")

    assert RepositorioWorkflowsSqlAlchemy(sesion_bd).reordenar_pasos(workflow.id, []) == workflow


@pytest.mark.parametrize(
    "orden", ["repetido", "falta", "desconocido", "de otro workflow", "vacio"], ids=lambda o: o
)
def test_reordenar_con_un_orden_invalido_no_cambia_nada(sesion_bd, orden) -> None:
    workflow = _con_pasos(sesion_bd, "Ventas", "A", "B", "C")
    otro = _con_pasos(sesion_bd, "Compras", "X")
    a, b, c = _ids(workflow)
    ids = {
        "repetido": [c, c, a, b],
        "falta": [c, a],
        "desconocido": [c, a, b, 999999],
        "de otro workflow": [c, a, b, otro.pasos[0].id],
        "vacio": [],
    }[orden]
    repositorio = RepositorioWorkflowsSqlAlchemy(sesion_bd)

    with pytest.raises(OrdenDePasosInvalidoError):
        repositorio.reordenar_pasos(workflow.id, ids)

    assert _filas(workflow.id) == [(1, a, "A"), (2, b, "B"), (3, c, "C")]
    # La sesión queda lista para otra operación.
    assert repositorio.anadir_paso(workflow.id, "D").pasos[-1].numero == 4


def test_leer_para_copiar_devuelve_el_workflow_con_sus_pasos_por_numero(sesion_bd) -> None:
    workflow = _con_pasos(sesion_bd, "Ventas", "Contactar", "Proponer", "Cerrar")
    a, b, c = _ids(workflow)
    repositorio = RepositorioWorkflowsSqlAlchemy(sesion_bd)
    repositorio.reordenar_pasos(workflow.id, [c, a, b])

    leido = repositorio.leer_para_copiar(workflow.id)
    sesion_bd.rollback()

    assert [p.nombre for p in leido.pasos] == ["Cerrar", "Contactar", "Proponer"]
    assert (leido.id, leido.nombre) == (workflow.id, "Ventas")


def test_leer_para_copiar_un_workflow_que_no_existe_devuelve_none(sesion_bd) -> None:
    assert RepositorioWorkflowsSqlAlchemy(sesion_bd).leer_para_copiar(999999) is None
    sesion_bd.rollback()


def test_actualizar_una_tarea_guarda_su_workflow_y_anade_las_subtareas_nuevas_al_final(
    sesion_bd,
) -> None:
    ventas = _con_pasos(sesion_bd, "Ventas", "A")
    compras = _con_pasos(sesion_bd, "Compras", "B", "C")
    tareas = RepositorioTareasSqlAlchemy(sesion_bd)
    tarea = tareas.crear(
        Tarea(
            nombre="T",
            descripcion="d",
            fecha_creacion=datetime(2026, 11, 12, 9, 0, 0),
            workflow=ReferenciaWorkflow(id=ventas.id, nombre="Ventas"),
            subtareas=[Subtarea(nombre="A")],
        )
    )
    tarea.workflow = ReferenciaWorkflow(id=compras.id, nombre="Compras")

    actualizada = tareas.actualizar(tarea, [Subtarea(nombre="B"), Subtarea(nombre="C")])

    assert actualizada.workflow == ReferenciaWorkflow(id=compras.id, nombre="Compras")
    assert [s.nombre for s in actualizada.subtareas] == ["A", "B", "C"]
    ids = [s.id for s in actualizada.subtareas]
    assert ids == sorted(ids)
    sesion = FabricaSesiones()
    try:
        assert sesion.scalar(select(TareaModelo.workflow_id)) == compras.id
        consulta = select(SubtareaModelo.nombre, SubtareaModelo.resuelta).order_by(
            SubtareaModelo.id
        )
        assert [tuple(f) for f in sesion.execute(consulta)] == [
            ("A", False),
            ("B", False),
            ("C", False),
        ]
    finally:
        sesion.close()
