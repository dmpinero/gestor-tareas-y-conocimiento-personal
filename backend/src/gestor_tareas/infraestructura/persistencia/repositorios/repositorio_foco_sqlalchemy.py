from datetime import UTC, datetime

from sqlalchemy import delete, func, literal, select, update
from sqlalchemy.dialects.mysql import insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from gestor_tareas.dominio.excepciones import EntidadNoEncontradaError
from gestor_tareas.dominio.foco.entidades import Foco, PeriodoDeFoco
from gestor_tareas.dominio.foco.errores import subtarea_no_encontrada, tarea_no_encontrada
from gestor_tareas.infraestructura.persistencia.modelos import (
    FocoTrabajoModelo,
    HistorialFocoModelo,
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


def _en_utc_sin_zona(instante: datetime) -> datetime:
    """Las columnas guardan el instante en UTC sin zona."""
    return instante.astimezone(UTC).replace(tzinfo=None)


def _con_zona_utc(instante: datetime | None) -> datetime | None:
    return instante.replace(tzinfo=UTC) if instante is not None else None


def _es_clave_ajena_sin_fila(error: IntegrityError) -> bool:
    argumentos = getattr(error.orig, "args", ())
    return bool(argumentos) and argumentos[0] == _CLAVE_AJENA_SIN_FILA


class RepositorioFocoSqlAlchemy:
    """Adaptador de ``RepositorioFoco`` sobre MySQL: una sola fila con ``id = 1`` y
    el historial, que cambia en la misma transacción que el foco."""

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
            "desde": _en_utc_sin_zona(desde),
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
            # El upsert ha bloqueado la fila del foco: quien fije a la vez espera, y
            # el periodo en curso que cierra es siempre el último.
            self._cerrar_en_curso(desde)
            self._abrir_periodo(id_tarea, id_subtarea, desde)
            foco = self.obtener()
            self._sesion.commit()
        if foco is None:  # La fila se acaba de escribir en la misma transacción.
            raise RuntimeError("El foco recién fijado no se puede leer")
        return foco

    def _no_encontrada(self, id_tarea: int, id_subtarea: int | None) -> EntidadNoEncontradaError:
        """Error de la tarea si ya no existe; si existe, el de la subtarea."""
        existe_tarea = self._sesion.scalar(select(TareaModelo.id).where(TareaModelo.id == id_tarea))
        if existe_tarea is None or id_subtarea is None:
            return tarea_no_encontrada(id_tarea)
        return subtarea_no_encontrada(id_tarea, id_subtarea)

    def _cerrar_en_curso(self, hasta: datetime, *condiciones) -> None:
        self._sesion.execute(
            update(HistorialFocoModelo)
            .where(HistorialFocoModelo.hasta.is_(None), *condiciones)
            .values(hasta=_en_utc_sin_zona(hasta))
        )

    def _abrir_periodo(self, id_tarea: int, id_subtarea: int | None, desde: datetime) -> None:
        """Abre el periodo en curso con los nombres actuales (la tarea y la subtarea
        ya están bloqueadas por la clave ajena del foco)."""
        nombres = (
            select(
                TareaModelo.id,
                literal(id_subtarea),
                TareaModelo.nombre,
                SubtareaModelo.nombre,
                literal(_en_utc_sin_zona(desde)),
            )
            .select_from(TareaModelo)
            .outerjoin(
                SubtareaModelo,
                (SubtareaModelo.id == id_subtarea) & (SubtareaModelo.tarea_id == TareaModelo.id),
            )
            .where(TareaModelo.id == id_tarea)
        )
        self._sesion.execute(
            insert(HistorialFocoModelo).from_select(
                ["tarea_id", "subtarea_id", "tarea_nombre", "subtarea_nombre", "desde"], nombres
            )
        )

    def quitar(self, hasta: datetime) -> None:
        with traducir_conflictos(self._sesion):
            self._sesion.execute(delete(FocoTrabajoModelo).where(FocoTrabajoModelo.id == _ID_FOCO))
            self._cerrar_en_curso(hasta)
            self._sesion.commit()

    def cerrar_periodo_de_tarea(self, id_tarea: int, hasta: datetime) -> None:
        # Sin confirmar: va en la transacción del borrado de la tarea.
        with traducir_conflictos(self._sesion):
            self._cerrar_en_curso(hasta, HistorialFocoModelo.tarea_id == id_tarea)
            self._guardar_ultimos_nombres(HistorialFocoModelo.tarea_id == id_tarea)

    def cerrar_periodo_de_subtarea(self, id_tarea: int, id_subtarea: int, hasta: datetime) -> None:
        # Sin confirmar: va en la transacción del borrado de la subtarea.
        with traducir_conflictos(self._sesion):
            self._cerrar_en_curso(
                hasta,
                HistorialFocoModelo.tarea_id == id_tarea,
                HistorialFocoModelo.subtarea_id == id_subtarea,
            )
            self._guardar_ultimos_nombres(HistorialFocoModelo.subtarea_id == id_subtarea)

    def _guardar_ultimos_nombres(self, *condiciones) -> None:
        """Copia en los periodos indicados los nombres actuales de su tarea y su
        subtarea, para que tras borrarlas el historial muestre el último nombre."""
        nombre_tarea = (
            select(TareaModelo.nombre)
            .where(TareaModelo.id == HistorialFocoModelo.tarea_id)
            .scalar_subquery()
        )
        nombre_subtarea = (
            select(SubtareaModelo.nombre)
            .where(SubtareaModelo.id == HistorialFocoModelo.subtarea_id)
            .scalar_subquery()
        )
        self._sesion.execute(
            update(HistorialFocoModelo)
            .where(*condiciones)
            .values(
                tarea_nombre=func.coalesce(nombre_tarea, HistorialFocoModelo.tarea_nombre),
                subtarea_nombre=func.coalesce(nombre_subtarea, HistorialFocoModelo.subtarea_nombre),
            )
            .execution_options(synchronize_session=False)
        )

    def listar_historial(
        self, desde: datetime | None, hasta: datetime | None
    ) -> list[PeriodoDeFoco]:
        # Nombres actuales mientras existen; si no, los guardados al fijar el foco.
        consulta = (
            select(
                HistorialFocoModelo.id,
                HistorialFocoModelo.tarea_id,
                func.coalesce(TareaModelo.nombre, HistorialFocoModelo.tarea_nombre),
                HistorialFocoModelo.subtarea_id,
                func.coalesce(SubtareaModelo.nombre, HistorialFocoModelo.subtarea_nombre),
                HistorialFocoModelo.desde,
                HistorialFocoModelo.hasta,
            )
            .outerjoin(TareaModelo, TareaModelo.id == HistorialFocoModelo.tarea_id)
            .outerjoin(SubtareaModelo, SubtareaModelo.id == HistorialFocoModelo.subtarea_id)
            .order_by(HistorialFocoModelo.desde.desc(), HistorialFocoModelo.id.desc())
        )
        if desde is not None:
            consulta = consulta.where(HistorialFocoModelo.desde >= _en_utc_sin_zona(desde))
        if hasta is not None:
            consulta = consulta.where(HistorialFocoModelo.desde < _en_utc_sin_zona(hasta))
        return [
            PeriodoDeFoco(
                id=id_periodo,
                tarea_id=id_tarea,
                tarea_nombre=nombre_tarea,
                subtarea_id=id_subtarea,
                subtarea_nombre=nombre_subtarea,
                desde=inicio.replace(tzinfo=UTC),
                hasta=_con_zona_utc(fin),
            )
            for (
                id_periodo,
                id_tarea,
                nombre_tarea,
                id_subtarea,
                nombre_subtarea,
                inicio,
                fin,
            ) in self._sesion.execute(consulta)
        ]
