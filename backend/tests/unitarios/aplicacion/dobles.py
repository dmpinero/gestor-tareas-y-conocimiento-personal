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

    def obtener_por_id(self, id_tarea: int) -> Tarea | None:
        return self._tareas.get(id_tarea)

    def actualizar(self, tarea: Tarea) -> Tarea:
        assert tarea.id in self._tareas
        self._tareas[tarea.id] = tarea
        return tarea
