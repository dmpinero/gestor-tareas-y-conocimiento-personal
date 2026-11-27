from collections.abc import Sequence
from typing import Protocol

from gestor_tareas.dominio.siguientes.entidades import ClaveDeEntrada, Lista, TareaSiguiente


class RepositorioSiguientes(Protocol):
    """Puerto de persistencia de las dos listas de entradas para después del foco: la
    cola de siguientes y las sugerencias elegidas (``Lista``). Cada entrada es una
    tarea entera o una subtarea suya (``ClaveDeEntrada``) y está como mucho en una de
    las listas.

    Cada operación actúa sobre la lista ``lista`` (por defecto, la cola de
    siguientes) y devuelve esa lista visible (sin las entradas de tareas completadas
    ni de subtareas resueltas) en su orden y con los nombres actuales; las que
    escriben confirman. Las reglas de ``dominio.siguientes.reglas`` se comprueban en
    la misma transacción que la escritura, para que otra petición simultánea no las
    deje desfasadas.
    """

    def listar(self, lista: Lista = Lista.SIGUIENTES) -> list[TareaSiguiente]:
        """La lista visible en su orden."""
        ...

    def anadir(
        self, id_tarea: int, lista: Lista = Lista.SIGUIENTES, id_subtarea: int | None = None
    ) -> list[TareaSiguiente]:
        """Añade la entrada (la tarea entera, o su subtarea ``id_subtarea``) al final
        de la lista; si estaba en la otra, la saca de ella; si ya estaba en esta, no
        cambia nada.

        Lanza ``EntidadNoEncontradaError`` si la tarea no existe o la subtarea no es
        suya, ``TareaCompletadaEnLaColaError`` si la tarea está completada y
        ``SubtareaResueltaEnLaColaError`` si la subtarea está resuelta; nada
        cambia."""
        ...

    def reordenar(
        self, claves: Sequence[ClaveDeEntrada], lista: Lista = Lista.SIGUIENTES
    ) -> list[TareaSiguiente]:
        """Pone las entradas visibles de la lista en el orden de ``claves`` y deja
        detrás las que no se ven. Lanza ``OrdenDeLaColaInvalidoError`` si ``claves``
        no es exactamente esa lista visible; nada cambia."""
        ...

    def quitar(
        self, id_tarea: int, lista: Lista = Lista.SIGUIENTES, id_subtarea: int | None = None
    ) -> list[TareaSiguiente]:
        """Saca la entrada (la tarea entera, o su subtarea ``id_subtarea``) de la
        lista; si no estaba en ella (o no existe), no cambia nada: tampoco la saca de
        la otra. Quitar la tarea entera no quita las entradas de sus subtareas."""
        ...
