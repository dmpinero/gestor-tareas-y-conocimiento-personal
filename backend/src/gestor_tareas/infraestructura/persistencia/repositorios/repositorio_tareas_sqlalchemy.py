from collections.abc import Sequence

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from gestor_tareas.dominio.excepciones import EntidadNoEncontradaError
from gestor_tareas.dominio.nombres_catalogo import ordenar_nombres
from gestor_tareas.dominio.tarea.entidades import (
    Oportunidad,
    ReferenciaEstado,
    ReferenciaGrupoEstados,
    ReferenciaWorkflow,
    Subtarea,
    Tarea,
    TipoTarea,
)
from gestor_tareas.infraestructura.persistencia.modelos import (
    EtiquetaModelo,
    OportunidadModelo,
    PersonaModelo,
    SubtareaModelo,
    TareaModelo,
)
from gestor_tareas.infraestructura.persistencia.repositorios.conflictos import traducir_conflictos
from gestor_tareas.infraestructura.persistencia.repositorios.repositorios_catalogos_sqlalchemy import (  # noqa: E501
    filas_obtenidas,
)


def _a_oportunidad(modelo: OportunidadModelo | None) -> Oportunidad | None:
    if modelo is None:
        return None
    return Oportunidad(
        codigo=modelo.codigo, descripcion=modelo.descripcion, observaciones=modelo.observaciones
    )


def _a_entidad(modelo: TareaModelo) -> Tarea:
    return Tarea(
        id=modelo.id,
        nombre=modelo.nombre,
        prioridad=modelo.prioridad,
        descripcion=modelo.descripcion,
        fecha_creacion=modelo.fecha_creacion,
        fecha_vencimiento=modelo.fecha_vencimiento,
        etiquetas=ordenar_nombres(e.nombre for e in modelo.etiquetas),
        asignados=ordenar_nombres(p.nombre for p in modelo.asignados),
        tipo=TipoTarea(modelo.tipo) if modelo.tipo is not None else None,
        oportunidad=_a_oportunidad(modelo.oportunidad),
        completada=modelo.completada,
        subtareas=[_a_subtarea(s) for s in sorted(modelo.subtareas, key=lambda s: s.id)],
        grupo_estados=(
            ReferenciaGrupoEstados(id=modelo.grupo_estados.id, nombre=modelo.grupo_estados.nombre)
            if modelo.grupo_estados is not None
            else None
        ),
        estado=(
            ReferenciaEstado(id=modelo.estado.id, nombre=modelo.estado.nombre)
            if modelo.estado is not None
            else None
        ),
        workflow=(
            ReferenciaWorkflow(id=modelo.workflow.id, nombre=modelo.workflow.nombre)
            if modelo.workflow is not None
            else None
        ),
    )


def _a_subtarea(modelo: SubtareaModelo) -> Subtarea:
    return Subtarea(
        id=modelo.id,
        nombre=modelo.nombre,
        asignado=modelo.asignado.nombre if modelo.asignado is not None else None,
        prioridad=modelo.prioridad,
        resuelta=modelo.resuelta,
        comentarios=modelo.numero_comentarios,
    )


class RepositorioTareasSqlAlchemy:
    def __init__(self, sesion: Session) -> None:
        self._sesion = sesion

    def _filas_catalogo[M: (EtiquetaModelo, PersonaModelo)](
        self, modelo: type[M], nombres: list[str]
    ) -> list[M]:
        """Filas del catálogo con esos nombres, que ya deben existir.

        Se usan las filas que ``obtener_o_crear`` ya devolvió en esta sesión. Solo
        los nombres que no pasaron por él se buscan, con una lectura con bloqueo
        (FOR SHARE) para ver también lo confirmado después de la instantánea.
        """
        if not nombres:
            return []
        filas, faltan = filas_obtenidas(self._sesion, modelo, nombres)
        if faltan:
            consulta = select(modelo).where(modelo.nombre.in_(faltan)).with_for_update(read=True)
            filas.extend(self._sesion.scalars(consulta))
        if len(filas) != len(nombres):
            raise ValueError(f"Faltan nombres en el catálogo {modelo.__tablename__}: {nombres}")
        return filas

    def _asignar_datos(self, modelo: TareaModelo, tarea: Tarea) -> None:
        modelo.nombre = tarea.nombre
        modelo.prioridad = tarea.prioridad
        modelo.descripcion = tarea.descripcion
        modelo.fecha_creacion = tarea.fecha_creacion
        modelo.fecha_vencimiento = tarea.fecha_vencimiento
        # Asignar la lista completa sustituye el conjunto de enlaces de la tarea.
        modelo.etiquetas = self._filas_catalogo(EtiquetaModelo, tarea.etiquetas)
        modelo.asignados = self._filas_catalogo(PersonaModelo, tarea.asignados)
        modelo.tipo = tarea.tipo.value if tarea.tipo is not None else None
        self._asignar_oportunidad(modelo, tarea.oportunidad)
        modelo.grupo_estados_id = tarea.grupo_estados.id if tarea.grupo_estados else None
        modelo.estado_id = tarea.estado.id if tarea.estado else None
        modelo.workflow_id = tarea.workflow.id if tarea.workflow else None

    @staticmethod
    def _asignar_oportunidad(modelo: TareaModelo, oportunidad: Oportunidad | None) -> None:
        """Sustituye los datos de oportunidad de la tarea.

        La fila existente se modifica en lugar de reemplazarse: con otra fila con
        la misma clave, SQLAlchemy insertaría la nueva antes de borrar la vieja.
        """
        if oportunidad is None:
            modelo.oportunidad = None
            return
        if modelo.oportunidad is None:
            modelo.oportunidad = OportunidadModelo()
        modelo.oportunidad.codigo = oportunidad.codigo
        modelo.oportunidad.descripcion = oportunidad.descripcion
        modelo.oportunidad.observaciones = oportunidad.observaciones

    def _subtarea_nueva(self, subtarea: Subtarea) -> SubtareaModelo:
        persona = None
        if subtarea.asignado is not None:
            (persona,) = self._filas_catalogo(PersonaModelo, [subtarea.asignado])
        return SubtareaModelo(
            nombre=subtarea.nombre,
            asignado=persona,
            prioridad=subtarea.prioridad,
            resuelta=subtarea.resuelta,
        )

    def crear(self, tarea: Tarea) -> Tarea:
        with traducir_conflictos(self._sesion):
            # Las subtareas se insertan en el orden de la lista, así que sus ids
            # (y con ellos su orden de alta) siguen ese orden.
            modelo = TareaModelo(
                completada=tarea.completada,
                subtareas=[self._subtarea_nueva(s) for s in tarea.subtareas],
            )
            self._asignar_datos(modelo, tarea)
            self._sesion.add(modelo)
            self._sesion.commit()
        return _a_entidad(modelo)

    def listar(self) -> list[Tarea]:
        modelos = self._sesion.scalars(select(TareaModelo).order_by(TareaModelo.id)).all()
        return [_a_entidad(m) for m in modelos]

    def obtener_por_id(self, id_tarea: int) -> Tarea | None:
        modelo = self._sesion.get(TareaModelo, id_tarea)
        return _a_entidad(modelo) if modelo is not None else None

    def _tarea_bloqueada(self, id_tarea: int) -> TareaModelo | None:
        """La tarea leída con bloqueo, o ``None`` si ya no existe.

        La lectura con bloqueo ve lo último confirmado y espera a un borrado en
        curso: si otra petición borra la tarea entre la lectura del caso de uso y
        esta escritura, se detecta aquí en lugar de fallar el UPDATE.
        """
        consulta = (
            select(TareaModelo)
            .where(TareaModelo.id == id_tarea)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        return self._sesion.scalars(consulta).one_or_none()

    def obtener_para_modificar(self, id_tarea: int) -> Tarea | None:
        # Sin confirmar: el bloqueo dura hasta que se guarden los cambios.
        with traducir_conflictos(self._sesion):
            modelo = self._tarea_bloqueada(id_tarea)
            return _a_entidad(modelo) if modelo is not None else None

    def actualizar(self, tarea: Tarea, subtareas_nuevas: Sequence[Subtarea] = ()) -> Tarea:
        with traducir_conflictos(self._sesion):
            modelo = self._tarea_bloqueada(tarea.id)
            if modelo is None:
                self._sesion.rollback()
                raise EntidadNoEncontradaError(f"No existe la tarea con id {tarea.id}")
            self._asignar_datos(modelo, tarea)
            # Al final de las que ya tiene, en el orden de la lista: se insertan en ese
            # orden, así que sus ids (y su orden de alta) lo siguen.
            modelo.subtareas.extend(self._subtarea_nueva(s) for s in subtareas_nuevas)
            self._sesion.commit()
        return _a_entidad(modelo)

    def cambiar_completada(self, id_tarea: int, completada: bool) -> Tarea | None:
        with traducir_conflictos(self._sesion):
            modelo = self._tarea_bloqueada(id_tarea)
            if modelo is None:
                self._sesion.rollback()
                return None
            modelo.completada = completada
            self._sesion.commit()
        return _a_entidad(modelo)

    def cambiar_estado(self, id_tarea: int, estado: ReferenciaEstado) -> Tarea:
        with traducir_conflictos(self._sesion):
            modelo = self._tarea_bloqueada(id_tarea)
            if modelo is None:
                self._sesion.rollback()
                raise EntidadNoEncontradaError(f"No existe la tarea con id {id_tarea}")
            modelo.estado_id = estado.id
            self._sesion.flush()
            # Antes de confirmar: después, otra petición podría haberla borrado. La
            # relación con el estado aún no se ha recargado: se usa el nuevo.
            tarea = _a_entidad(modelo)
            tarea.estado = ReferenciaEstado(id=estado.id, nombre=estado.nombre)
            self._sesion.commit()
        return tarea

    def eliminar(self, id_tarea: int) -> bool:
        with traducir_conflictos(self._sesion):
            # Un único DELETE: el ON DELETE CASCADE de la base de datos borra en la
            # misma sentencia sus datos de oportunidad, sus enlaces con los
            # catálogos, sus subtareas, sus comentarios y los de sus subtareas (las
            # filas de los catálogos no se tocan). Espera a quien tenga la tarea
            # bloqueada (p. ej. un alta de subtarea en curso) y se lleva lo que haya
            # confirmado.
            resultado = self._sesion.execute(delete(TareaModelo).where(TareaModelo.id == id_tarea))
            if resultado.rowcount == 0:
                self._sesion.rollback()
                return False
            self._sesion.commit()
        return True

    def _subtarea_bloqueada(self, id_tarea: int, id_subtarea: int) -> SubtareaModelo | None:
        """La subtarea de esa tarea, leída con bloqueo, o ``None`` si no la tiene.

        La lectura con bloqueo ve lo último confirmado y espera a otra operación en
        curso sobre la misma subtarea (si la borra, ya no la encuentra).
        """
        consulta = (
            select(SubtareaModelo)
            .where(SubtareaModelo.id == id_subtarea, SubtareaModelo.tarea_id == id_tarea)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        return self._sesion.scalars(consulta).one_or_none()

    def _tarea_tras_confirmar(self, id_tarea: int) -> Tarea | None:
        """Devuelve la tarea leída de nuevo tras confirmar la transacción.

        Se lee después de confirmar, con una instantánea nueva: antes, una lectura
        normal (REPEATABLE READ) no vería la persona que otra petición dio de alta
        tras la instantánea, aunque esta sesión ya la haya enlazado. La
        confirmación caduca además lo cargado en la sesión, así que la lista de
        subtareas no queda desfasada. Devuelve ``None`` si la tarea ya no existe.
        """
        modelo = self._sesion.get(TareaModelo, id_tarea)
        return _a_entidad(modelo) if modelo is not None else None

    def anadir_subtarea(self, id_tarea: int, subtarea: Subtarea) -> Tarea | None:
        with traducir_conflictos(self._sesion):
            # Lectura compartida con bloqueo: la tarea no puede borrarse mientras se
            # añade la subtarea, y se ve aunque se haya creado tras la instantánea.
            consulta = select(TareaModelo.id).where(TareaModelo.id == id_tarea)
            if self._sesion.scalars(consulta.with_for_update(read=True)).first() is None:
                # Deshace también las altas en el catálogo hechas para la subtarea.
                self._sesion.rollback()
                return None
            persona = None
            if subtarea.asignado is not None:
                (persona,) = self._filas_catalogo(PersonaModelo, [subtarea.asignado])
            self._sesion.add(
                SubtareaModelo(
                    tarea_id=id_tarea,
                    nombre=subtarea.nombre,
                    asignado=persona,
                    prioridad=subtarea.prioridad,
                    resuelta=False,
                )
            )
            self._sesion.commit()
        return self._tarea_tras_confirmar(id_tarea)

    def cambiar_resuelta_subtarea(
        self, id_tarea: int, id_subtarea: int, resuelta: bool
    ) -> Tarea | None:
        with traducir_conflictos(self._sesion):
            subtarea = self._subtarea_bloqueada(id_tarea, id_subtarea)
            if subtarea is None:
                self._sesion.rollback()
                return None
            subtarea.resuelta = resuelta
            self._sesion.commit()
        return self._tarea_tras_confirmar(id_tarea)

    def editar_subtarea(self, id_tarea: int, subtarea: Subtarea) -> Tarea | None:
        if subtarea.id is None:
            raise ValueError("La subtarea a editar debe tener id")
        with traducir_conflictos(self._sesion):
            modelo = self._subtarea_bloqueada(id_tarea, subtarea.id)
            if modelo is None:
                # Deshace también las altas en el catálogo hechas para la subtarea.
                self._sesion.rollback()
                return None
            persona = None
            if subtarea.asignado is not None:
                (persona,) = self._filas_catalogo(PersonaModelo, [subtarea.asignado])
            modelo.nombre = subtarea.nombre
            modelo.asignado = persona
            modelo.prioridad = subtarea.prioridad
            self._sesion.commit()
        return self._tarea_tras_confirmar(id_tarea)

    def eliminar_subtarea(self, id_tarea: int, id_subtarea: int) -> Tarea | None:
        with traducir_conflictos(self._sesion):
            subtarea = self._subtarea_bloqueada(id_tarea, id_subtarea)
            if subtarea is None:
                self._sesion.rollback()
                return None
            self._sesion.delete(subtarea)
            self._sesion.commit()
        return self._tarea_tras_confirmar(id_tarea)
