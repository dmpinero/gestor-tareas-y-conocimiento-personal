from gestor_tareas.aplicacion.reintentos import reintentar_si_hay_conflicto
from gestor_tareas.aplicacion.workflow_oportunidades.errores import paso_no_encontrado
from gestor_tareas.dominio.workflow_oportunidades.repositorio import (
    RepositorioWorkflowOportunidades,
)


class EliminarPaso:
    """Elimina un paso; los siguientes se renumeran para no dejar huecos."""

    def __init__(self, repositorio: RepositorioWorkflowOportunidades) -> None:
        self._repositorio = repositorio

    def ejecutar(self, id_paso: int) -> None:
        def eliminar() -> None:
            if not self._repositorio.eliminar_paso(id_paso):
                raise paso_no_encontrado(id_paso)

        reintentar_si_hay_conflicto(eliminar)
