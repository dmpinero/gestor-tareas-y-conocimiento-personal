from typing import Protocol

from gestor_tareas.dominio.workflow_oportunidades.entidades import PasoWorkflowOportunidad


class RepositorioWorkflowOportunidades(Protocol):
    """Puerto de persistencia de los pasos del workflow de las oportunidades.

    Las operaciones que cambian los números (alta, baja y reordenación) deben
    mantenerlos en 1..n, sin huecos ni repetidos, también con peticiones
    simultáneas.
    """

    def listar_pasos(self) -> list[PasoWorkflowOportunidad]:
        """Devuelve todos los pasos ordenados por número."""
        ...

    def leer_pasos_para_copiar(self) -> list[PasoWorkflowOportunidad]:
        """Devuelve todos los pasos ordenados por número, para copiarlos en una tarea.

        La lectura nunca ve el workflow a medias de un alta, una baja o una
        reordenación simultánea, y las impide hasta que termine la transacción de
        quien lee: la copia debe guardarse en esa misma transacción.
        """
        ...

    def anadir_paso(self, nombre: str) -> PasoWorkflowOportunidad:
        """Guarda un paso nuevo al final del workflow (número = último + 1)."""
        ...

    def renombrar_paso(self, id_paso: int, nombre: str) -> PasoWorkflowOportunidad | None:
        """Cambia el nombre del paso y lo devuelve, o ``None`` si no existe.

        El número del paso no cambia.
        """
        ...

    def eliminar_paso(self, id_paso: int) -> bool:
        """Elimina el paso y renumera los siguientes; ``False`` si no existe."""
        ...

    def reordenar_pasos(self, ids: list[int]) -> list[PasoWorkflowOportunidad]:
        """Numera los pasos según el orden de ``ids`` y los devuelve en ese orden.

        ``ids`` debe incluir cada paso exactamente una vez (ver
        ``comprobar_nuevo_orden``); si no, lanza ``OrdenDePasosInvalidoError`` y no
        cambia nada.
        """
        ...
