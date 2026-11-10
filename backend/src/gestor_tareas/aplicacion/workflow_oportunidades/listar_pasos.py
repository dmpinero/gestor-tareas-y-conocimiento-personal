from gestor_tareas.dominio.workflow_oportunidades.entidades import PasoWorkflowOportunidad
from gestor_tareas.dominio.workflow_oportunidades.repositorio import (
    RepositorioWorkflowOportunidades,
)


class ListarPasos:
    def __init__(self, repositorio: RepositorioWorkflowOportunidades) -> None:
        self._repositorio = repositorio

    def ejecutar(self) -> list[PasoWorkflowOportunidad]:
        return self._repositorio.listar_pasos()
