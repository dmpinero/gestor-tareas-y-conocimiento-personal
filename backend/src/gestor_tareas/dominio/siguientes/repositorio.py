from collections.abc import Sequence
from typing import Protocol

from gestor_tareas.dominio.siguientes.entidades import TareaSiguiente


class RepositorioSiguientes(Protocol):
    """Puerto de persistencia de la cola de siguientes tareas.

    Cada operación devuelve la cola visible (sin las completadas) en su orden y con
    los nombres actuales; las que escriben confirman. Las reglas de
    ``dominio.siguientes.reglas`` se comprueban en la misma transacción que la
    escritura, para que otra petición simultánea no las deje desfasadas.
    """

    def listar(self) -> list[TareaSiguiente]:
        """La cola visible en su orden."""
        ...

    def anadir(self, id_tarea: int) -> list[TareaSiguiente]:
        """Añade la tarea al final de la cola; si ya estaba, no cambia nada.

        Lanza ``EntidadNoEncontradaError`` si la tarea no existe y
        ``TareaCompletadaEnLaColaError`` si está completada; la cola no cambia."""
        ...

    def reordenar(self, ids: Sequence[int]) -> list[TareaSiguiente]:
        """Pone las tareas visibles en el orden de ``ids`` y deja las completadas
        detrás. Lanza ``OrdenDeLaColaInvalidoError`` si ``ids`` no es exactamente la
        cola visible; la cola no cambia."""
        ...

    def quitar(self, id_tarea: int) -> list[TareaSiguiente]:
        """Saca la tarea de la cola; si no estaba (o no existe), no cambia nada."""
        ...
