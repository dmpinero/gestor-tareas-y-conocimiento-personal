"""El instante de congelación del contador lo pone el reloj del caso de uso, en UTC y
sin fracción de segundo, como el de los comentarios."""

from datetime import UTC, datetime, timedelta, timezone

from gestor_tareas.aplicacion.tarea.actualizar_tarea import ActualizarTarea
from gestor_tareas.aplicacion.tarea.cambiar_estado import CambiarEstadoTarea
from gestor_tareas.aplicacion.tarea.crear_tarea import CrearTarea
from gestor_tareas.aplicacion.tarea.marcar_completada import MarcarCompletada
from tests.unitarios.aplicacion.dobles import (
    RepositorioEtiquetasFalso,
    RepositorioGruposEstadosFalso,
    RepositorioPersonasFalso,
    RepositorioTareasFalso,
    RepositorioWorkflowsFalso,
)

_FECHA = datetime(2026, 11, 11, 10, 0, 0)
# 14:30:05.123456 en UTC+2, es decir, 12:30:05 en UTC.
_RELOJ = datetime(2026, 11, 17, 14, 30, 5, 123456, tzinfo=timezone(timedelta(hours=2)))
_INSTANTE = datetime(2026, 11, 17, 12, 30, 5, tzinfo=UTC)


def _reloj() -> datetime:
    return _RELOJ


class _Repositorios:
    def __init__(self) -> None:
        self.tareas = RepositorioTareasFalso()
        self.grupos = RepositorioGruposEstadosFalso(Flujo=["TODO", "DONE"], Cerrado=["Done"])

    def crear(self, grupo: str) -> int:
        tarea = CrearTarea(
            self.tareas,
            RepositorioEtiquetasFalso(),
            RepositorioPersonasFalso(),
            RepositorioWorkflowsFalso(),
            self.grupos,
            reloj=_reloj,
        ).ejecutar(
            nombre="T",
            descripcion="d",
            fecha_creacion=_FECHA,
            grupo_estados_id=self.grupos.id_de(grupo),
        )
        assert tarea.id is not None
        return tarea.id

    def editar(self, id_tarea: int, grupo: str | None):
        return ActualizarTarea(
            self.tareas,
            RepositorioEtiquetasFalso(),
            RepositorioPersonasFalso(),
            self.grupos,
            RepositorioWorkflowsFalso(),
            reloj=_reloj,
        ).ejecutar(
            id_tarea,
            nombre="T",
            descripcion="d",
            fecha_creacion=_FECHA,
            grupo_estados_id=self.grupos.id_de(grupo) if grupo else None,
        )


def test_marcar_completada_congela_con_el_instante_del_reloj() -> None:
    repos = _Repositorios()
    id_tarea = repos.crear("Flujo")

    tarea = MarcarCompletada(repos.tareas, reloj=_reloj).ejecutar(id_tarea, True)

    assert tarea.congelada_en == _INSTANTE
    assert repos.tareas.obtener_por_id(id_tarea).congelada_en == _INSTANTE


def test_mover_a_done_congela_con_el_instante_del_reloj() -> None:
    repos = _Repositorios()
    id_tarea = repos.crear("Flujo")

    tarea = CambiarEstadoTarea(repos.tareas, repos.grupos, reloj=_reloj).ejecutar(
        id_tarea, repos.grupos.id_estado("Flujo", "DONE")
    )

    assert tarea.congelada_en == _INSTANTE


def test_crear_en_done_congela_con_el_instante_del_reloj() -> None:
    repos = _Repositorios()

    id_tarea = repos.crear("Cerrado")

    assert repos.tareas.obtener_por_id(id_tarea).congelada_en == _INSTANTE


def test_editar_asignando_un_grupo_que_empieza_en_done_congela_y_quitarlo_descongela() -> None:
    repos = _Repositorios()
    id_tarea = repos.crear("Flujo")

    assert repos.editar(id_tarea, "Cerrado").congelada_en == _INSTANTE
    assert repos.editar(id_tarea, None).congelada_en is None
