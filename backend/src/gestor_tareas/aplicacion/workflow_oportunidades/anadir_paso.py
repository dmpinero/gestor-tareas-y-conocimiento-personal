from gestor_tareas.aplicacion.reintentos import reintentar_si_hay_conflicto
from gestor_tareas.dominio.workflow_oportunidades.entidades import PasoWorkflowOportunidad
from gestor_tareas.dominio.workflow_oportunidades.repositorio import (
    RepositorioWorkflowOportunidades,
)


class AnadirPaso:
    """Añade un paso al final del workflow: es continuación del último."""

    def __init__(self, repositorio: RepositorioWorkflowOportunidades) -> None:
        self._repositorio = repositorio

    def ejecutar(self, nombre: str) -> PasoWorkflowOportunidad:
        # Si choca con otra petición simultánea sobre el workflow, se repite entera.
        return reintentar_si_hay_conflicto(lambda: self._repositorio.anadir_paso(nombre))
