from gestor_tareas.dominio.persona.entidades import Persona
from gestor_tareas.dominio.persona.repositorio import RepositorioPersonas


class ListarPersonas:
    def __init__(self, repositorio: RepositorioPersonas) -> None:
        self._repositorio = repositorio

    def ejecutar(self) -> list[Persona]:
        return self._repositorio.listar()
