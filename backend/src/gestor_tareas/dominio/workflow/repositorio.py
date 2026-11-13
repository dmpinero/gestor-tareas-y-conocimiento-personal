from typing import Protocol

from gestor_tareas.dominio.workflow.entidades import Workflow


class RepositorioWorkflows(Protocol):
    """Puerto de persistencia de los workflows y sus pasos.

    Los workflows se devuelven siempre con sus pasos por número. Las operaciones
    que cambian los números (alta, baja y reordenación de pasos) deben mantenerlos
    en 1..n dentro de cada workflow, sin huecos ni repetidos, también con
    peticiones simultáneas.

    Los nombres de workflow son únicos sin distinguir mayúsculas: un nombre
    repetido lanza ``NombreDuplicadoError``. Un workflow que no existe, o un paso
    que no es del workflow indicado, lanza ``EntidadNoEncontradaError``.
    """

    def listar(self) -> list[Workflow]:
        """Todos los workflows, por nombre sin distinguir mayúsculas."""
        ...

    def crear(self, nombre: str) -> Workflow:
        """Guarda un workflow nuevo, sin pasos."""
        ...

    def renombrar(self, id_workflow: int, nombre: str) -> Workflow:
        """Cambia el nombre del workflow; sus pasos no cambian."""
        ...

    def eliminar(self, id_workflow: int) -> None:
        """Elimina el workflow con sus pasos; sus tareas quedan sin workflow y
        conservan sus subtareas."""
        ...

    def anadir_paso(self, id_workflow: int, nombre: str) -> Workflow:
        """Guarda un paso nuevo al final del workflow (número = último + 1) y
        devuelve el workflow."""
        ...

    def renombrar_paso(self, id_workflow: int, id_paso: int, nombre: str) -> Workflow:
        """Cambia el nombre del paso (su número no cambia) y devuelve el workflow."""
        ...

    def eliminar_paso(self, id_workflow: int, id_paso: int) -> Workflow:
        """Elimina el paso, renumera los siguientes y devuelve el workflow."""
        ...

    def reordenar_pasos(self, id_workflow: int, ids: list[int]) -> Workflow:
        """Numera los pasos del workflow según el orden de ``ids`` y devuelve el
        workflow.

        ``ids`` debe incluir cada paso del workflow exactamente una vez (ver
        ``comprobar_nuevo_orden``); si no, lanza ``OrdenDePasosInvalidoError`` y no
        cambia nada.
        """
        ...

    def leer_para_copiar(self, id_workflow: int) -> Workflow | None:
        """El workflow con sus pasos por número, para asignarlo a una tarea y
        copiar sus pasos en ella, o ``None`` si no existe.

        La lectura ve lo último confirmado, nunca ve el workflow a medias de un
        alta, una baja o una reordenación simultánea, e impide que el workflow o
        sus pasos cambien (o se borre) hasta que termine la transacción de quien
        lee: la tarea debe guardarse en esa misma transacción. No confirma.
        """
        ...
