from collections.abc import Sequence
from typing import Protocol

from gestor_tareas.dominio.siguientes.entidades import Lista, TareaSiguiente


class RepositorioSiguientes(Protocol):
    """Puerto de persistencia de las dos listas de tareas para después del foco: la
    cola de siguientes y las sugerencias elegidas (``Lista``). Una tarea está como
    mucho en una de ellas.

    Cada operación actúa sobre la lista ``lista`` (por defecto, la cola de
    siguientes) y devuelve esa lista visible (sin las completadas) en su orden y con
    los nombres actuales; las que escriben confirman. Las reglas de
    ``dominio.siguientes.reglas`` se comprueban en la misma transacción que la
    escritura, para que otra petición simultánea no las deje desfasadas.
    """

    def listar(self, lista: Lista = Lista.SIGUIENTES) -> list[TareaSiguiente]:
        """La lista visible en su orden."""
        ...

    def anadir(self, id_tarea: int, lista: Lista = Lista.SIGUIENTES) -> list[TareaSiguiente]:
        """Añade la tarea al final de la lista; si estaba en la otra, la saca de ella;
        si ya estaba en esta, no cambia nada.

        Lanza ``EntidadNoEncontradaError`` si la tarea no existe y
        ``TareaCompletadaEnLaColaError`` si está completada; nada cambia."""
        ...

    def reordenar(
        self, ids: Sequence[int], lista: Lista = Lista.SIGUIENTES
    ) -> list[TareaSiguiente]:
        """Pone las tareas visibles de la lista en el orden de ``ids`` y deja sus
        completadas detrás. Lanza ``OrdenDeLaColaInvalidoError`` si ``ids`` no es
        exactamente esa lista visible; nada cambia."""
        ...

    def quitar(self, id_tarea: int, lista: Lista = Lista.SIGUIENTES) -> list[TareaSiguiente]:
        """Saca la tarea de la lista; si no estaba en ella (o no existe), no cambia
        nada: tampoco la saca de la otra."""
        ...
