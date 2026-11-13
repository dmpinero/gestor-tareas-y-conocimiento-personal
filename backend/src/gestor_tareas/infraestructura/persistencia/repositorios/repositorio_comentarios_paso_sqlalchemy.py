"""Comentarios de los pasos de los workflows sobre MySQL.

Las altas, ediciones y borrados bloquean primero la fila del paso en exclusiva
(``SELECT ... FOR UPDATE``), dentro de la transacción. Quien copia los pasos de un
workflow en una tarea los tiene bloqueados en compartido (ver
``RepositorioWorkflowsSqlAlchemy.leer_para_copiar``), así que una operación con los
comentarios de un paso espera a que termine la copia, y la copia espera a que
termine la operación: nunca se copian los comentarios de un paso a medias. El
bloqueo del paso también impide que se borre mientras tanto.
"""

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from gestor_tareas.dominio.comentario.entidades import ComentarioPaso
from gestor_tareas.infraestructura.persistencia.modelos import (
    ComentarioPasoModelo,
    PasoWorkflowModelo,
    WorkflowModelo,
)
from gestor_tareas.infraestructura.persistencia.repositorios.conflictos import traducir_conflictos


def _a_entidad(modelo: ComentarioPasoModelo, id_workflow: int) -> ComentarioPaso:
    return ComentarioPaso(
        id=modelo.id,
        id_workflow=id_workflow,
        id_paso=modelo.paso_id,
        texto=modelo.texto,
        # La columna guarda el instante en UTC sin la zona: se le vuelve a poner.
        creado=modelo.creado.replace(tzinfo=UTC),
        editado=modelo.editado.replace(tzinfo=UTC) if modelo.editado is not None else None,
    )


def _a_columna(instante: datetime) -> datetime:
    """El instante en UTC sin la zona, como lo guarda la columna."""
    return instante.astimezone(UTC).replace(tzinfo=None)


class RepositorioComentariosPasoSqlAlchemy:
    def __init__(self, sesion: Session) -> None:
        self._sesion = sesion

    def _existe_paso(self, id_workflow: int, id_paso: int, *, con_bloqueo: bool = False) -> bool:
        consulta = select(PasoWorkflowModelo.id).where(
            PasoWorkflowModelo.id == id_paso, PasoWorkflowModelo.workflow_id == id_workflow
        )
        if con_bloqueo:
            # Exclusivo: espera a la copia en curso de los pasos y la impide (ver el
            # docstring del módulo), y ve el paso aunque se haya creado tras la
            # instantánea.
            consulta = consulta.with_for_update()
        return self._sesion.scalars(consulta).first() is not None

    def crear(self, comentario: ComentarioPaso) -> ComentarioPaso | None:
        with traducir_conflictos(self._sesion):
            if not self._existe_paso(comentario.id_workflow, comentario.id_paso, con_bloqueo=True):
                self._sesion.rollback()
                return None
            modelo = ComentarioPasoModelo(
                paso_id=comentario.id_paso,
                texto=comentario.texto,
                creado=_a_columna(comentario.creado),
            )
            self._sesion.add(modelo)
            self._sesion.flush()
            # Antes de confirmar, para no volver a leer la fila después.
            guardado = _a_entidad(modelo, comentario.id_workflow)
            self._sesion.commit()
        return guardado

    def listar_de_paso(self, id_workflow: int, id_paso: int) -> list[ComentarioPaso] | None:
        try:
            if not self._existe_paso(id_workflow, id_paso):
                return None
            consulta = (
                select(ComentarioPasoModelo)
                .where(ComentarioPasoModelo.paso_id == id_paso)
                .order_by(ComentarioPasoModelo.creado, ComentarioPasoModelo.id)
            )
            return [_a_entidad(m, id_workflow) for m in self._sesion.scalars(consulta)]
        finally:
            # Solo son consultas: no deja una transacción abierta.
            self._sesion.rollback()

    def existe_workflow(self, id_workflow: int) -> bool:
        consulta = select(WorkflowModelo.id).where(WorkflowModelo.id == id_workflow)
        existe = self._sesion.scalars(consulta).first() is not None
        # Solo es una consulta: no deja una transacción abierta.
        self._sesion.rollback()
        return existe

    def existe_paso(self, id_workflow: int, id_paso: int) -> bool:
        existe = self._existe_paso(id_workflow, id_paso)
        # Solo es una consulta: no deja una transacción abierta.
        self._sesion.rollback()
        return existe

    def _comentario_bloqueado(
        self, id_workflow: int, id_paso: int, id_comentario: int
    ) -> ComentarioPasoModelo | None:
        """El comentario de ese paso de ese workflow, leído con bloqueo, o ``None``
        si no lo tiene. Antes bloquea el paso (ver el docstring del módulo)."""
        if not self._existe_paso(id_workflow, id_paso, con_bloqueo=True):
            return None
        consulta = (
            select(ComentarioPasoModelo)
            .where(
                ComentarioPasoModelo.id == id_comentario,
                ComentarioPasoModelo.paso_id == id_paso,
            )
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        return self._sesion.scalars(consulta).one_or_none()

    def editar(
        self, id_workflow: int, id_paso: int, id_comentario: int, texto: str, editado: datetime
    ) -> ComentarioPaso | None:
        with traducir_conflictos(self._sesion):
            modelo = self._comentario_bloqueado(id_workflow, id_paso, id_comentario)
            if modelo is None:
                self._sesion.rollback()
                return None
            modelo.texto = texto
            modelo.editado = _a_columna(editado)
            self._sesion.flush()
            # Antes de confirmar, para no volver a leer la fila después.
            guardado = _a_entidad(modelo, id_workflow)
            self._sesion.commit()
        return guardado

    def eliminar(self, id_workflow: int, id_paso: int, id_comentario: int) -> bool:
        with traducir_conflictos(self._sesion):
            modelo = self._comentario_bloqueado(id_workflow, id_paso, id_comentario)
            if modelo is None:
                self._sesion.rollback()
                return False
            self._sesion.delete(modelo)
            self._sesion.commit()
        return True
