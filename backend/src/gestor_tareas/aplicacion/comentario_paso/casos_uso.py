"""Casos de uso de los comentarios de los pasos de los workflows (Ajustes →
Workflows), con las mismas reglas que los de las tareas y subtareas.

Un paso de otro workflow se trata como si no existiera, y un comentario de otro paso
también. Si una operación choca con otra petición simultánea, se repite entera.
"""

from collections.abc import Callable
from datetime import datetime

from gestor_tareas.aplicacion.comentario.anadir_comentario import (
    ahora_en_utc,
    instante_de_comentario,
)
from gestor_tareas.aplicacion.reintentos import reintentar_si_hay_conflicto
from gestor_tareas.dominio.comentario.entidades import ComentarioPaso
from gestor_tareas.dominio.comentario.repositorio import RepositorioComentariosPaso
from gestor_tareas.dominio.excepciones import EntidadNoEncontradaError
from gestor_tareas.dominio.workflow.errores import paso_no_encontrado, workflow_no_encontrado


def _paso_no_encontrado(
    repositorio: RepositorioComentariosPaso, id_workflow: int, id_paso: int
) -> EntidadNoEncontradaError:
    """Error del workflow si no existe; si existe, el del paso que no tiene."""
    if not repositorio.existe_workflow(id_workflow):
        return workflow_no_encontrado(id_workflow)
    return paso_no_encontrado(id_workflow, id_paso)


def _comentario_no_encontrado(
    repositorio: RepositorioComentariosPaso, id_workflow: int, id_paso: int, id_comentario: int
) -> EntidadNoEncontradaError:
    """Error del workflow o del paso si no existen; si existen, el del comentario que
    no tiene el paso."""
    if not repositorio.existe_paso(id_workflow, id_paso):
        return _paso_no_encontrado(repositorio, id_workflow, id_paso)
    return EntidadNoEncontradaError(
        f"No existe el comentario con id {id_comentario} en el paso con id {id_paso}"
    )


class ListarComentariosPaso:
    """Devuelve el histórico de comentarios de un paso en orden cronológico."""

    def __init__(self, repositorio: RepositorioComentariosPaso) -> None:
        self._repositorio = repositorio

    def ejecutar(self, id_workflow: int, id_paso: int) -> list[ComentarioPaso]:
        comentarios = self._repositorio.listar_de_paso(id_workflow, id_paso)
        if comentarios is None:
            raise _paso_no_encontrado(self._repositorio, id_workflow, id_paso)
        return comentarios


class AnadirComentarioPaso:
    """Añade un comentario al histórico de un paso existente. El instante de alta lo
    pone la aplicación, en UTC y sin fracción de segundo."""

    def __init__(
        self,
        repositorio: RepositorioComentariosPaso,
        reloj: Callable[[], datetime] = ahora_en_utc,
    ) -> None:
        self._repositorio = repositorio
        self._reloj = reloj

    def ejecutar(self, id_workflow: int, id_paso: int, texto: str) -> ComentarioPaso:
        def guardar() -> ComentarioPaso:
            comentario = self._repositorio.crear(
                ComentarioPaso(
                    id_workflow=id_workflow,
                    id_paso=id_paso,
                    texto=texto,
                    creado=instante_de_comentario(self._reloj),
                )
            )
            if comentario is None:
                raise _paso_no_encontrado(self._repositorio, id_workflow, id_paso)
            return comentario

        return reintentar_si_hay_conflicto(guardar)


class EditarComentarioPaso:
    """Sustituye el texto de un comentario de un paso y lo marca como editado. El
    instante de edición lo pone la aplicación, en UTC y sin fracción de segundo; el
    de alta no cambia."""

    def __init__(
        self,
        repositorio: RepositorioComentariosPaso,
        reloj: Callable[[], datetime] = ahora_en_utc,
    ) -> None:
        self._repositorio = repositorio
        self._reloj = reloj

    def ejecutar(
        self, id_workflow: int, id_paso: int, id_comentario: int, texto: str
    ) -> ComentarioPaso:
        def guardar() -> ComentarioPaso:
            comentario = self._repositorio.editar(
                id_workflow, id_paso, id_comentario, texto, instante_de_comentario(self._reloj)
            )
            if comentario is None:
                raise _comentario_no_encontrado(
                    self._repositorio, id_workflow, id_paso, id_comentario
                )
            return comentario

        return reintentar_si_hay_conflicto(guardar)


class EliminarComentarioPaso:
    """Borra un comentario del histórico de un paso."""

    def __init__(self, repositorio: RepositorioComentariosPaso) -> None:
        self._repositorio = repositorio

    def ejecutar(self, id_workflow: int, id_paso: int, id_comentario: int) -> None:
        def borrar() -> None:
            if not self._repositorio.eliminar(id_workflow, id_paso, id_comentario):
                raise _comentario_no_encontrado(
                    self._repositorio, id_workflow, id_paso, id_comentario
                )

        reintentar_si_hay_conflicto(borrar)
