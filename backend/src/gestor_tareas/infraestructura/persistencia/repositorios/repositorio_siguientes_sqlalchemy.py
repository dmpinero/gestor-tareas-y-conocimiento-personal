from collections.abc import Sequence

from sqlalchemy import case, delete, func, select, update
from sqlalchemy.orm import Session

from gestor_tareas.dominio.foco.errores import tarea_no_encontrada
from gestor_tareas.dominio.siguientes.entidades import Lista, TareaSiguiente
from gestor_tareas.dominio.siguientes.reglas import (
    EntradaDeLaCola,
    comprobar_que_se_puede_anadir,
    nuevo_orden_de_la_cola,
)
from gestor_tareas.infraestructura.persistencia.modelos import ColaSiguientesModelo, TareaModelo
from gestor_tareas.infraestructura.persistencia.repositorios.conflictos import (
    traducir_conflictos,
)

_ORDEN = (ColaSiguientesModelo.posicion, ColaSiguientesModelo.tarea_id)


class RepositorioSiguientesSqlAlchemy:
    """Adaptador de ``RepositorioSiguientes`` sobre MySQL.

    Las dos listas comparten la tabla ``cola_siguientes`` (la columna ``lista`` dice
    en cuál está cada tarea). Cada escritura bloquea antes todas sus filas
    (``FOR UPDATE``), así que las escrituras simultáneas, en una lista o en otra, se
    ejecutan una detrás de otra y cada una ve las listas que dejó la anterior. Las
    completadas se guardan pero no se devuelven.
    """

    def __init__(self, sesion: Session) -> None:
        self._sesion = sesion

    def listar(self, lista: Lista = Lista.SIGUIENTES) -> list[TareaSiguiente]:
        consulta = (
            select(ColaSiguientesModelo.tarea_id, TareaModelo.nombre)
            .join(TareaModelo, TareaModelo.id == ColaSiguientesModelo.tarea_id)
            .where(ColaSiguientesModelo.lista == lista.value, TareaModelo.completada.is_(False))
            .order_by(*_ORDEN)
        )
        return [
            TareaSiguiente(tarea_id=id_tarea, tarea_nombre=nombre)
            for id_tarea, nombre in self._sesion.execute(consulta)
        ]

    def _bloquear_listas(self, lista: Lista) -> list[EntradaDeLaCola]:
        """La lista ``lista`` guardada en su orden. Bloquea hasta confirmar las filas
        de las dos listas (las de las tareas no se bloquean)."""
        consulta = (
            select(
                ColaSiguientesModelo.tarea_id, ColaSiguientesModelo.lista, TareaModelo.completada
            )
            .join(TareaModelo, TareaModelo.id == ColaSiguientesModelo.tarea_id)
            .order_by(*_ORDEN)
            .with_for_update(of=ColaSiguientesModelo)
        )
        return [
            EntradaDeLaCola(tarea_id=id_tarea, completada=completada)
            for id_tarea, de_la_lista, completada in self._sesion.execute(consulta)
            if de_la_lista == lista.value
        ]

    def anadir(self, id_tarea: int, lista: Lista = Lista.SIGUIENTES) -> list[TareaSiguiente]:
        with traducir_conflictos(self._sesion):
            # Bloqueo compartido: nadie la borra ni la completa hasta confirmar.
            completada = self._sesion.scalar(
                select(TareaModelo.completada)
                .where(TareaModelo.id == id_tarea)
                .with_for_update(read=True)
            )
            try:
                if completada is None:
                    raise tarea_no_encontrada(id_tarea)
                comprobar_que_se_puede_anadir(completada)
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
                select(ColaSiguientesModelo.lista).where(ColaSiguientesModelo.tarea_id == id_tarea)
            )
            if esta_en is None:
                self._sesion.add(
                    ColaSiguientesModelo(tarea_id=id_tarea, lista=lista.value, posicion=posicion)
                )
                self._sesion.flush()
            elif esta_en != lista.value:
                # Estaba en la otra lista: pasa al final de esta.
                self._sesion.execute(
                    update(ColaSiguientesModelo)
                    .where(ColaSiguientesModelo.tarea_id == id_tarea)
                    .values(lista=lista.value, posicion=posicion)
                    .execution_options(synchronize_session=False)
                )
            resultado = self.listar(lista)
            self._sesion.commit()
        return resultado

    def reordenar(
        self, ids: Sequence[int], lista: Lista = Lista.SIGUIENTES
    ) -> list[TareaSiguiente]:
        with traducir_conflictos(self._sesion):
            try:
                orden = nuevo_orden_de_la_cola(self._bloquear_listas(lista), ids)
            except Exception:
                self._sesion.rollback()
                raise
            if orden:
                posiciones = {id_tarea: posicion for posicion, id_tarea in enumerate(orden)}
                self._sesion.execute(
                    update(ColaSiguientesModelo)
                    .where(
                        ColaSiguientesModelo.lista == lista.value,
                        ColaSiguientesModelo.tarea_id.in_(orden),
                    )
                    .values(posicion=case(posiciones, value=ColaSiguientesModelo.tarea_id))
                    .execution_options(synchronize_session=False)
                )
            resultado = self.listar(lista)
            self._sesion.commit()
        return resultado

    def quitar(self, id_tarea: int, lista: Lista = Lista.SIGUIENTES) -> list[TareaSiguiente]:
        with traducir_conflictos(self._sesion):
            self._sesion.execute(
                delete(ColaSiguientesModelo).where(
                    ColaSiguientesModelo.tarea_id == id_tarea,
                    ColaSiguientesModelo.lista == lista.value,
                )
            )
            resultado = self.listar(lista)
            self._sesion.commit()
        return resultado
