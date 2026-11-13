"""Grupos de estados y sus estados sobre MySQL.

Las altas, bajas, cambios de nombre y reordenaciones de los estados de un grupo, y
el borrado del grupo, se ponen en fila con el bloqueo exclusivo de la fila del grupo
(``SELECT ... FOR UPDATE``), por grupo y dentro de la transacción (como los pasos de
los workflows): dos altas sobre un grupo vacío no se quedan solo con bloqueos de
hueco compatibles entre sí (que acabarían en interbloqueo), y el bloqueo se libera
al confirmar o deshacer, sin quedar en la conexión. Después se leen los estados del
grupo con ``FOR UPDATE`` (lo último confirmado) y las posiciones se renumeran en dos
fases (negativas y después las finales), porque la restricción única de (grupo_id,
posicion) se comprueba fila a fila.

Quien asigna un grupo a una tarea o la mueve de estado lee el grupo y sus estados
con ``FOR SHARE`` (``leer_para_asignar``): espera a que termine el cambio en curso
del grupo y lo impide hasta que guarde la tarea. Las lecturas compartidas son
compatibles entre sí, así que las tareas de un mismo grupo no se ponen en fila.

Las tareas apuntan a su grupo y a su estado con claves ajenas sin acción: borrar un
estado o un grupo con tareas lo impediría la base de datos, así que en la misma
transacción se mueven (o se desasignan) antes sus tareas. Si una petición
simultánea se cruza y MySQL detecta un interbloqueo, se traduce en
``ConflictoDeConcurrenciaError`` y el caso de uso repite la operación entera.
"""

from collections.abc import Callable, Sequence

from sqlalchemy import case, delete, func, select, update
from sqlalchemy.orm import Session

from gestor_tareas.dominio.grupo_estados.entidades import EstadoGrupo, GrupoEstados
from gestor_tareas.dominio.grupo_estados.errores import (
    estado_duplicado,
    estado_no_encontrado,
    grupo_duplicado,
    grupo_no_encontrado,
)
from gestor_tareas.dominio.grupo_estados.reglas import (
    comprobar_destino_de_las_tareas,
    comprobar_nuevo_orden,
)
from gestor_tareas.dominio.nombres_catalogo import clave_orden_nombre
from gestor_tareas.infraestructura.persistencia.modelos import (
    EstadoGrupoModelo,
    GrupoEstadosModelo,
    TareaModelo,
)
from gestor_tareas.infraestructura.persistencia.repositorios.conflictos import traducir_conflictos
from gestor_tareas.infraestructura.persistencia.repositorios.nombres_unicos import nombre_unico

_Grupo = GrupoEstadosModelo
_Estado = EstadoGrupoModelo


class RepositorioGruposEstadosSqlAlchemy:
    def __init__(self, sesion: Session) -> None:
        self._sesion = sesion

    # --- Lecturas -------------------------------------------------------------

    def _tareas_por_estado(self, id_grupo: int | None = None) -> dict[int, int]:
        """Número de tareas de cada estado (de un grupo o de todos).

        El de un grupo es la suma de los de sus estados: una tarea tiene grupo si y
        solo si tiene estado, y su estado es de su grupo.
        """
        consulta = (
            select(TareaModelo.estado_id, func.count())
            .where(TareaModelo.estado_id.is_not(None))
            .group_by(TareaModelo.estado_id)
        )
        if id_grupo is not None:
            consulta = consulta.where(TareaModelo.grupo_estados_id == id_grupo)
        return {id_estado: total for id_estado, total in self._sesion.execute(consulta)}

    @staticmethod
    def _a_entidad(
        grupo: GrupoEstadosModelo,
        estados: Sequence[EstadoGrupoModelo],
        tareas_por_estado: dict[int, int],
    ) -> GrupoEstados:
        entidades = [
            EstadoGrupo(
                id=e.id, nombre=e.nombre, posicion=e.posicion, tareas=tareas_por_estado.get(e.id, 0)
            )
            for e in sorted(estados, key=lambda e: e.posicion)
        ]
        return GrupoEstados(
            id=grupo.id,
            nombre=grupo.nombre,
            estados=entidades,
            tareas=sum(e.tareas for e in entidades),
        )

    def listar(self) -> list[GrupoEstados]:
        grupos = self._sesion.scalars(select(_Grupo)).all()
        estados_por_grupo: dict[int, list[EstadoGrupoModelo]] = {g.id: [] for g in grupos}
        for estado in self._sesion.scalars(select(_Estado)):
            estados_por_grupo.setdefault(estado.grupo_id, []).append(estado)
        tareas = self._tareas_por_estado()
        entidades = [self._a_entidad(g, estados_por_grupo[g.id], tareas) for g in grupos]
        return sorted(entidades, key=lambda g: (*clave_orden_nombre(g.nombre), g.id))

    def _leer(self, grupo: GrupoEstadosModelo) -> GrupoEstados:
        """El grupo completo tal como lo ve esta transacción (sin confirmar aún)."""
        estados = self._sesion.scalars(select(_Estado).where(_Estado.grupo_id == grupo.id)).all()
        return self._a_entidad(grupo, estados, self._tareas_por_estado(grupo.id))

    # --- Bloqueos -------------------------------------------------------------

    def _grupo_bloqueado(self, id_grupo: int, compartido: bool = False) -> GrupoEstadosModelo:
        consulta = (
            select(_Grupo)
            .where(_Grupo.id == id_grupo)
            .with_for_update(read=compartido)
            .execution_options(populate_existing=True)
        )
        grupo = self._sesion.scalars(consulta).one_or_none()
        if grupo is None:
            raise grupo_no_encontrado(id_grupo)
        return grupo

    def _estados_bloqueados(
        self, id_grupo: int, compartido: bool = False
    ) -> list[EstadoGrupoModelo]:
        """Los estados del grupo, leídos con bloqueo (lo último confirmado), por
        posición. Se bloquean en orden de clave primaria, siempre el mismo."""
        consulta = (
            select(_Estado)
            .where(_Estado.grupo_id == id_grupo)
            .order_by(_Estado.id)
            .with_for_update(read=compartido)
            .execution_options(populate_existing=True)
        )
        return sorted(self._sesion.scalars(consulta), key=lambda e: e.posicion)

    def _modificar(
        self,
        id_grupo: int,
        operacion: Callable[[GrupoEstadosModelo, list[EstadoGrupoModelo]], None],
    ) -> GrupoEstados:
        """Ejecuta la operación en una transacción con el grupo y sus estados
        bloqueados y devuelve el grupo como queda.

        Si falla, deshace la transacción entera; un interbloqueo o una espera
        agotada se traducen en ``ConflictoDeConcurrenciaError``.
        """
        with traducir_conflictos(self._sesion):
            try:
                grupo = self._grupo_bloqueado(id_grupo)
                operacion(grupo, self._estados_bloqueados(id_grupo))
                self._sesion.flush()
                # Antes de confirmar: después, otra petición podría haberlo borrado.
                resultado = self._leer(grupo)
            except BaseException:
                self._sesion.rollback()
                raise
            self._sesion.commit()
        return resultado

    def _ejecutar(self, sentencia) -> None:
        self._sesion.execute(sentencia.execution_options(synchronize_session=False))

    # --- Grupos ---------------------------------------------------------------

    def crear(self, nombre: str) -> GrupoEstados:
        with traducir_conflictos(self._sesion):
            try:
                with nombre_unico(lambda: grupo_duplicado(nombre)):
                    grupo = _Grupo(nombre=nombre)
                    self._sesion.add(grupo)
                    self._sesion.flush()
                resultado = GrupoEstados(id=grupo.id, nombre=grupo.nombre)
            except BaseException:
                self._sesion.rollback()
                raise
            self._sesion.commit()
        return resultado

    def renombrar(self, id_grupo: int, nombre: str) -> GrupoEstados:
        def renombrar(grupo: GrupoEstadosModelo, _: list[EstadoGrupoModelo]) -> None:
            with nombre_unico(lambda: grupo_duplicado(nombre)):
                grupo.nombre = nombre
                self._sesion.flush()

        return self._modificar(id_grupo, renombrar)

    def eliminar(self, id_grupo: int) -> None:
        with traducir_conflictos(self._sesion):
            try:
                grupo = self._grupo_bloqueado(id_grupo)
                # Primero sus tareas quedan sin grupo ni estado (los dos en la misma
                # sentencia, por el CHECK); después el ON DELETE CASCADE borra los
                # estados con el grupo.
                self._ejecutar(
                    update(TareaModelo)
                    .where(TareaModelo.grupo_estados_id == id_grupo)
                    .values(grupo_estados_id=None, estado_id=None)
                )
                self._ejecutar(delete(_Grupo).where(_Grupo.id == id_grupo))
                self._sesion.expunge(grupo)
            except BaseException:
                self._sesion.rollback()
                raise
            self._sesion.commit()

    # --- Estados --------------------------------------------------------------

    def anadir_estado(self, id_grupo: int, nombre: str) -> GrupoEstados:
        def anadir(grupo: GrupoEstadosModelo, estados: list[EstadoGrupoModelo]) -> None:
            posicion = (estados[-1].posicion if estados else 0) + 1
            # El nombre del grupo se lee antes: tras el error, la sesión ya no lee.
            nombre_grupo = grupo.nombre
            with nombre_unico(lambda: estado_duplicado(nombre, nombre_grupo)):
                self._sesion.add(_Estado(grupo_id=grupo.id, nombre=nombre, posicion=posicion))
                self._sesion.flush()

        return self._modificar(id_grupo, anadir)

    @staticmethod
    def _estado_del_grupo(
        grupo: GrupoEstadosModelo, estados: list[EstadoGrupoModelo], id_estado: int
    ) -> EstadoGrupoModelo:
        estado = next((e for e in estados if e.id == id_estado), None)
        if estado is None:
            raise estado_no_encontrado(grupo.id, id_estado)
        return estado

    def renombrar_estado(self, id_grupo: int, id_estado: int, nombre: str) -> GrupoEstados:
        def renombrar(grupo: GrupoEstadosModelo, estados: list[EstadoGrupoModelo]) -> None:
            estado = self._estado_del_grupo(grupo, estados, id_estado)
            nombre_grupo = grupo.nombre
            with nombre_unico(lambda: estado_duplicado(nombre, nombre_grupo)):
                estado.nombre = nombre
                self._sesion.flush()

        return self._modificar(id_grupo, renombrar)

    @staticmethod
    def _de_la_pareja(id_grupo: int, id_estado: int):
        """Condición de las tareas del estado. Incluye el grupo para que MySQL use el
        índice de la clave ajena compuesta y bloquee solo esas filas, no toda la
        tabla."""
        return (TareaModelo.grupo_estados_id == id_grupo) & (TareaModelo.estado_id == id_estado)

    def _ids_tareas_del_estado_bloqueadas(self, id_grupo: int, id_estado: int) -> list[int]:
        """Ids de las tareas del estado, leídas con bloqueo: cuenta también las que
        otra petición confirmó después de la instantánea de esta transacción."""
        consulta = select(TareaModelo.id).where(self._de_la_pareja(id_grupo, id_estado))
        return list(self._sesion.scalars(consulta.with_for_update()))

    def eliminar_estado(self, id_grupo: int, id_estado: int, mover_a: int | None) -> GrupoEstados:
        def eliminar(grupo: GrupoEstadosModelo, estados: list[EstadoGrupoModelo]) -> None:
            eliminado = self._estado_del_grupo(grupo, estados, id_estado)
            tareas = len(self._ids_tareas_del_estado_bloqueadas(grupo.id, id_estado))
            como_entidad = self._a_entidad(grupo, estados, {id_estado: tareas})
            comprobar_destino_de_las_tareas(como_entidad, como_entidad.estado(id_estado), mover_a)
            if tareas:
                self._ejecutar(
                    update(TareaModelo)
                    .where(self._de_la_pareja(grupo.id, id_estado))
                    .values(estado_id=mover_a)
                )
            self._ejecutar(delete(_Estado).where(_Estado.id == id_estado))
            # Los siguientes bajan una posición: primero a negativo y después al final.
            siguientes = (_Estado.grupo_id == grupo.id) & (_Estado.posicion > eliminado.posicion)
            self._ejecutar(update(_Estado).where(siguientes).values(posicion=-_Estado.posicion))
            negativos = (_Estado.grupo_id == grupo.id) & (_Estado.posicion < 0)
            self._ejecutar(update(_Estado).where(negativos).values(posicion=-_Estado.posicion - 1))
            # Las sentencias no actualizan los objetos de la sesión: se descartan para
            # que la lectura final los cargue de nuevo.
            for estado in estados:
                self._sesion.expunge(estado)

        return self._modificar(id_grupo, eliminar)

    def reordenar_estados(self, id_grupo: int, ids: list[int]) -> GrupoEstados:
        def reordenar(grupo: GrupoEstadosModelo, estados: list[EstadoGrupoModelo]) -> None:
            comprobar_nuevo_orden((e.id for e in estados), ids)
            if not ids:
                return
            afectados = _Estado.id.in_(ids)
            # Primero todas a negativo, que no choca con ninguna posición final: si se
            # asignaran directamente, un estado podría tomar la que aún tiene otro.
            self._ejecutar(update(_Estado).where(afectados).values(posicion=-_Estado.posicion))
            posiciones = {id_estado: posicion for posicion, id_estado in enumerate(ids, start=1)}
            self._ejecutar(
                update(_Estado).where(afectados).values(posicion=case(posiciones, value=_Estado.id))
            )
            for estado in estados:
                self._sesion.expunge(estado)

        return self._modificar(id_grupo, reordenar)

    # --- Asignación a las tareas -----------------------------------------------

    def leer_para_asignar(self, id_grupo: int) -> GrupoEstados | None:
        # Sin confirmar: el bloqueo compartido dura hasta que se guarde la tarea.
        with traducir_conflictos(self._sesion):
            consulta = (
                select(_Grupo)
                .where(_Grupo.id == id_grupo)
                .with_for_update(read=True)
                .execution_options(populate_existing=True)
            )
            grupo = self._sesion.scalars(consulta).one_or_none()
            if grupo is None:
                return None
            estados = self._estados_bloqueados(id_grupo, compartido=True)
            return self._a_entidad(grupo, estados, {})
