from datetime import datetime

from gestor_tareas.aplicacion.reintentos import reintentar_si_hay_conflicto
from gestor_tareas.aplicacion.tarea.asignar_grupo_estados import GrupoPedido
from gestor_tareas.aplicacion.tarea.resolver_catalogos import resolver_nombres
from gestor_tareas.dominio.etiqueta.repositorio import RepositorioEtiquetas
from gestor_tareas.dominio.excepciones import EntidadNoEncontradaError
from gestor_tareas.dominio.grupo_estados.repositorio import RepositorioGruposEstados
from gestor_tareas.dominio.persona.repositorio import RepositorioPersonas
from gestor_tareas.dominio.tarea.entidades import Oportunidad, Tarea, TipoTarea
from gestor_tareas.dominio.tarea.repositorio import RepositorioTareas


class ActualizarTarea:
    """Sustituye todos los datos editables de una tarea ya existente.

    Las etiquetas y personas asignadas sustituyen por completo a las anteriores, y
    también el tipo y sus datos (sin tipo, la tarea pierde sus datos de
    oportunidad).

    Las subtareas no cambian, tampoco al cambiar el tipo: una oportunidad que deja
    de serlo conserva las que recibió del workflow, y una tarea que pasa a ser
    oportunidad no recibe ninguna (solo se crean al dar de alta una oportunidad).

    El grupo de estados también se sustituye: con el mismo grupo, la tarea conserva
    su estado; con otro, queda en su primer estado, y sin grupo, sin estado.
    """

    def __init__(
        self,
        repositorio: RepositorioTareas,
        repositorio_etiquetas: RepositorioEtiquetas,
        repositorio_personas: RepositorioPersonas,
        repositorio_grupos: RepositorioGruposEstados,
    ) -> None:
        self._repositorio = repositorio
        self._repositorio_etiquetas = repositorio_etiquetas
        self._repositorio_personas = repositorio_personas
        self._repositorio_grupos = repositorio_grupos

    def ejecutar(
        self,
        id_tarea: int,
        nombre: str,
        descripcion: str,
        fecha_creacion: datetime,
        prioridad: int | None = None,
        fecha_vencimiento: datetime | None = None,
        etiquetas: list[str] | None = None,
        asignados: list[str] | None = None,
        tipo: TipoTarea | None = None,
        oportunidad: Oportunidad | None = None,
        grupo_estados_id: int | None = None,
    ) -> Tarea:
        def guardar() -> Tarea:
            # Primero el grupo y después la tarea (ver GrupoPedido). La tarea se lee
            # con bloqueo: así se conserva el estado que tiene ahora, no el de una
            # lectura anterior.
            grupo = GrupoPedido(self._repositorio_grupos, grupo_estados_id)
            tarea = self._repositorio.obtener_para_modificar(id_tarea)
            if tarea is None:
                raise EntidadNoEncontradaError(f"No existe la tarea con id {id_tarea}")

            tarea.nombre = nombre
            tarea.prioridad = prioridad
            tarea.descripcion = descripcion
            tarea.fecha_creacion = fecha_creacion
            tarea.fecha_vencimiento = fecha_vencimiento
            tarea.etiquetas = resolver_nombres(self._repositorio_etiquetas, etiquetas or [])
            tarea.asignados = resolver_nombres(self._repositorio_personas, asignados or [])
            tarea.tipo = tipo
            tarea.oportunidad = oportunidad
            grupo.asignar(tarea)
            return self._repositorio.actualizar(tarea)

        # Leer la tarea, dar de alta en los catálogos y guardar es una sola
        # transacción: si choca con otra petición simultánea, se repite entera.
        return reintentar_si_hay_conflicto(guardar)
