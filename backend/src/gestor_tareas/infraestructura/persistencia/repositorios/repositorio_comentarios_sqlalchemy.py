from datetime import UTC

from sqlalchemy import select
from sqlalchemy.orm import Session

from gestor_tareas.dominio.comentario.entidades import Comentario
from gestor_tareas.infraestructura.persistencia.modelos import ComentarioModelo, TareaModelo
from gestor_tareas.infraestructura.persistencia.repositorios.conflictos import traducir_conflictos


def _a_entidad(modelo: ComentarioModelo) -> Comentario:
    return Comentario(
        id=modelo.id,
        id_tarea=modelo.tarea_id,
        texto=modelo.texto,
        # La columna guarda el instante en UTC sin la zona: se le vuelve a poner.
        creado=modelo.creado.replace(tzinfo=UTC),
    )


class RepositorioComentariosSqlAlchemy:
    def __init__(self, sesion: Session) -> None:
        self._sesion = sesion

    def _existe_tarea(self, id_tarea: int, *, con_bloqueo: bool = False) -> bool:
        consulta = select(TareaModelo.id).where(TareaModelo.id == id_tarea)
        if con_bloqueo:
            # Lectura compartida con bloqueo: la tarea no puede borrarse mientras se
            # añade el comentario, y se ve aunque se haya creado tras la instantánea.
            consulta = consulta.with_for_update(read=True)
        return self._sesion.scalars(consulta).first() is not None

    def crear(self, comentario: Comentario) -> Comentario | None:
        with traducir_conflictos(self._sesion):
            if not self._existe_tarea(comentario.id_tarea, con_bloqueo=True):
                self._sesion.rollback()
                return None
            modelo = ComentarioModelo(
                tarea_id=comentario.id_tarea,
                texto=comentario.texto,
                creado=comentario.creado.astimezone(UTC).replace(tzinfo=None),
            )
            self._sesion.add(modelo)
            self._sesion.flush()
            # Antes de confirmar, para no volver a leer la fila (ni abrir otra
            # transacción) después.
            guardado = _a_entidad(modelo)
            self._sesion.commit()
        return guardado

    def listar_de_tarea(self, id_tarea: int) -> list[Comentario] | None:
        if not self._existe_tarea(id_tarea):
            return None
        consulta = (
            select(ComentarioModelo)
            .where(ComentarioModelo.tarea_id == id_tarea)
            .order_by(ComentarioModelo.creado, ComentarioModelo.id)
        )
        return [_a_entidad(m) for m in self._sesion.scalars(consulta)]
