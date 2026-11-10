from typing import Protocol

from gestor_tareas.dominio.tarea.entidades import Tarea


class RepositorioTareas(Protocol):
    """Puerto de persistencia para Tarea.

    ``tarea.etiquetas`` y ``tarea.asignados`` deben existir ya en sus catálogos
    (ver ``RepositorioEtiquetas.obtener_o_crear``); el repositorio solo enlaza.
    """

    def crear(self, tarea: Tarea) -> Tarea:
        """Guarda una tarea nueva, con el estado ``tarea.completada`` y sus
        ``tarea.pasos_oportunidad`` (a los que asigna id)."""
        ...

    def listar(self) -> list[Tarea]:
        """Devuelve todas las tareas ordenadas por id ascendente."""
        ...

    def obtener_por_id(self, id_tarea: int) -> Tarea | None:
        """Devuelve la tarea con ese id, o ``None`` si no existe."""
        ...

    def actualizar(self, tarea: Tarea) -> Tarea:
        """Guarda los datos de una tarea ya existente (``tarea.id`` debe existir).

        Las etiquetas y personas asignadas sustituyen por completo a las anteriores,
        y lo mismo el tipo y sus datos: si ``tarea.oportunidad`` es ``None``, se
        borran los datos de oportunidad que tuviera.

        El estado completada no cambia (se ignora ``tarea.completada``): solo lo
        cambia ``cambiar_completada``.

        Los pasos de la oportunidad tampoco cambian (se ignora
        ``tarea.pasos_oportunidad``), salvo que la tarea deje de ser oportunidad
        (``tarea.tipo`` distinto de ``TipoTarea.OPORTUNIDAD``): entonces se borran.
        """
        ...

    def cambiar_completada(self, id_tarea: int, completada: bool) -> Tarea | None:
        """Guarda el estado completada de la tarea y la devuelve, o ``None`` si no existe.

        El resto de datos de la tarea no cambia.
        """
        ...

    def cambiar_hecho_paso(self, id_tarea: int, id_paso: int, hecho: bool) -> Tarea | None:
        """Marca el paso de la oportunidad como hecho o pendiente y devuelve la tarea.

        Devuelve ``None`` si la tarea no tiene un paso con ese id (porque la tarea
        no existe, el paso no existe o es de otra tarea). El resto de datos de la
        tarea no cambia.
        """
        ...
