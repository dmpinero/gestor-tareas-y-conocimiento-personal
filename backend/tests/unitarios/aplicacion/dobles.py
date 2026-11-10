from copy import deepcopy
from dataclasses import replace

from gestor_tareas.dominio.etiqueta.entidades import Etiqueta
from gestor_tareas.dominio.persona.entidades import Persona
from gestor_tareas.dominio.tarea.entidades import Tarea, TipoTarea
from gestor_tareas.dominio.workflow_oportunidades.entidades import PasoWorkflowOportunidad


class RepositorioTareasFalso:
    """Doble de RepositorioTareas en memoria, para tests unitarios de aplicación."""

    def __init__(self) -> None:
        self._tareas: dict[int, Tarea] = {}
        self._siguiente_id = 1
        self._siguiente_id_paso = 1

    def crear(self, tarea: Tarea) -> Tarea:
        tarea.id = self._siguiente_id
        for paso in tarea.pasos_oportunidad:
            paso.id = self._siguiente_id_paso
            self._siguiente_id_paso += 1
        self._tareas[tarea.id] = tarea
        self._siguiente_id += 1
        return deepcopy(tarea)

    def listar(self) -> list[Tarea]:
        return [self._tareas[id_tarea] for id_tarea in sorted(self._tareas)]

    def obtener_por_id(self, id_tarea: int) -> Tarea | None:
        tarea = self._tareas.get(id_tarea)
        # Copia, como hace el repositorio real: modificarla no altera lo guardado.
        return deepcopy(tarea) if tarea is not None else None

    def actualizar(self, tarea: Tarea) -> Tarea:
        assert tarea.id in self._tareas
        guardada = self._tareas[tarea.id]
        # Como el repositorio real, la edición no cambia el estado completada ni los
        # pasos, salvo que la tarea deje de ser oportunidad: entonces los borra.
        tarea.completada = guardada.completada
        tarea.pasos_oportunidad = (
            deepcopy(guardada.pasos_oportunidad) if tarea.tipo is TipoTarea.OPORTUNIDAD else []
        )
        self._tareas[tarea.id] = deepcopy(tarea)
        return tarea

    def cambiar_completada(self, id_tarea: int, completada: bool) -> Tarea | None:
        tarea = self._tareas.get(id_tarea)
        if tarea is None:
            return None
        tarea.completada = completada
        return deepcopy(tarea)

    def cambiar_hecho_paso(self, id_tarea: int, id_paso: int, hecho: bool) -> Tarea | None:
        tarea = self._tareas.get(id_tarea)
        paso = next(
            (p for p in (tarea.pasos_oportunidad if tarea else []) if p.id == id_paso), None
        )
        if paso is None:
            return None
        paso.hecho = hecho
        return deepcopy(tarea)


class RepositorioWorkflowOportunidadesFalso:
    """Doble del workflow en memoria: solo lo que leen los casos de uso de tareas."""

    def __init__(self, *nombres: str) -> None:
        self.pasos = [
            PasoWorkflowOportunidad(id=10 + i, numero=i, nombre=nombre)
            for i, nombre in enumerate(nombres, start=1)
        ]
        self.lecturas_para_copiar = 0

    def leer_pasos_para_copiar(self) -> list[PasoWorkflowOportunidad]:
        self.lecturas_para_copiar += 1
        return [replace(p) for p in sorted(self.pasos, key=lambda p: p.numero)]


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
