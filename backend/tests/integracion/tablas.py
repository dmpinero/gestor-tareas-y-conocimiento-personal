from sqlalchemy.orm import Session

from gestor_tareas.infraestructura.persistencia import modelos


def vaciar_tablas(sesion: Session) -> None:
    """Vacía el foco de trabajo (con su historial) y las tablas de tareas (con sus vínculos,
    sus subtareas y comentarios, también los de las subtareas), catálogos (también los
    subestados y los códigos de servicio), workflows (con los comentarios de sus pasos) y grupos
    de estados, y las imágenes de los comentarios, respetando el orden de las claves
    ajenas."""
    for tabla in (
        modelos.HistorialFocoModelo.__table__,
        modelos.FocoTrabajoModelo.__table__,
        modelos.ComentarioModelo.__table__,
        modelos.ComentarioSubtareaModelo.__table__,
        modelos.SubtareaModelo.__table__,
        modelos.ComentarioPasoModelo.__table__,
        modelos.PasoWorkflowModelo.__table__,
        modelos.tarea_etiquetas,
        modelos.tarea_personas,
        modelos.OportunidadModelo.__table__,
        modelos.TareaVinculadaModelo.__table__,
        modelos.TareaModelo.__table__,
        modelos.SubestadoModelo.__table__,
        modelos.CodigoServicioModelo.__table__,
        modelos.WorkflowModelo.__table__,
        modelos.EstadoGrupoModelo.__table__,
        modelos.GrupoEstadosModelo.__table__,
        modelos.EtiquetaModelo.__table__,
        modelos.PersonaModelo.__table__,
        modelos.ImagenModelo.__table__,
    ):
        sesion.execute(tabla.delete())
    sesion.commit()
