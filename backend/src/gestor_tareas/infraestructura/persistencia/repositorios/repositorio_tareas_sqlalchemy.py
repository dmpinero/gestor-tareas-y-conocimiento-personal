from collections.abc import Callable, Sequence
from datetime import UTC, datetime

from sqlalchemy import ColumnElement, delete, insert, or_, select, tuple_, update
from sqlalchemy.orm import Session

from gestor_tareas.dominio.excepciones import EntidadNoEncontradaError
from gestor_tareas.dominio.nombres_catalogo import ordenar_nombres
from gestor_tareas.dominio.tarea.congelacion import instante_de_congelacion
from gestor_tareas.dominio.tarea.entidades import (
    Oportunidad,
    ReferenciaEstado,
    ReferenciaGrupoEstados,
    ReferenciaWorkflow,
    Subtarea,
    SubtareasSincronizadas,
    Tarea,
    TipoTarea,
)
from gestor_tareas.dominio.tarea.hibernacion import EstadoDeHibernacionInvalidoError
from gestor_tareas.infraestructura.persistencia.modelos import (
    ComentarioModelo,
    EtiquetaModelo,
    OportunidadModelo,
    PersonaModelo,
    SubestadoModelo,
    SubtareaModelo,
    TareaModelo,
    TareaVinculadaModelo,
)
from gestor_tareas.infraestructura.persistencia.repositorios.conflictos import traducir_conflictos
from gestor_tareas.infraestructura.persistencia.repositorios.repositorio_comentarios_subtarea_sqlalchemy import (  # noqa: E501
    nuevo_comentario_subtarea,
)
from gestor_tareas.infraestructura.persistencia.repositorios.repositorios_catalogos_sqlalchemy import (  # noqa: E501
    filas_obtenidas,
)


def _instante_de_columna(valor: datetime | None) -> datetime | None:
    """La columna guarda el instante en UTC sin la zona: se le vuelve a poner."""
    return valor.replace(tzinfo=UTC) if valor is not None else None


def _instante_a_columna(instante: datetime | None) -> datetime | None:
    """El instante en UTC sin la zona, como lo guarda la columna."""
    return instante.astimezone(UTC).replace(tzinfo=None) if instante is not None else None


def ajustar_congelacion_de_tareas(
    sesion: Session,
    condicion: ColumnElement[bool],
    nombre_estado: str | None,
    ahora: datetime,
) -> None:
    """Aplica la regla de congelación (``instante_de_congelacion``) a las tareas que
    cumplen la condición, que van a quedar en el estado ``nombre_estado`` (``None``:
    sin estado) sin cambiar su estado completada.

    Las lee con bloqueo y guarda solo las que cambian; no confirma. Es para los
    cambios de estado de muchas tareas a la vez (renombrar o eliminar un estado,
    eliminar un grupo), dentro de su transacción.
    """
    consulta = (
        select(TareaModelo.id, TareaModelo.completada, TareaModelo.congelada_en)
        .where(condicion)
        .order_by(TareaModelo.id)
        .with_for_update()
    )
    for fila in sesion.execute(consulta).all():
        anterior = _instante_de_columna(fila.congelada_en)
        nuevo = instante_de_congelacion(anterior, fila.completada, nombre_estado, ahora)
        if nuevo != anterior:
            sesion.execute(
                update(TareaModelo)
                .where(TareaModelo.id == fila.id)
                .values(congelada_en=_instante_a_columna(nuevo))
                .execution_options(synchronize_session=False)
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
        subtareas=[_a_subtarea(s) for s in _ordenar_subtareas(modelo)],
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
        congelada_en=_instante_de_columna(modelo.congelada_en),
        subestado=modelo.subestado.nombre if modelo.subestado is not None else None,
        hibernada_desde=_instante_de_columna(modelo.hibernada_desde),
        vinculadas=sorted(v.vinculada_id for v in modelo.vinculos),
    )


def _ordenar_subtareas(modelo: TareaModelo) -> list[SubtareaModelo]:
    """Primero las subtareas que nacen de un paso del workflow de la tarea, por el
    número actual del paso; después las demás (añadidas a mano, de un paso que ya no
    existe o de otro workflow), por orden de alta."""

    def clave(subtarea: SubtareaModelo) -> tuple[int, int, int]:
        paso = subtarea.paso
        if paso is not None and paso.workflow_id == modelo.workflow_id:
            return (0, paso.numero, subtarea.id)
        return (1, 0, subtarea.id)

    return sorted(modelo.subtareas, key=clave)


def _a_subtarea(modelo: SubtareaModelo) -> Subtarea:
    return Subtarea(
        id=modelo.id,
        nombre=modelo.nombre,
        asignado=modelo.asignado.nombre if modelo.asignado is not None else None,
        prioridad=modelo.prioridad,
        resuelta=modelo.resuelta,
        comentarios=modelo.numero_comentarios,
        paso_id=modelo.paso_id,
    )


class RepositorioTareasSqlAlchemy:
    def __init__(self, sesion: Session) -> None:
        self._sesion = sesion

    def _filas_catalogo[M: (EtiquetaModelo, PersonaModelo, SubestadoModelo)](
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
        modelo.subestado = (
            self._filas_catalogo(SubestadoModelo, [tarea.subestado])[0]
            if tarea.subestado is not None
            else None
        )
        modelo.congelada_en = _instante_a_columna(tarea.congelada_en)

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
        # Sus comentarios iniciales se insertan con ella, en la misma transacción y en
        # el orden de la lista (sus ids siguen ese orden).
        return SubtareaModelo(
            nombre=subtarea.nombre,
            asignado=persona,
            prioridad=subtarea.prioridad,
            resuelta=subtarea.resuelta,
            paso_id=subtarea.paso_id,
            comentarios=[
                nuevo_comentario_subtarea(c.texto, c.creado) for c in subtarea.comentarios_iniciales
            ],
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

    def cambiar_completada(self, id_tarea: int, completada: bool, ahora: datetime) -> Tarea | None:
        with traducir_conflictos(self._sesion):
            modelo = self._tarea_bloqueada(id_tarea)
            if modelo is None:
                self._sesion.rollback()
                return None
            tarea = _a_entidad(modelo)
            tarea.completada = completada
            tarea.ajustar_congelacion(ahora)
            modelo.completada = completada
            modelo.congelada_en = _instante_a_columna(tarea.congelada_en)
            self._sesion.commit()
        return _a_entidad(modelo)

    def hibernar(self, id_tarea: int, ahora: datetime, comentario: str | None) -> Tarea | None:
        with traducir_conflictos(self._sesion):
            modelo = self._tarea_bloqueada(id_tarea)
            if modelo is None:
                self._sesion.rollback()
                return None
            tarea = self._cambiar_hibernacion(modelo, lambda t: t.hibernar(ahora))
            if comentario is not None:
                self._sesion.add(
                    ComentarioModelo(
                        tarea_id=id_tarea, texto=comentario, creado=_instante_a_columna(ahora)
                    )
                )
            modelo.hibernada_desde = _instante_a_columna(tarea.hibernada_desde)
            self._sesion.commit()
        return _a_entidad(modelo)

    def reanudar(self, id_tarea: int, ahora: datetime) -> Tarea | None:
        with traducir_conflictos(self._sesion):
            modelo = self._tarea_bloqueada(id_tarea)
            if modelo is None:
                self._sesion.rollback()
                return None
            tarea = self._cambiar_hibernacion(modelo, lambda t: t.reanudar(ahora))
            modelo.fecha_vencimiento = tarea.fecha_vencimiento
            modelo.hibernada_desde = _instante_a_columna(tarea.hibernada_desde)
            self._sesion.commit()
        return _a_entidad(modelo)

    def _bloquear_tareas(self, ids: Sequence[int]) -> set[int]:
        """Lee con bloqueo las tareas de ``ids`` y devuelve las que existen.

        Se bloquean en orden de id: dos peticiones que vinculan las mismas tareas
        desde lados distintos esperan una a otra en lugar de bloquearse entre sí, y
        ninguna de las tareas puede borrarse hasta confirmar.
        """
        consulta = (
            select(TareaModelo.id)
            .where(TareaModelo.id.in_(ids))
            .order_by(TareaModelo.id)
            .with_for_update()
        )
        return set(self._sesion.scalars(consulta).all())

    def _comprobar_tareas(self, id_tarea: int, otras: Sequence[int]) -> bool:
        """Bloquea la tarea y las ``otras``. Devuelve ``False`` (deshecha la
        transacción) si la tarea no existe y lanza ``EntidadNoEncontradaError`` (ídem)
        con la primera de las ``otras`` que no exista."""
        existentes = self._bloquear_tareas([id_tarea, *otras])
        if id_tarea not in existentes:
            self._sesion.rollback()
            return False
        faltan = sorted(set(otras) - existentes)
        if faltan:
            self._sesion.rollback()
            raise EntidadNoEncontradaError(f"No existe la tarea con id {faltan[0]}")
        return True

    def vincular(self, id_tarea: int, ids: Sequence[int]) -> Tarea | None:
        with traducir_conflictos(self._sesion):
            if not self._comprobar_tareas(id_tarea, ids):
                return None
            ya_vinculadas = set(
                self._sesion.scalars(
                    select(TareaVinculadaModelo.vinculada_id).where(
                        TareaVinculadaModelo.tarea_id == id_tarea,
                        TareaVinculadaModelo.vinculada_id.in_(ids),
                    )
                ).all()
            )
            nuevas = [i for i in ids if i not in ya_vinculadas]
            if nuevas:
                # Los dos sentidos de cada vínculo, en la misma sentencia.
                filas = [{"tarea_id": id_tarea, "vinculada_id": i} for i in nuevas]
                filas += [{"tarea_id": i, "vinculada_id": id_tarea} for i in nuevas]
                self._sesion.execute(insert(TareaVinculadaModelo), filas)
            self._sesion.commit()
        return self._tarea_tras_confirmar(id_tarea)

    def desvincular(self, id_tarea: int, id_vinculada: int) -> Tarea | None:
        with traducir_conflictos(self._sesion):
            if not self._comprobar_tareas(id_tarea, [id_vinculada]):
                return None
            self._sesion.execute(
                delete(TareaVinculadaModelo).where(
                    or_(
                        tuple_(TareaVinculadaModelo.tarea_id, TareaVinculadaModelo.vinculada_id)
                        == (id_tarea, id_vinculada),
                        tuple_(TareaVinculadaModelo.tarea_id, TareaVinculadaModelo.vinculada_id)
                        == (id_vinculada, id_tarea),
                    )
                )
            )
            self._sesion.commit()
        return self._tarea_tras_confirmar(id_tarea)

    def _cambiar_hibernacion(self, modelo: TareaModelo, cambio: Callable[[Tarea], None]) -> Tarea:
        """Aplica el cambio de hibernación a la tarea leída con bloqueo y la devuelve;
        si no se admite, deshace la transacción (y libera el bloqueo) y lanza el
        error."""
        tarea = _a_entidad(modelo)
        try:
            cambio(tarea)
        except EstadoDeHibernacionInvalidoError:
            self._sesion.rollback()
            raise
        return tarea

    def cambiar_estado(self, id_tarea: int, estado: ReferenciaEstado, ahora: datetime) -> Tarea:
        with traducir_conflictos(self._sesion):
            modelo = self._tarea_bloqueada(id_tarea)
            if modelo is None:
                self._sesion.rollback()
                raise EntidadNoEncontradaError(f"No existe la tarea con id {id_tarea}")
            # La relación con el estado aún no se ha recargado: se usa el nuevo.
            tarea = _a_entidad(modelo)
            tarea.estado = ReferenciaEstado(id=estado.id, nombre=estado.nombre)
            tarea.ajustar_congelacion(ahora)
            modelo.estado_id = estado.id
            modelo.congelada_en = _instante_a_columna(tarea.congelada_en)
            # Antes de confirmar: después, otra petición podría haberla borrado.
            self._sesion.flush()
            self._sesion.commit()
        return tarea

    def eliminar(self, id_tarea: int) -> bool:
        with traducir_conflictos(self._sesion):
            # Un único DELETE: el ON DELETE CASCADE de la base de datos borra en la
            # misma sentencia sus datos de oportunidad, sus enlaces con los
            # catálogos, sus vínculos con otras tareas (en los dos sentidos), sus
            # subtareas, sus comentarios y los de sus subtareas (las filas de los
            # catálogos no se tocan). Espera a quien tenga la tarea
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

    def listar_abiertas_de_workflow(
        self, id_workflow: int, para_modificar: bool = False
    ) -> list[Tarea]:
        consulta = (
            select(TareaModelo)
            .where(TareaModelo.workflow_id == id_workflow, TareaModelo.completada.is_(False))
            .order_by(TareaModelo.id)
        )
        if not para_modificar:
            return [_a_entidad(m) for m in self._sesion.scalars(consulta)]
        # Sin confirmar: los bloqueos duran hasta que se guarden los cambios. Primero
        # las tareas y después sus subtareas, en orden de clave primaria: quien
        # renombra o borra una subtarea a la vez espera (o se le espera) sin cruzarse.
        with traducir_conflictos(self._sesion):
            consulta = consulta.with_for_update().execution_options(populate_existing=True)
            modelos = list(self._sesion.scalars(consulta))
            if modelos:
                subtareas = (
                    select(SubtareaModelo)
                    .where(SubtareaModelo.tarea_id.in_([m.id for m in modelos]))
                    .order_by(SubtareaModelo.id)
                    .with_for_update()
                    .execution_options(populate_existing=True)
                )
                self._sesion.scalars(subtareas).all()
                for modelo in modelos:
                    # Recarga la lista con lo último confirmado (ya bloqueado).
                    self._sesion.expire(modelo, ["subtareas"])
            return [_a_entidad(m) for m in modelos]

    def sincronizar_subtareas(self, cambios: Sequence[SubtareasSincronizadas]) -> None:
        with traducir_conflictos(self._sesion):
            for cambio in cambios:
                modelo = self._sesion.get(TareaModelo, cambio.id_tarea)
                if modelo is None:
                    self._sesion.rollback()
                    raise EntidadNoEncontradaError(f"No existe la tarea con id {cambio.id_tarea}")
                por_id = {s.id: s for s in modelo.subtareas}
                for id_subtarea, nombre in cambio.nombres.items():
                    por_id[id_subtarea].nombre = nombre
                # Al final de las que ya tiene, en el orden de la lista (como en
                # ``actualizar``).
                modelo.subtareas.extend(self._subtarea_nueva(s) for s in cambio.nuevas)
            self._sesion.commit()
