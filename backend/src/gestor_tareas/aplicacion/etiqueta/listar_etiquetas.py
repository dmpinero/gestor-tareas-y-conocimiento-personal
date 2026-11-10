from gestor_tareas.dominio.etiqueta.entidades import Etiqueta
from gestor_tareas.dominio.etiqueta.repositorio import RepositorioEtiquetas


class ListarEtiquetas:
    def __init__(self, repositorio: RepositorioEtiquetas) -> None:
        self._repositorio = repositorio

    def ejecutar(self) -> list[Etiqueta]:
        return self._repositorio.listar()
