from collections.abc import Sequence
from typing import Protocol

from gestor_tareas.dominio.tarea.entidades import ReferenciaEstado, Subtarea, Tarea


class RepositorioTareas(Protocol):
    """Puerto de persistencia para Tarea.

    ``tarea.etiquetas`` y ``tarea.asignados`` deben existir ya en sus catálogos
    (ver ``RepositorioEtiquetas.obtener_o_crear``); el repositorio solo enlaza.
    """

    def crear(self, tarea: Tarea) -> Tarea:
        """Guarda una tarea nueva, con el estado ``tarea.completada``, su
        ``tarea.workflow`` (que debe existir) y sus ``tarea.subtareas`` en ese orden
        (a las que asigna id; su ``asignado`` debe existir ya en el catálogo de
        personas, y se ignora ``comentarios``)."""
        ...

    def listar(self) -> list[Tarea]:
        """Devuelve todas las tareas ordenadas por id ascendente."""
        ...

    def obtener_por_id(self, id_tarea: int) -> Tarea | None:
        """Devuelve la tarea con ese id, o ``None`` si no existe."""
        ...

    def obtener_para_modificar(self, id_tarea: int) -> Tarea | None:
        """Devuelve la tarea con ese id, o ``None`` si no existe, para modificarla.

        La lectura ve lo último confirmado e impide que otra petición la cambie o la
        borre hasta que termine la transacción de quien lee, que debe guardar los
        cambios en ella. No confirma.
        """
        ...

    def eliminar(self, id_tarea: int) -> bool:
        """Borra la tarea con sus datos de tipo, sus enlaces con los catálogos, sus
        subtareas, sus comentarios y los de sus subtareas, todo en una transacción.
        Las etiquetas y personas del catálogo se conservan. Devuelve ``False`` si la
        tarea no existe."""
        ...

    def actualizar(self, tarea: Tarea, subtareas_nuevas: Sequence[Subtarea] = ()) -> Tarea:
        """Guarda los datos de una tarea ya existente (``tarea.id`` debe existir).

        Las etiquetas y personas asignadas sustituyen por completo a las anteriores,
        y lo mismo el tipo y sus datos: si ``tarea.oportunidad`` es ``None``, se
        borran los datos de oportunidad que tuviera.

        El estado completada no cambia (se ignora ``tarea.completada``): solo lo
        cambia ``cambiar_completada``. El grupo de estados y el estado sí se
        guardan: ``tarea.estado`` debe ser un estado de ``tarea.grupo_estados``.
        También el workflow (``tarea.workflow``), que debe existir.

        Las subtareas que ya tiene no cambian (se ignora ``tarea.subtareas``),
        tampoco al cambiar el tipo de la tarea. ``subtareas_nuevas`` se añaden,
        pendientes y en ese orden, después de las que ya tiene (su ``asignado``
        debe existir ya en el catálogo de personas).

        Lanza ``EntidadNoEncontradaError`` si otra petición ha borrado la tarea
        mientras tanto.
        """
        ...

    def cambiar_completada(self, id_tarea: int, completada: bool) -> Tarea | None:
        """Guarda el estado completada de la tarea y la devuelve, o ``None`` si no existe.

        El resto de datos de la tarea no cambia.
        """
        ...

    def cambiar_estado(self, id_tarea: int, estado: ReferenciaEstado) -> Tarea:
        """Guarda el estado de la tarea, que debe ser de su grupo, y la devuelve.

        El resto de datos de la tarea no cambia. Lanza ``EntidadNoEncontradaError``
        si otra petición ha borrado la tarea mientras tanto.
        """
        ...

    def anadir_subtarea(self, id_tarea: int, subtarea: Subtarea) -> Tarea | None:
        """Añade la subtarea, pendiente, al final de las de la tarea y devuelve la tarea.

        ``subtarea.asignado`` debe existir ya en el catálogo de personas (ver
        ``RepositorioPersonas.obtener_o_crear``). Devuelve ``None`` si la tarea no
        existe, y entonces deshace la transacción (también las altas en el
        catálogo hechas en ella). El resto de datos de la tarea no cambia.
        """
        ...

    def cambiar_resuelta_subtarea(
        self, id_tarea: int, id_subtarea: int, resuelta: bool
    ) -> Tarea | None:
        """Marca la subtarea como resuelta o pendiente y devuelve la tarea.

        Devuelve ``None`` si la tarea no tiene una subtarea con ese id (porque la
        tarea no existe, la subtarea no existe o es de otra tarea). El resto de
        datos de la tarea no cambia.
        """
        ...

    def editar_subtarea(self, id_tarea: int, subtarea: Subtarea) -> Tarea | None:
        """Sustituye el nombre, la persona asignada y la prioridad de la subtarea
        ``subtarea.id`` y devuelve la tarea.

        Es un reemplazo completo: ``asignado`` o ``prioridad`` a ``None`` los vacían.
        El estado resuelta no cambia (se ignora ``subtarea.resuelta``).
        ``subtarea.asignado`` debe existir ya en el catálogo de personas. Devuelve
        ``None`` si la tarea no tiene una subtarea con ese id (como en
        ``cambiar_resuelta_subtarea``), y entonces deshace la transacción (también
        las altas en el catálogo hechas en ella). El resto de datos de la tarea no
        cambia.
        """
        ...

    def eliminar_subtarea(self, id_tarea: int, id_subtarea: int) -> Tarea | None:
        """Borra la subtarea y devuelve la tarea, o ``None`` si la tarea no tiene
        una subtarea con ese id (como en ``cambiar_resuelta_subtarea``)."""
        ...
