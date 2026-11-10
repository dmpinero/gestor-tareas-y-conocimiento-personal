from gestor_tareas.aplicacion.reintentos import reintentar_si_hay_conflicto
from gestor_tareas.dominio.workflow_oportunidades.entidades import PasoWorkflowOportunidad
from gestor_tareas.dominio.workflow_oportunidades.repositorio import (
    RepositorioWorkflowOportunidades,
)


class ReordenarPasos:
    """Numera los pasos del workflow en el orden recibido (el primero es el 1).

    ``ids`` debe incluir cada paso exactamente una vez; si no, se lanza
    ``OrdenDePasosInvalidoError`` y no cambia nada. La comprobación la hace el
    repositorio dentro de la misma transacción que la reordenación, para que un
    alta o una baja simultánea no la deje desfasada.
    """

    def __init__(self, repositorio: RepositorioWorkflowOportunidades) -> None:
        self._repositorio = repositorio

    def ejecutar(self, ids: list[int]) -> list[PasoWorkflowOportunidad]:
        return reintentar_si_hay_conflicto(lambda: self._repositorio.reordenar_pasos(ids))
