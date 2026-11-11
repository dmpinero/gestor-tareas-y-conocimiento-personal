from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from gestor_tareas.dominio.comentario.entidades import ComentarioSubtarea
from gestor_tareas.infraestructura.persistencia.modelos import (
    ComentarioSubtareaModelo,
    SubtareaModelo,
    TareaModelo,
)
from gestor_tareas.infraestructura.persistencia.repositorios.conflictos import traducir_conflictos


def _a_entidad(modelo: ComentarioSubtareaModelo, id_tarea: int) -> ComentarioSubtarea:
    return ComentarioSubtarea(
        id=modelo.id,
        id_tarea=id_tarea,
        id_subtarea=modelo.subtarea_id,
        texto=modelo.texto,
        # La columna guarda el instante en UTC sin la zona: se le vuelve a poner.
        creado=modelo.creado.replace(tzinfo=UTC),
        editado=modelo.editado.replace(tzinfo=UTC) if modelo.editado is not None else None,
    )


def _a_columna(instante: datetime) -> datetime:
    """El instante en UTC sin la zona, como lo guarda la columna."""
    return instante.astimezone(UTC).replace(tzinfo=None)


class RepositorioComentariosSubtareaSqlAlchemy:
    def __init__(self, sesion: Session) -> None:
        self._sesion = sesion

    def _existe_subtarea(
        self, id_tarea: int, id_subtarea: int, *, con_bloqueo: bool = False
    ) -> bool:
        consulta = select(SubtareaModelo.id).where(
            SubtareaModelo.id == id_subtarea, SubtareaModelo.tarea_id == id_tarea
        )
        if con_bloqueo:
            # Lectura compartida con bloqueo: la subtarea (y su tarea) no pueden
            # borrarse mientras se añade el comentario, y se ve aunque se haya creado
            # tras la instantánea.
            consulta = consulta.with_for_update(read=True)
        return self._sesion.scalars(consulta).first() is not None

    def crear(self, comentario: ComentarioSubtarea) -> ComentarioSubtarea | None:
        with traducir_conflictos(self._sesion):
            if not self._existe_subtarea(
                comentario.id_tarea, comentario.id_subtarea, con_bloqueo=True
            ):
                self._sesion.rollback()
                return None
            modelo = ComentarioSubtareaModelo(
                subtarea_id=comentario.id_subtarea,
                texto=comentario.texto,
                creado=_a_columna(comentario.creado),
            )
            self._sesion.add(modelo)
            self._sesion.flush()
            # Antes de confirmar, para no volver a leer la fila (ni abrir otra
            # transacción) después.
            guardado = _a_entidad(modelo, comentario.id_tarea)
            self._sesion.commit()
        return guardado

    def listar_de_subtarea(
        self, id_tarea: int, id_subtarea: int
    ) -> list[ComentarioSubtarea] | None:
        try:
            if not self._existe_subtarea(id_tarea, id_subtarea):
                return None
            consulta = (
                select(ComentarioSubtareaModelo)
                .where(ComentarioSubtareaModelo.subtarea_id == id_subtarea)
                .order_by(ComentarioSubtareaModelo.creado, ComentarioSubtareaModelo.id)
            )
            return [_a_entidad(m, id_tarea) for m in self._sesion.scalars(consulta)]
        finally:
            # Solo son consultas: no deja una transacción abierta.
            self._sesion.rollback()

    def existe_tarea(self, id_tarea: int) -> bool:
        existe = (
            self._sesion.scalars(select(TareaModelo.id).where(TareaModelo.id == id_tarea)).first()
            is not None
        )
        # Solo es una consulta: no deja una transacción abierta.
        self._sesion.rollback()
        return existe

    def existe_subtarea(self, id_tarea: int, id_subtarea: int) -> bool:
        existe = self._existe_subtarea(id_tarea, id_subtarea)
        # Solo es una consulta: no deja una transacción abierta.
        self._sesion.rollback()
        return existe

    def _comentario_bloqueado(
        self, id_tarea: int, id_subtarea: int, id_comentario: int
    ) -> ComentarioSubtareaModelo | None:
        """El comentario de esa subtarea de esa tarea, leído con bloqueo, o ``None``
        si no lo tiene.

        La lectura con bloqueo ve lo último confirmado y espera a otra operación en
        curso sobre el mismo comentario (si lo borra, ya no lo encuentra).
        """
        consulta = (
            select(ComentarioSubtareaModelo)
            .join(SubtareaModelo, SubtareaModelo.id == ComentarioSubtareaModelo.subtarea_id)
            .where(
                ComentarioSubtareaModelo.id == id_comentario,
                ComentarioSubtareaModelo.subtarea_id == id_subtarea,
                SubtareaModelo.tarea_id == id_tarea,
            )
            .with_for_update(of=ComentarioSubtareaModelo)
            .execution_options(populate_existing=True)
        )
        return self._sesion.scalars(consulta).one_or_none()

    def editar(
        self, id_tarea: int, id_subtarea: int, id_comentario: int, texto: str, editado: datetime
    ) -> ComentarioSubtarea | None:
        with traducir_conflictos(self._sesion):
            modelo = self._comentario_bloqueado(id_tarea, id_subtarea, id_comentario)
            if modelo is None:
                self._sesion.rollback()
                return None
            modelo.texto = texto
            modelo.editado = _a_columna(editado)
            self._sesion.flush()
            # Antes de confirmar, para no volver a leer la fila después (otra
            # petición podría haberla borrado entre medias).
            guardado = _a_entidad(modelo, id_tarea)
            self._sesion.commit()
        return guardado

    def eliminar(self, id_tarea: int, id_subtarea: int, id_comentario: int) -> bool:
        with traducir_conflictos(self._sesion):
            modelo = self._comentario_bloqueado(id_tarea, id_subtarea, id_comentario)
            if modelo is None:
                self._sesion.rollback()
                return False
            self._sesion.delete(modelo)
            self._sesion.commit()
        return True
