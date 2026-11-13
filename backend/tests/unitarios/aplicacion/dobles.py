from collections.abc import Sequence
from copy import deepcopy
from dataclasses import replace
from datetime import datetime

from gestor_tareas.dominio.comentario.entidades import (
    Comentario,
    ComentarioPaso,
    ComentarioSubtarea,
)
from gestor_tareas.dominio.etiqueta.entidades import Etiqueta
from gestor_tareas.dominio.excepciones import EntidadNoEncontradaError
from gestor_tareas.dominio.grupo_estados.entidades import EstadoGrupo, GrupoEstados
from gestor_tareas.dominio.persona.entidades import Persona
from gestor_tareas.dominio.tarea.entidades import (
    ComentarioInicial,
    ReferenciaEstado,
    Subtarea,
    Tarea,
)
from gestor_tareas.dominio.workflow.entidades import PasoWorkflow, Workflow


class RepositorioTareasFalso:
    """Doble de RepositorioTareas en memoria, para tests unitarios de aplicación."""

    def __init__(self) -> None:
        self._tareas: dict[int, Tarea] = {}
        self._siguiente_id = 1
        self._siguiente_id_subtarea = 1
        # Comentarios con los que nació cada subtarea, por id de subtarea.
        self.comentarios_iniciales: dict[int, list[ComentarioInicial]] = {}

    def crear(self, tarea: Tarea) -> Tarea:
        tarea.id = self._siguiente_id
        # Como el repositorio real: guarda las subtareas en su orden, con ids
        # crecientes, y sin comentarios.
        tarea.subtareas = [self._nueva_subtarea(s, s.resuelta) for s in tarea.subtareas]
        self._tareas[tarea.id] = tarea
        self._siguiente_id += 1
        return deepcopy(tarea)

    def listar(self) -> list[Tarea]:
        return [self._tareas[id_tarea] for id_tarea in sorted(self._tareas)]

    def obtener_por_id(self, id_tarea: int) -> Tarea | None:
        tarea = self._tareas.get(id_tarea)
        # Copia, como hace el repositorio real: modificarla no altera lo guardado.
        return deepcopy(tarea) if tarea is not None else None

    def obtener_para_modificar(self, id_tarea: int) -> Tarea | None:
        return self.obtener_por_id(id_tarea)

    def cambiar_estado(self, id_tarea: int, estado: ReferenciaEstado) -> Tarea:
        tarea = self._tareas.get(id_tarea)
        if tarea is None:
            raise EntidadNoEncontradaError(f"No existe la tarea con id {id_tarea}")
        tarea.estado = replace(estado)
        return deepcopy(tarea)

    def actualizar(self, tarea: Tarea, subtareas_nuevas: Sequence[Subtarea] = ()) -> Tarea:
        assert tarea.id in self._tareas
        guardada = self._tareas[tarea.id]
        # Como el repositorio real, la edición no cambia el estado completada ni las
        # subtareas que ya tiene (tampoco al cambiar el tipo), y añade al final las
        # nuevas.
        tarea.completada = guardada.completada
        tarea.subtareas = deepcopy(guardada.subtareas) + [
            self._nueva_subtarea(s, s.resuelta) for s in subtareas_nuevas
        ]
        self._tareas[tarea.id] = deepcopy(tarea)
        return tarea

    def cambiar_completada(self, id_tarea: int, completada: bool) -> Tarea | None:
        tarea = self._tareas.get(id_tarea)
        if tarea is None:
            return None
        tarea.completada = completada
        return deepcopy(tarea)

    def eliminar(self, id_tarea: int) -> bool:
        return self._tareas.pop(id_tarea, None) is not None

    def _nueva_subtarea(self, subtarea: Subtarea, resuelta: bool) -> Subtarea:
        # Como el repositorio real: guarda sus comentarios iniciales (los cuenta y no
        # los devuelve).
        nueva = replace(
            subtarea,
            id=self._siguiente_id_subtarea,
            resuelta=resuelta,
            comentarios=len(subtarea.comentarios_iniciales),
            comentarios_iniciales=[],
        )
        self.comentarios_iniciales[nueva.id] = deepcopy(subtarea.comentarios_iniciales)
        self._siguiente_id_subtarea += 1
        return nueva

    def anadir_subtarea(self, id_tarea: int, subtarea: Subtarea) -> Tarea | None:
        tarea = self._tareas.get(id_tarea)
        if tarea is None:
            return None
        tarea.subtareas.append(self._nueva_subtarea(subtarea, resuelta=False))
        return deepcopy(tarea)

    def _subtarea(self, id_tarea: int, id_subtarea: int) -> Subtarea | None:
        tarea = self._tareas.get(id_tarea)
        return next((s for s in (tarea.subtareas if tarea else []) if s.id == id_subtarea), None)

    def cambiar_resuelta_subtarea(
        self, id_tarea: int, id_subtarea: int, resuelta: bool
    ) -> Tarea | None:
        subtarea = self._subtarea(id_tarea, id_subtarea)
        if subtarea is None:
            return None
        subtarea.resuelta = resuelta
        return deepcopy(self._tareas[id_tarea])

    def eliminar_subtarea(self, id_tarea: int, id_subtarea: int) -> Tarea | None:
        subtarea = self._subtarea(id_tarea, id_subtarea)
        if subtarea is None:
            return None
        self._tareas[id_tarea].subtareas.remove(subtarea)
        return deepcopy(self._tareas[id_tarea])

    def editar_subtarea(self, id_tarea: int, subtarea: Subtarea) -> Tarea | None:
        assert subtarea.id is not None
        guardada = self._subtarea(id_tarea, subtarea.id)
        if guardada is None:
            return None
        # Como el repositorio real: sustituye nombre, persona y prioridad, y conserva
        # el estado resuelta.
        guardada.nombre = subtarea.nombre
        guardada.asignado = subtarea.asignado
        guardada.prioridad = subtarea.prioridad
        return deepcopy(self._tareas[id_tarea])


class RepositorioComentariosFalso:
    """Doble de RepositorioComentarios en memoria, sobre las tareas de otro doble."""

    def __init__(self, tareas: RepositorioTareasFalso) -> None:
        self._tareas = tareas
        self.comentarios: list[Comentario] = []
        self._siguiente_id = 0

    def crear(self, comentario: Comentario) -> Comentario | None:
        if self._tareas.obtener_por_id(comentario.id_tarea) is None:
            return None
        self._siguiente_id += 1
        guardado = replace(comentario, id=self._siguiente_id)
        self.comentarios.append(guardado)
        return replace(guardado)

    def listar_de_tarea(self, id_tarea: int) -> list[Comentario] | None:
        if self._tareas.obtener_por_id(id_tarea) is None:
            return None
        propios = [c for c in self.comentarios if c.id_tarea == id_tarea]
        return [replace(c) for c in sorted(propios, key=lambda c: (c.creado, c.id))]

    def existe_tarea(self, id_tarea: int) -> bool:
        return self._tareas.obtener_por_id(id_tarea) is not None

    def _indice(self, id_tarea: int, id_comentario: int) -> int | None:
        return next(
            (
                i
                for i, c in enumerate(self.comentarios)
                if c.id == id_comentario and c.id_tarea == id_tarea
            ),
            None,
        )

    def editar(
        self, id_tarea: int, id_comentario: int, texto: str, editado: datetime
    ) -> Comentario | None:
        indice = self._indice(id_tarea, id_comentario)
        if indice is None:
            return None
        self.comentarios[indice] = replace(self.comentarios[indice], texto=texto, editado=editado)
        return replace(self.comentarios[indice])

    def eliminar(self, id_tarea: int, id_comentario: int) -> bool:
        indice = self._indice(id_tarea, id_comentario)
        if indice is None:
            return False
        del self.comentarios[indice]
        return True


class RepositorioComentariosSubtareaFalso:
    """Doble de RepositorioComentariosSubtarea en memoria, sobre las tareas de otro
    doble."""

    def __init__(self, tareas: RepositorioTareasFalso) -> None:
        self._tareas = tareas
        self.comentarios: list[ComentarioSubtarea] = []
        self._siguiente_id = 0

    def existe_tarea(self, id_tarea: int) -> bool:
        return self._tareas.obtener_por_id(id_tarea) is not None

    def existe_subtarea(self, id_tarea: int, id_subtarea: int) -> bool:
        tarea = self._tareas.obtener_por_id(id_tarea)
        return tarea is not None and any(s.id == id_subtarea for s in tarea.subtareas)

    def crear(self, comentario: ComentarioSubtarea) -> ComentarioSubtarea | None:
        if not self.existe_subtarea(comentario.id_tarea, comentario.id_subtarea):
            return None
        self._siguiente_id += 1
        guardado = replace(comentario, id=self._siguiente_id)
        self.comentarios.append(guardado)
        return replace(guardado)

    def listar_de_subtarea(
        self, id_tarea: int, id_subtarea: int
    ) -> list[ComentarioSubtarea] | None:
        if not self.existe_subtarea(id_tarea, id_subtarea):
            return None
        propios = [c for c in self.comentarios if c.id_subtarea == id_subtarea]
        return [replace(c) for c in sorted(propios, key=lambda c: (c.creado, c.id))]

    def _indice(self, id_tarea: int, id_subtarea: int, id_comentario: int) -> int | None:
        if not self.existe_subtarea(id_tarea, id_subtarea):
            return None
        return next(
            (
                i
                for i, c in enumerate(self.comentarios)
                if c.id == id_comentario and c.id_subtarea == id_subtarea
            ),
            None,
        )

    def editar(
        self, id_tarea: int, id_subtarea: int, id_comentario: int, texto: str, editado: datetime
    ) -> ComentarioSubtarea | None:
        indice = self._indice(id_tarea, id_subtarea, id_comentario)
        if indice is None:
            return None
        self.comentarios[indice] = replace(self.comentarios[indice], texto=texto, editado=editado)
        return replace(self.comentarios[indice])

    def eliminar(self, id_tarea: int, id_subtarea: int, id_comentario: int) -> bool:
        indice = self._indice(id_tarea, id_subtarea, id_comentario)
        if indice is None:
            return False
        del self.comentarios[indice]
        return True


class RepositorioWorkflowsFalso:
    """Doble de los workflows en memoria: solo lo que leen los casos de uso de tareas.
    ``workflows`` es {nombre: [pasos en orden]}; los ids empiezan en 300 (workflows) y
    400 (pasos)."""

    def __init__(self, **workflows: list[str]) -> None:
        self.workflows: dict[int, Workflow] = {}
        id_paso = 400
        for id_workflow, (nombre, pasos) in enumerate(workflows.items(), start=300):
            entidades = []
            for numero, nombre_paso in enumerate(pasos, start=1):
                entidades.append(PasoWorkflow(id=id_paso, nombre=nombre_paso, numero=numero))
                id_paso += 1
            self.workflows[id_workflow] = Workflow(id=id_workflow, nombre=nombre, pasos=entidades)
        self.lecturas_para_copiar: list[int] = []
        # Comentarios de los pasos (los gestiona RepositorioComentariosPasoFalso).
        self.comentarios: list[ComentarioPaso] = []

    def paso(self, workflow: str, paso: str) -> PasoWorkflow:
        pasos = self.workflows[self.id_de(workflow)].pasos
        return next(p for p in pasos if p.nombre == paso)

    def id_de(self, nombre: str) -> int:
        return next(w.id for w in self.workflows.values() if w.nombre == nombre)

    def leer_para_copiar(self, id_workflow: int) -> Workflow | None:
        self.lecturas_para_copiar.append(id_workflow)
        workflow = self.workflows.get(id_workflow)
        if workflow is None:
            return None
        # Como el repositorio real: los pasos por número.
        copia = deepcopy(workflow)
        copia.pasos.sort(key=lambda p: p.numero)
        # Y con los textos de los comentarios de cada paso, en su orden.
        for paso in copia.pasos:
            propios = sorted(
                (c for c in self.comentarios if c.id_paso == paso.id),
                key=lambda c: (c.creado, c.id),
            )
            paso.comentarios = len(propios)
            paso.comentarios_para_copiar = [c.texto for c in propios]
        return copia


class RepositorioComentariosPasoFalso:
    """Doble de RepositorioComentariosPaso en memoria, sobre los workflows de otro
    doble (guarda los comentarios en ``workflows.comentarios``)."""

    def __init__(self, workflows: RepositorioWorkflowsFalso) -> None:
        self._workflows = workflows
        self._siguiente_id = 0

    @property
    def comentarios(self) -> list[ComentarioPaso]:
        return self._workflows.comentarios

    def existe_workflow(self, id_workflow: int) -> bool:
        return id_workflow in self._workflows.workflows

    def existe_paso(self, id_workflow: int, id_paso: int) -> bool:
        workflow = self._workflows.workflows.get(id_workflow)
        return workflow is not None and any(p.id == id_paso for p in workflow.pasos)

    def crear(self, comentario: ComentarioPaso) -> ComentarioPaso | None:
        if not self.existe_paso(comentario.id_workflow, comentario.id_paso):
            return None
        self._siguiente_id += 1
        guardado = replace(comentario, id=self._siguiente_id)
        self.comentarios.append(guardado)
        return replace(guardado)

    def listar_de_paso(self, id_workflow: int, id_paso: int) -> list[ComentarioPaso] | None:
        if not self.existe_paso(id_workflow, id_paso):
            return None
        propios = [c for c in self.comentarios if c.id_paso == id_paso]
        return [replace(c) for c in sorted(propios, key=lambda c: (c.creado, c.id))]

    def _indice(self, id_workflow: int, id_paso: int, id_comentario: int) -> int | None:
        if not self.existe_paso(id_workflow, id_paso):
            return None
        return next(
            (
                i
                for i, c in enumerate(self.comentarios)
                if c.id == id_comentario and c.id_paso == id_paso
            ),
            None,
        )

    def editar(
        self, id_workflow: int, id_paso: int, id_comentario: int, texto: str, editado: datetime
    ) -> ComentarioPaso | None:
        indice = self._indice(id_workflow, id_paso, id_comentario)
        if indice is None:
            return None
        self.comentarios[indice] = replace(self.comentarios[indice], texto=texto, editado=editado)
        return replace(self.comentarios[indice])

    def eliminar(self, id_workflow: int, id_paso: int, id_comentario: int) -> bool:
        indice = self._indice(id_workflow, id_paso, id_comentario)
        if indice is None:
            return False
        del self.comentarios[indice]
        return True


class RepositorioGruposEstadosFalso:
    """Doble de los grupos de estados en memoria: solo lo que leen los casos de uso de
    tareas. ``grupos`` es {nombre: [estados en orden]}; los ids empiezan en 100 (grupos)
    y 200 (estados)."""

    def __init__(self, **grupos: list[str]) -> None:
        self.grupos: dict[int, GrupoEstados] = {}
        id_estado = 200
        for id_grupo, (nombre, estados) in enumerate(grupos.items(), start=100):
            entidades = []
            for posicion, nombre_estado in enumerate(estados, start=1):
                entidades.append(EstadoGrupo(id=id_estado, nombre=nombre_estado, posicion=posicion))
                id_estado += 1
            self.grupos[id_grupo] = GrupoEstados(id=id_grupo, nombre=nombre, estados=entidades)
        self.lecturas_para_asignar: list[int] = []

    def id_de(self, nombre: str) -> int:
        return next(g.id for g in self.grupos.values() if g.nombre == nombre)

    def id_estado(self, grupo: str, estado: str) -> int:
        return next(e.id for e in self.grupos[self.id_de(grupo)].estados if e.nombre == estado)

    def leer_para_asignar(self, id_grupo: int) -> GrupoEstados | None:
        self.lecturas_para_asignar.append(id_grupo)
        grupo = self.grupos.get(id_grupo)
        return deepcopy(grupo) if grupo is not None else None


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
