from gestor_tareas.dominio.tarea.entidades import Tarea


class RepositorioTareasFalso:
    """Doble de RepositorioTareas en memoria, para tests unitarios de aplicación."""

    def __init__(self) -> None:
        self._tareas: dict[int, Tarea] = {}
        self._siguiente_id = 1

    def crear(self, tarea: Tarea) -> Tarea:
        tarea.id = self._siguiente_id
        self._tareas[tarea.id] = tarea
        self._siguiente_id += 1
        return tarea

    def listar(self) -> list[Tarea]:
        return [self._tareas[id_tarea] for id_tarea in sorted(self._tareas)]
