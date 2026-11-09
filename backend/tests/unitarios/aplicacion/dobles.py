from dataclasses import replace

from gestor_tareas.dominio.etiqueta.entidades import Etiqueta
from gestor_tareas.dominio.persona.entidades import Persona
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
        tarea = self._tareas.get(id_tarea)
        # Copia, como hace el repositorio real: modificarla no altera lo guardado.
        return replace(tarea) if tarea is not None else None

    def actualizar(self, tarea: Tarea) -> Tarea:
        assert tarea.id in self._tareas
        self._tareas[tarea.id] = tarea
        return tarea


class _RepositorioCatalogoFalso[T: (Etiqueta, Persona)]:
    """Catálogo en memoria que compara los nombres sin distinguir mayúsculas."""

    def __init__(self, entidad: type[T], nombres_iniciales: tuple[str, ...] = ()) -> None:
        self._entidad = entidad
        self._elementos: list[T] = []
        for nombre in nombres_iniciales:
            self._insertar(nombre)

    def _insertar(self, nombre: str) -> T:
        elemento = self._entidad(id=len(self._elementos) + 1, nombre=nombre)
        self._elementos.append(elemento)
        return elemento

    def listar(self) -> list[T]:
        return sorted(self._elementos, key=lambda e: (e.nombre.casefold(), e.nombre))

    def obtener_o_crear(self, nombres: list[str]) -> list[T]:
        resultado = []
        for nombre in nombres:
            existente = next(
                (e for e in self._elementos if e.nombre.casefold() == nombre.casefold()), None
            )
            resultado.append(existente or self._insertar(nombre))
        return resultado


class RepositorioEtiquetasFalso(_RepositorioCatalogoFalso[Etiqueta]):
    def __init__(self, *nombres_iniciales: str) -> None:
        super().__init__(Etiqueta, nombres_iniciales)


class RepositorioPersonasFalso(_RepositorioCatalogoFalso[Persona]):
    def __init__(self, *nombres_iniciales: str) -> None:
        super().__init__(Persona, nombres_iniciales)
