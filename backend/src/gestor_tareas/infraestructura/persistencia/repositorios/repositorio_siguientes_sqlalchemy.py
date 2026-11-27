from collections.abc import Sequence

from sqlalchemy import case, delete, false, func, or_, select, update
from sqlalchemy.orm import Session

from gestor_tareas.dominio.foco.errores import subtarea_no_encontrada, tarea_no_encontrada
from gestor_tareas.dominio.siguientes.entidades import ClaveDeEntrada, Lista, TareaSiguiente
from gestor_tareas.dominio.siguientes.reglas import (
    EntradaDeLaCola,
    comprobar_que_se_puede_anadir,
    nuevo_orden_de_la_cola,
)
from gestor_tareas.infraestructura.persistencia.modelos import (
    ColaSiguientesModelo,
    SubtareaModelo,
    TareaModelo,
)
from gestor_tareas.infraestructura.persistencia.repositorios.conflictos import (
    traducir_conflictos,
)

_ORDEN = (ColaSiguientesModelo.posicion, ColaSiguientesModelo.id)


def _es_la_entrada(id_tarea: int, id_subtarea: int | None):
    """Condición de la fila de la entrada: la tarea entera o esa subtarea suya."""
    subtarea = (
        ColaSiguientesModelo.subtarea_id.is_(None)
        if id_subtarea is None
        else ColaSiguientesModelo.subtarea_id == id_subtarea
    )
    return (ColaSiguientesModelo.tarea_id == id_tarea) & subtarea


def _con_tarea_y_subtarea(consulta):
    """Une cada fila con su tarea y, si es de una subtarea, con ella."""
    return consulta.join(TareaModelo, TareaModelo.id == ColaSiguientesModelo.tarea_id).outerjoin(
        SubtareaModelo, SubtareaModelo.id == ColaSiguientesModelo.subtarea_id
    )


# La entrada no se ve: su tarea está completada o su subtarea, resuelta.
_OCULTA = or_(TareaModelo.completada, func.coalesce(SubtareaModelo.resuelta, false()))


class RepositorioSiguientesSqlAlchemy:
    """Adaptador de ``RepositorioSiguientes`` sobre MySQL.

    Las dos listas comparten la tabla ``cola_siguientes`` (la columna ``lista`` dice
    en cuál está cada entrada, de tarea entera o de subtarea). Cada escritura bloquea
    antes todas sus filas (``FOR UPDATE``), así que las escrituras simultáneas, en una
    lista o en otra, se ejecutan una detrás de otra y cada una ve las listas que dejó
    la anterior. Las de tareas completadas o subtareas resueltas se guardan pero no se
    devuelven.
    """

    def __init__(self, sesion: Session) -> None:
        self._sesion = sesion

    def listar(self, lista: Lista = Lista.SIGUIENTES) -> list[TareaSiguiente]:
        consulta = (
            _con_tarea_y_subtarea(
                select(
                    ColaSiguientesModelo.tarea_id,
                    TareaModelo.nombre,
                    ColaSiguientesModelo.subtarea_id,
                    SubtareaModelo.nombre,
                )
            )
            .where(ColaSiguientesModelo.lista == lista.value, ~_OCULTA)
            .order_by(*_ORDEN)
        )
        return [
            TareaSiguiente(
                tarea_id=id_tarea,
                tarea_nombre=nombre_tarea,
                subtarea_id=id_subtarea,
                subtarea_nombre=nombre_subtarea,
            )
            for id_tarea, nombre_tarea, id_subtarea, nombre_subtarea in self._sesion.execute(
                consulta
            )
        ]

    def _bloquear_listas(self, lista: Lista) -> dict[ClaveDeEntrada, tuple[int, EntradaDeLaCola]]:
        """La lista ``lista`` guardada en su orden, por clave, con el id de cada fila.
        Bloquea hasta confirmar las filas de las dos listas (las de las tareas y las
        subtareas no se bloquean)."""
        consulta = (
            _con_tarea_y_subtarea(
                select(
                    ColaSiguientesModelo.id,
                    ColaSiguientesModelo.tarea_id,
                    ColaSiguientesModelo.subtarea_id,
                    ColaSiguientesModelo.lista,
                    _OCULTA,
                )
            )
            .order_by(*_ORDEN)
            .with_for_update(of=ColaSiguientesModelo)
        )
        entradas: dict[ClaveDeEntrada, tuple[int, EntradaDeLaCola]] = {}
        for id_fila, id_tarea, id_subtarea, de_la_lista, oculta in self._sesion.execute(consulta):
            if de_la_lista == lista.value:
                entrada = EntradaDeLaCola(
                    tarea_id=id_tarea, completada=bool(oculta), subtarea_id=id_subtarea
                )
                entradas[entrada.clave] = (id_fila, entrada)
        return entradas

    def _comprobar_que_se_puede_anadir(self, id_tarea: int, id_subtarea: int | None) -> None:
        """Comprueba la tarea y, si se da, su subtarea, con un bloqueo compartido:
        nadie las borra, completa ni resuelve hasta confirmar."""
        completada = self._sesion.scalar(
            select(TareaModelo.completada)
            .where(TareaModelo.id == id_tarea)
            .with_for_update(read=True)
        )
        if completada is None:
            raise tarea_no_encontrada(id_tarea)
        resuelta = False
        if id_subtarea is not None:
            resuelta = self._sesion.scalar(
                select(SubtareaModelo.resuelta)
                .where(SubtareaModelo.id == id_subtarea, SubtareaModelo.tarea_id == id_tarea)
                .with_for_update(read=True)
            )
            if resuelta is None:
                raise subtarea_no_encontrada(id_tarea, id_subtarea)
        comprobar_que_se_puede_anadir(completada, resuelta)

    def anadir(
        self, id_tarea: int, lista: Lista = Lista.SIGUIENTES, id_subtarea: int | None = None
    ) -> list[TareaSiguiente]:
        with traducir_conflictos(self._sesion):
            try:
                self._comprobar_que_se_puede_anadir(id_tarea, id_subtarea)
            except Exception:
                self._sesion.rollback()
                raise
            self._bloquear_listas(lista)
            ultima = self._sesion.scalar(
                select(func.max(ColaSiguientesModelo.posicion)).where(
                    ColaSiguientesModelo.lista == lista.value
                )
            )
            posicion = 0 if ultima is None else ultima + 1
            esta_en = self._sesion.scalar(
                select(ColaSiguientesModelo.lista).where(_es_la_entrada(id_tarea, id_subtarea))
            )
            if esta_en is None:
                self._sesion.add(
                    ColaSiguientesModelo(
                        tarea_id=id_tarea,
                        subtarea_id=id_subtarea,
                        lista=lista.value,
                        posicion=posicion,
                    )
                )
                self._sesion.flush()
            elif esta_en != lista.value:
                # Estaba en la otra lista: pasa al final de esta.
                self._sesion.execute(
                    update(ColaSiguientesModelo)
                    .where(_es_la_entrada(id_tarea, id_subtarea))
                    .values(lista=lista.value, posicion=posicion)
                    .execution_options(synchronize_session=False)
                )
            resultado = self.listar(lista)
            self._sesion.commit()
        return resultado

    def reordenar(
        self, claves: Sequence[ClaveDeEntrada], lista: Lista = Lista.SIGUIENTES
    ) -> list[TareaSiguiente]:
        with traducir_conflictos(self._sesion):
            guardadas = self._bloquear_listas(lista)
            try:
                orden = nuevo_orden_de_la_cola([e for _, e in guardadas.values()], claves)
            except Exception:
                self._sesion.rollback()
                raise
            if orden:
                posiciones = {guardadas[clave][0]: posicion for posicion, clave in enumerate(orden)}
                self._sesion.execute(
                    update(ColaSiguientesModelo)
                    .where(ColaSiguientesModelo.id.in_(posiciones))
                    .values(posicion=case(posiciones, value=ColaSiguientesModelo.id))
                    .execution_options(synchronize_session=False)
                )
            resultado = self.listar(lista)
            self._sesion.commit()
        return resultado

    def quitar(
        self, id_tarea: int, lista: Lista = Lista.SIGUIENTES, id_subtarea: int | None = None
    ) -> list[TareaSiguiente]:
        with traducir_conflictos(self._sesion):
            self._sesion.execute(
                delete(ColaSiguientesModelo).where(
                    _es_la_entrada(id_tarea, id_subtarea),
                    ColaSiguientesModelo.lista == lista.value,
                )
            )
            resultado = self.listar(lista)
            self._sesion.commit()
        return resultado
