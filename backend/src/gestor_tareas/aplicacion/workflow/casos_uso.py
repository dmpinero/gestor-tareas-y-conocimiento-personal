"""Casos de uso de los workflows (Ajustes → Workflows).

Cada operación es una transacción completa del repositorio: si choca con otra
petición simultánea, se repite entera.
"""

from gestor_tareas.aplicacion.reintentos import reintentar_si_hay_conflicto
from gestor_tareas.dominio.workflow.entidades import Workflow
from gestor_tareas.dominio.workflow.repositorio import RepositorioWorkflows


class _CasoDeUsoWorkflows:
    def __init__(self, repositorio: RepositorioWorkflows) -> None:
        self._repositorio = repositorio


class ListarWorkflows(_CasoDeUsoWorkflows):
    """Todos los workflows por nombre, con sus pasos por número."""

    def ejecutar(self) -> list[Workflow]:
        return self._repositorio.listar()


class CrearWorkflow(_CasoDeUsoWorkflows):
    """Crea un workflow sin pasos; el nombre no puede repetirse (sin mayúsculas)."""

    def ejecutar(self, nombre: str) -> Workflow:
        return reintentar_si_hay_conflicto(lambda: self._repositorio.crear(nombre))


class RenombrarWorkflow(_CasoDeUsoWorkflows):
    """Cambia el nombre del workflow; sus pasos no cambian."""

    def ejecutar(self, id_workflow: int, nombre: str) -> Workflow:
        return reintentar_si_hay_conflicto(lambda: self._repositorio.renombrar(id_workflow, nombre))


class EliminarWorkflow(_CasoDeUsoWorkflows):
    """Elimina el workflow con sus pasos; sus tareas quedan sin workflow y conservan
    sus subtareas."""

    def ejecutar(self, id_workflow: int) -> None:
        reintentar_si_hay_conflicto(lambda: self._repositorio.eliminar(id_workflow))


class AnadirPaso(_CasoDeUsoWorkflows):
    """Añade un paso al final del workflow (es continuación del último) y devuelve el
    workflow."""

    def ejecutar(self, id_workflow: int, nombre: str) -> Workflow:
        return reintentar_si_hay_conflicto(
            lambda: self._repositorio.anadir_paso(id_workflow, nombre)
        )


class RenombrarPaso(_CasoDeUsoWorkflows):
    """Cambia el nombre de un paso del workflow; su número no cambia."""

    def ejecutar(self, id_workflow: int, id_paso: int, nombre: str) -> Workflow:
        return reintentar_si_hay_conflicto(
            lambda: self._repositorio.renombrar_paso(id_workflow, id_paso, nombre)
        )


class EliminarPaso(_CasoDeUsoWorkflows):
    """Elimina un paso del workflow; los siguientes se renumeran para no dejar huecos."""

    def ejecutar(self, id_workflow: int, id_paso: int) -> Workflow:
        return reintentar_si_hay_conflicto(
            lambda: self._repositorio.eliminar_paso(id_workflow, id_paso)
        )


class ReordenarPasos(_CasoDeUsoWorkflows):
    """Numera los pasos del workflow en el orden recibido (el primero es el 1).

    ``ids`` debe incluir cada paso del workflow exactamente una vez; si no, se lanza
    ``OrdenDePasosInvalidoError`` y no cambia nada. La comprobación la hace el
    repositorio dentro de la misma transacción que la reordenación, para que un
    alta o una baja simultánea no la deje desfasada.
    """

    def ejecutar(self, id_workflow: int, ids: list[int]) -> Workflow:
        return reintentar_si_hay_conflicto(
            lambda: self._repositorio.reordenar_pasos(id_workflow, ids)
        )
