from collections.abc import Callable
from datetime import datetime

from gestor_tareas.aplicacion.comentario.anadir_comentario import (
    ahora_en_utc,
    instante_de_comentario,
)
from gestor_tareas.aplicacion.reintentos import reintentar_si_hay_conflicto
from gestor_tareas.dominio.excepciones import EntidadNoEncontradaError
from gestor_tareas.dominio.foco.repositorio import RepositorioFoco
from gestor_tareas.dominio.tarea.repositorio import RepositorioTareas


class EliminarTarea:
    """Borra una tarea con sus subtareas, sus comentarios y los de sus subtareas.

    Las etiquetas y personas del catálogo se conservan. Con ``foco``, si la tarea (o
    una subtarea suya) estaba en foco, cierra ahora su periodo del historial en la
    misma transacción que el borrado (el foco se quita con la tarea).
    """

    def __init__(
        self,
        repositorio: RepositorioTareas,
        foco: RepositorioFoco | None = None,
        reloj: Callable[[], datetime] = ahora_en_utc,
    ) -> None:
        self._repositorio = repositorio
        self._foco = foco
        self._reloj = reloj

    def ejecutar(self, id_tarea: int) -> None:
        def borrar() -> None:
            if self._foco is not None:
                # Sin confirmar: lo confirma (o lo deshace) el borrado.
                self._foco.cerrar_periodo_de_tarea(id_tarea, instante_de_comentario(self._reloj))
            if not self._repositorio.eliminar(id_tarea):
                raise EntidadNoEncontradaError(f"No existe la tarea con id {id_tarea}")

        # Si choca con otra petición simultánea sobre la misma tarea, se repite.
        reintentar_si_hay_conflicto(borrar)
