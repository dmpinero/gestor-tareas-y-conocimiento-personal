from dataclasses import dataclass, field


@dataclass
class EstadoGrupo:
    """Estado de un grupo de estados.

    ``posicion`` es su lugar en el grupo (1..n, sin huecos): solo define el orden de
    las columnas del tablero, porque una tarea puede pasar de cualquier estado del
    grupo a cualquier otro. La asigna el sistema al dar de alta el estado (va al
    final) y la recalcula al eliminar o reordenar.

    ``tareas`` es el número de tareas que están en el estado; solo se lee.
    """

    nombre: str
    posicion: int | None = None
    tareas: int = 0
    id: int | None = None


@dataclass
class GrupoEstados:
    """Conjunto de estados con nombre que se asigna a las tareas.

    Las tareas apuntan al grupo: los cambios en sus estados se reflejan en ellas.
    ``estados`` va por posición y ``tareas`` es el número de tareas del grupo; solo
    se lee.
    """

    nombre: str
    estados: list[EstadoGrupo] = field(default_factory=list)
    tareas: int = 0
    id: int | None = None

    def estado(self, id_estado: int) -> EstadoGrupo | None:
        """El estado del grupo con ese id, o ``None`` si no es de este grupo."""
        return next((e for e in self.estados if e.id == id_estado), None)
