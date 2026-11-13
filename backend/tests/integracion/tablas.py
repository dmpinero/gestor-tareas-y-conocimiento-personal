from sqlalchemy.orm import Session

from gestor_tareas.infraestructura.persistencia import modelos


def vaciar_tablas(sesion: Session) -> None:
    """Vacía las tablas de tareas (con sus subtareas y comentarios, también los de
    las subtareas), catálogos, workflows (con los comentarios de sus pasos) y grupos
    de estados, respetando el orden de las claves ajenas."""
    for tabla in (
        modelos.ComentarioModelo.__table__,
        modelos.ComentarioSubtareaModelo.__table__,
        modelos.SubtareaModelo.__table__,
        modelos.ComentarioPasoModelo.__table__,
        modelos.PasoWorkflowModelo.__table__,
        modelos.tarea_etiquetas,
        modelos.tarea_personas,
        modelos.OportunidadModelo.__table__,
        modelos.TareaModelo.__table__,
        modelos.WorkflowModelo.__table__,
        modelos.EstadoGrupoModelo.__table__,
        modelos.GrupoEstadosModelo.__table__,
        modelos.EtiquetaModelo.__table__,
        modelos.PersonaModelo.__table__,
    ):
        sesion.execute(tabla.delete())
    sesion.commit()
