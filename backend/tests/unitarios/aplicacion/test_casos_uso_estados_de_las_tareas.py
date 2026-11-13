from datetime import datetime

import pytest

from gestor_tareas.aplicacion.tarea.actualizar_tarea import ActualizarTarea
from gestor_tareas.aplicacion.tarea.cambiar_estado import CambiarEstadoTarea
from gestor_tareas.aplicacion.tarea.crear_tarea import CrearTarea
from gestor_tareas.dominio.excepciones import (
    AsignacionDeEstadoInvalidaError,
    EntidadNoEncontradaError,
)
from gestor_tareas.dominio.tarea.entidades import ReferenciaEstado, ReferenciaGrupoEstados, Tarea
from tests.unitarios.aplicacion.dobles import (
    RepositorioEtiquetasFalso,
    RepositorioGruposEstadosFalso,
    RepositorioPersonasFalso,
    RepositorioTareasFalso,
    RepositorioWorkflowsFalso,
)

_FECHA = datetime(2026, 11, 11, 10, 0, 0)


class _Repositorios:
    def __init__(self) -> None:
        self.tareas = RepositorioTareasFalso()
        self.grupos = RepositorioGruposEstadosFalso(
            Desarrollo=["Pendiente", "En curso", "Hecha"], Ventas=["Nueva", "Ganada"], Vacio=[]
        )

    def crear(self, grupo: str | None = None, id_grupo: int | None = None) -> Tarea:
        if grupo is not None:
            id_grupo = self.grupos.id_de(grupo)
        return CrearTarea(
            self.tareas,
            RepositorioEtiquetasFalso(),
            RepositorioPersonasFalso(),
            RepositorioWorkflowsFalso(),
            self.grupos,
        ).ejecutar(nombre="T", descripcion="d", fecha_creacion=_FECHA, grupo_estados_id=id_grupo)

    def editar(self, id_tarea: int, grupo: str | None = None, id_grupo: int | None = None):
        if grupo is not None:
            id_grupo = self.grupos.id_de(grupo)
        return ActualizarTarea(
            self.tareas,
            RepositorioEtiquetasFalso(),
            RepositorioPersonasFalso(),
            self.grupos,
            RepositorioWorkflowsFalso(),
        ).ejecutar(
            id_tarea, nombre="T", descripcion="d", fecha_creacion=_FECHA, grupo_estados_id=id_grupo
        )

    def mover(self, id_tarea: int, id_estado: int) -> Tarea:
        return CambiarEstadoTarea(self.tareas, self.grupos).ejecutar(id_tarea, id_estado)

    def estado(self, grupo: str, estado: str) -> ReferenciaEstado:
        return ReferenciaEstado(id=self.grupos.id_estado(grupo, estado), nombre=estado)

    def en(self, grupo: str) -> ReferenciaGrupoEstados:
        return ReferenciaGrupoEstados(id=self.grupos.id_de(grupo), nombre=grupo)


def _grupo_y_estado(tarea: Tarea) -> tuple:
    return tarea.grupo_estados, tarea.estado


def test_crear_sin_grupo_deja_la_tarea_sin_grupo_ni_estado_y_no_lee_grupos() -> None:
    repos = _Repositorios()

    tarea = repos.crear()

    assert _grupo_y_estado(tarea) == (None, None)
    assert _grupo_y_estado(repos.tareas.obtener_por_id(tarea.id)) == (None, None)
    assert repos.grupos.lecturas_para_asignar == []


def test_crear_con_grupo_deja_la_tarea_en_su_primer_estado() -> None:
    repos = _Repositorios()

    tarea = repos.crear("Desarrollo")

    esperado = (repos.en("Desarrollo"), repos.estado("Desarrollo", "Pendiente"))
    assert _grupo_y_estado(tarea) == esperado
    assert _grupo_y_estado(repos.tareas.obtener_por_id(tarea.id)) == esperado


@pytest.mark.parametrize(
    ("id_grupo", "mensaje"),
    [
        (999, "No existe el grupo de estados con id 999"),
        (
            102,
            "El grupo de estados «Vacio» no tiene estados: añade al menos uno antes de "
            "asignarlo a una tarea",
        ),
    ],
)
def test_crear_con_un_grupo_que_no_vale_no_guarda_la_tarea(id_grupo, mensaje) -> None:
    repos = _Repositorios()

    with pytest.raises(AsignacionDeEstadoInvalidaError) as error:
        repos.crear(id_grupo=id_grupo)

    assert str(error.value) == mensaje
    assert repos.tareas.listar() == []


def test_editar_asignando_un_grupo_deja_la_tarea_en_su_primer_estado() -> None:
    repos = _Repositorios()
    id_tarea = repos.crear().id

    tarea = repos.editar(id_tarea, "Ventas")

    esperado = (repos.en("Ventas"), repos.estado("Ventas", "Nueva"))
    assert _grupo_y_estado(tarea) == esperado
    assert _grupo_y_estado(repos.tareas.obtener_por_id(id_tarea)) == esperado


def test_editar_manteniendo_el_grupo_conserva_el_estado() -> None:
    repos = _Repositorios()
    id_tarea = repos.crear("Desarrollo").id
    repos.mover(id_tarea, repos.grupos.id_estado("Desarrollo", "Hecha"))

    tarea = repos.editar(id_tarea, "Desarrollo")

    assert _grupo_y_estado(tarea) == (repos.en("Desarrollo"), repos.estado("Desarrollo", "Hecha"))


def test_editar_cambiando_de_grupo_deja_la_tarea_en_el_primer_estado_del_nuevo() -> None:
    repos = _Repositorios()
    id_tarea = repos.crear("Desarrollo").id
    repos.mover(id_tarea, repos.grupos.id_estado("Desarrollo", "En curso"))

    tarea = repos.editar(id_tarea, "Ventas")

    assert _grupo_y_estado(tarea) == (repos.en("Ventas"), repos.estado("Ventas", "Nueva"))


def test_editar_sin_grupo_quita_el_grupo_y_el_estado() -> None:
    repos = _Repositorios()
    id_tarea = repos.crear("Desarrollo").id

    tarea = repos.editar(id_tarea)

    assert _grupo_y_estado(tarea) == (None, None)
    assert _grupo_y_estado(repos.tareas.obtener_por_id(id_tarea)) == (None, None)


def test_editar_con_un_grupo_que_no_vale_no_cambia_la_tarea() -> None:
    repos = _Repositorios()
    id_tarea = repos.crear("Desarrollo").id

    with pytest.raises(AsignacionDeEstadoInvalidaError):
        repos.editar(id_tarea, "Vacio")

    guardada = repos.tareas.obtener_por_id(id_tarea)
    assert _grupo_y_estado(guardada) == (
        repos.en("Desarrollo"),
        repos.estado("Desarrollo", "Pendiente"),
    )


def test_editar_una_tarea_que_no_existe_responde_que_no_existe_aunque_el_grupo_no_valga() -> None:
    repos = _Repositorios()

    with pytest.raises(EntidadNoEncontradaError, match="^No existe la tarea con id 5$"):
        repos.editar(5, id_grupo=999)


def test_editar_lee_el_grupo_antes_que_la_tarea() -> None:
    """Orden de los bloqueos: primero el grupo y después la tarea."""
    repos = _Repositorios()
    id_tarea = repos.crear().id
    orden: list[str] = []
    leer_grupo, leer_tarea = repos.grupos.leer_para_asignar, repos.tareas.obtener_para_modificar
    repos.grupos.leer_para_asignar = lambda i: orden.append("grupo") or leer_grupo(i)
    repos.tareas.obtener_para_modificar = lambda i: orden.append("tarea") or leer_tarea(i)

    repos.editar(id_tarea, "Ventas")

    assert orden == ["grupo", "tarea"]


@pytest.mark.parametrize("destino", ["Hecha", "Pendiente", "En curso"])
def test_mover_lleva_la_tarea_a_cualquier_estado_de_su_grupo(destino) -> None:
    repos = _Repositorios()
    id_tarea = repos.crear("Desarrollo").id
    repos.mover(id_tarea, repos.grupos.id_estado("Desarrollo", "Hecha"))

    tarea = repos.mover(id_tarea, repos.grupos.id_estado("Desarrollo", destino))

    assert _grupo_y_estado(tarea) == (repos.en("Desarrollo"), repos.estado("Desarrollo", destino))
    assert repos.tareas.obtener_por_id(id_tarea).estado == repos.estado("Desarrollo", destino)


def test_mover_una_tarea_que_no_existe_lanza_no_encontrada() -> None:
    repos = _Repositorios()

    with pytest.raises(EntidadNoEncontradaError, match="^No existe la tarea con id 9$"):
        repos.mover(9, repos.grupos.id_estado("Desarrollo", "Hecha"))


def test_mover_una_tarea_sin_grupo_no_la_cambia() -> None:
    repos = _Repositorios()
    id_tarea = repos.crear().id

    with pytest.raises(AsignacionDeEstadoInvalidaError) as error:
        repos.mover(id_tarea, repos.grupos.id_estado("Desarrollo", "Hecha"))

    assert str(error.value) == f"La tarea con id {id_tarea} no tiene grupo de estados"
    assert _grupo_y_estado(repos.tareas.obtener_por_id(id_tarea)) == (None, None)


def test_mover_a_un_estado_de_otro_grupo_no_cambia_la_tarea() -> None:
    repos = _Repositorios()
    id_tarea = repos.crear("Desarrollo").id
    ajeno = repos.grupos.id_estado("Ventas", "Nueva")

    with pytest.raises(AsignacionDeEstadoInvalidaError) as error:
        repos.mover(id_tarea, ajeno)

    assert str(error.value) == (
        f"El estado con id {ajeno} no es del grupo de estados «Desarrollo» de la tarea"
    )
    assert repos.tareas.obtener_por_id(id_tarea).estado == repos.estado("Desarrollo", "Pendiente")
