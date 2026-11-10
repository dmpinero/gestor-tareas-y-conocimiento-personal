from sqlalchemy.orm import Session

from gestor_tareas.infraestructura.persistencia import modelos


def vaciar_tablas(sesion: Session) -> None:
    """Vacía las tablas de tareas, catálogos y workflow, respetando el orden de las
    claves ajenas."""
    for tabla in (
        modelos.PasoWorkflowOportunidadModelo.__table__,
        modelos.tarea_etiquetas,
        modelos.tarea_personas,
        modelos.OportunidadModelo.__table__,
        modelos.TareaModelo.__table__,
        modelos.EtiquetaModelo.__table__,
        modelos.PersonaModelo.__table__,
    ):
        sesion.execute(tabla.delete())
    sesion.commit()
