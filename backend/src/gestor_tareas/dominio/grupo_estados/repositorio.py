from datetime import datetime
from typing import Protocol

from gestor_tareas.dominio.grupo_estados.entidades import GrupoEstados


class RepositorioGruposEstados(Protocol):
    """Puerto de persistencia de los grupos de estados.

    Los grupos se devuelven siempre completos: sus estados por posición y el número
    de tareas del grupo y de cada estado. Las operaciones que cambian las posiciones
    (alta, baja y reordenación de estados) deben mantenerlas en 1..n, sin huecos ni
    repetidas, también con peticiones simultáneas.

    Los nombres de grupo son únicos entre los grupos, y los de estado dentro de su
    grupo, sin distinguir mayúsculas: un nombre repetido lanza
    ``NombreDuplicadoError``. Un grupo o un estado que no existe (o un estado de otro
    grupo) lanza ``EntidadNoEncontradaError``.
    """

    def listar(self) -> list[GrupoEstados]:
        """Todos los grupos, por nombre sin distinguir mayúsculas."""
        ...

    def crear(self, nombre: str) -> GrupoEstados:
        """Guarda un grupo nuevo, sin estados."""
        ...

    def renombrar(self, id_grupo: int, nombre: str) -> GrupoEstados:
        """Cambia el nombre del grupo; sus estados no cambian."""
        ...

    def eliminar(self, id_grupo: int, ahora: datetime) -> None:
        """Elimina el grupo con sus estados; sus tareas quedan sin grupo ni estado.

        Las que estaban en DONE sin estar completadas dejan de estar congeladas (ver
        ``Tarea.ajustar_congelacion``; ``ahora`` es el instante del cambio)."""
        ...

    def anadir_estado(self, id_grupo: int, nombre: str) -> GrupoEstados:
        """Añade un estado al final del grupo (posición = última + 1)."""
        ...

    def renombrar_estado(
        self, id_grupo: int, id_estado: int, nombre: str, ahora: datetime
    ) -> GrupoEstados:
        """Cambia el nombre del estado; su posición no cambia.

        Si pasa a llamarse DONE o deja de llamarse así, sus tareas se congelan o
        dejan de estarlo en la misma transacción (ver ``Tarea.ajustar_congelacion``;
        ``ahora`` es el instante del cambio)."""
        ...

    def eliminar_estado(
        self, id_grupo: int, id_estado: int, mover_a: int | None, ahora: datetime
    ) -> GrupoEstados:
        """Elimina el estado y renumera los siguientes.

        Antes mueve sus tareas al estado ``mover_a``, en la misma transacción, y con
        ello se congelan o dejan de estarlo (ver ``Tarea.ajustar_congelacion``;
        ``ahora`` es el instante del cambio). Lo que valga como destino lo decide
        ``comprobar_destino_de_las_tareas``, con el número de tareas leído en esa
        transacción; si no vale, no cambia nada.
        """
        ...

    def reordenar_estados(self, id_grupo: int, ids: list[int]) -> GrupoEstados:
        """Da a los estados las posiciones según el orden de ``ids``.

        ``ids`` debe incluir cada estado del grupo exactamente una vez (ver
        ``comprobar_nuevo_orden``); si no, lanza ``OrdenDeEstadosInvalidoError`` y no
        cambia nada.
        """
        ...

    def leer_para_asignar(self, id_grupo: int) -> GrupoEstados | None:
        """El grupo con sus estados, para asignarlo a una tarea, o ``None`` si no existe.

        La lectura ve lo último confirmado e impide que el grupo o sus estados
        cambien hasta que termine la transacción de quien lee: la tarea debe
        guardarse en esa misma transacción. No confirma.
        """
        ...
