from datetime import UTC, datetime

from sqlalchemy import delete, select
from sqlalchemy.dialects.mysql import insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from gestor_tareas.dominio.excepciones import EntidadNoEncontradaError
from gestor_tareas.dominio.foco.entidades import Foco
from gestor_tareas.dominio.foco.errores import subtarea_no_encontrada, tarea_no_encontrada
from gestor_tareas.infraestructura.persistencia.modelos import (
    FocoTrabajoModelo,
    SubtareaModelo,
    TareaModelo,
)
from gestor_tareas.infraestructura.persistencia.repositorios.conflictos import (
    traducir_conflictos,
)

# La única fila de la tabla (ver FocoTrabajoModelo).
_ID_FOCO = 1
# 1452: la clave ajena apunta a una fila que no existe.
_CLAVE_AJENA_SIN_FILA = 1452


def _es_clave_ajena_sin_fila(error: IntegrityError) -> bool:
    argumentos = getattr(error.orig, "args", ())
    return bool(argumentos) and argumentos[0] == _CLAVE_AJENA_SIN_FILA


class RepositorioFocoSqlAlchemy:
    """Adaptador de ``RepositorioFoco`` sobre MySQL: una sola fila con ``id = 1``."""

    def __init__(self, sesion: Session) -> None:
        self._sesion = sesion

    def obtener(self) -> Foco | None:
        fila = self._sesion.execute(
            select(
                FocoTrabajoModelo.tarea_id,
                TareaModelo.nombre,
                FocoTrabajoModelo.subtarea_id,
                SubtareaModelo.nombre,
                FocoTrabajoModelo.desde,
            )
            .join(TareaModelo, TareaModelo.id == FocoTrabajoModelo.tarea_id)
            .outerjoin(SubtareaModelo, SubtareaModelo.id == FocoTrabajoModelo.subtarea_id)
            .where(FocoTrabajoModelo.id == _ID_FOCO)
        ).first()
        if fila is None:
            return None
        id_tarea, nombre_tarea, id_subtarea, nombre_subtarea, desde = fila
        return Foco(
            tarea_id=id_tarea,
            tarea_nombre=nombre_tarea,
            subtarea_id=id_subtarea,
            subtarea_nombre=nombre_subtarea,
            desde=desde.replace(tzinfo=UTC),
        )

    def fijar(self, id_tarea: int, id_subtarea: int | None, desde: datetime) -> Foco:
        valores = {
            "tarea_id": id_tarea,
            "subtarea_id": id_subtarea,
            # La columna guarda el instante en UTC sin zona.
            "desde": desde.astimezone(UTC).replace(tzinfo=None),
        }
        sentencia = insert(FocoTrabajoModelo).values(id=_ID_FOCO, **valores)
        with traducir_conflictos(self._sesion):
            try:
                # Alta o sustitución de la única fila en una sola sentencia.
                self._sesion.execute(sentencia.on_duplicate_key_update(**valores))
            except IntegrityError as error:
                self._sesion.rollback()
                if not _es_clave_ajena_sin_fila(error):
                    raise
                raise self._no_encontrada(id_tarea, id_subtarea) from error
            foco = self.obtener()
            self._sesion.commit()
        assert foco is not None
        return foco

    def _no_encontrada(self, id_tarea: int, id_subtarea: int | None) -> EntidadNoEncontradaError:
        """Error de la tarea si ya no existe; si existe, el de la subtarea."""
        existe_tarea = self._sesion.scalar(select(TareaModelo.id).where(TareaModelo.id == id_tarea))
        if existe_tarea is None or id_subtarea is None:
            return tarea_no_encontrada(id_tarea)
        return subtarea_no_encontrada(id_tarea, id_subtarea)

    def quitar(self) -> None:
        with traducir_conflictos(self._sesion):
            self._sesion.execute(delete(FocoTrabajoModelo).where(FocoTrabajoModelo.id == _ID_FOCO))
            self._sesion.commit()
