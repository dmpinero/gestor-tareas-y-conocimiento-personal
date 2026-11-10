from gestor_tareas.aplicacion.reintentos import reintentar_si_hay_conflicto
from gestor_tareas.aplicacion.workflow_oportunidades.errores import paso_no_encontrado
from gestor_tareas.dominio.workflow_oportunidades.entidades import PasoWorkflowOportunidad
from gestor_tareas.dominio.workflow_oportunidades.repositorio import (
    RepositorioWorkflowOportunidades,
)


class RenombrarPaso:
    """Cambia el nombre de un paso; su número no cambia."""

    def __init__(self, repositorio: RepositorioWorkflowOportunidades) -> None:
        self._repositorio = repositorio

    def ejecutar(self, id_paso: int, nombre: str) -> PasoWorkflowOportunidad:
        def guardar() -> PasoWorkflowOportunidad:
            paso = self._repositorio.renombrar_paso(id_paso, nombre)
            if paso is None:
                raise paso_no_encontrado(id_paso)
            return paso

        return reintentar_si_hay_conflicto(guardar)
