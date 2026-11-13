"""Workflows y sus pasos sobre MySQL.

Las altas, bajas, cambios de nombre y reordenaciones de los pasos de un workflow, y
el cambio de nombre y el borrado del workflow, se ponen en fila con el bloqueo
exclusivo de la fila del workflow (``SELECT ... FOR UPDATE``), dentro de la
transacción: dos altas sobre un workflow vacío no se quedan solo con bloqueos de
hueco compatibles entre sí (que acabarían en interbloqueo), y el bloqueo se libera
al confirmar o deshacer. Después se leen los pasos del workflow con ``FOR UPDATE``
(lo último confirmado) y los números se renumeran en dos fases (negativos y después
los finales), porque la restricción única de (workflow_id, numero) se comprueba fila
a fila.

Quien asigna un workflow a una tarea y copia sus pasos lee el workflow y sus pasos
con ``FOR SHARE`` (``leer_para_copiar``), siempre antes que el grupo de estados y la
tarea: espera a que termine el cambio en curso del workflow, así que nunca ve una
reordenación a medias, y lo impide (también su borrado) hasta que guarde la tarea.
Las lecturas compartidas son compatibles entre sí, así que las tareas de un mismo
workflow no se ponen en fila. Después, con todos los pasos ya bloqueados, lee sus
comentarios con ``FOR SHARE``: quien da de alta, edita o borra un comentario de un
paso bloquea antes la fila del paso en exclusiva (ver
``RepositorioComentariosPasoSqlAlchemy``), así que la copia espera a que termine y
lo impide hasta que se guarde la tarea; nunca copia los comentarios de un paso a
medias.

Las tareas apuntan a su workflow con una clave ajena sin acción: al borrar el
workflow se dejan antes sus tareas sin workflow en la misma transacción. Sus pasos
los borra el ``ON DELETE CASCADE``. Si una petición simultánea se cruza y MySQL
detecta un interbloqueo, se traduce en ``ConflictoDeConcurrenciaError`` y el caso de
uso repite la operación entera.
"""

from collections import defaultdict
from collections.abc import Callable, Sequence

from sqlalchemy import case, delete, select, update
from sqlalchemy.orm import Session

from gestor_tareas.dominio.nombres_catalogo import clave_orden_nombre
from gestor_tareas.dominio.workflow.entidades import PasoWorkflow, Workflow
from gestor_tareas.dominio.workflow.errores import (
    paso_no_encontrado,
    workflow_duplicado,
    workflow_no_encontrado,
)
from gestor_tareas.dominio.workflow.orden import comprobar_nuevo_orden
from gestor_tareas.infraestructura.persistencia.modelos import (
    ComentarioPasoModelo,
    PasoWorkflowModelo,
    TareaModelo,
    WorkflowModelo,
)
from gestor_tareas.infraestructura.persistencia.repositorios.conflictos import traducir_conflictos
from gestor_tareas.infraestructura.persistencia.repositorios.nombres_unicos import nombre_unico

_Workflow = WorkflowModelo
_Paso = PasoWorkflowModelo


def _a_paso(modelo: PasoWorkflowModelo) -> PasoWorkflow:
    return PasoWorkflow(
        id=modelo.id,
        numero=modelo.numero,
        nombre=modelo.nombre,
        comentarios=modelo.numero_comentarios,
    )


def _a_entidad(workflow: WorkflowModelo, pasos: Sequence[PasoWorkflowModelo]) -> Workflow:
    return Workflow(
        id=workflow.id,
        nombre=workflow.nombre,
        pasos=[_a_paso(p) for p in sorted(pasos, key=lambda p: p.numero)],
    )


class RepositorioWorkflowsSqlAlchemy:
    def __init__(self, sesion: Session) -> None:
        self._sesion = sesion

    # --- Lecturas -------------------------------------------------------------

    def listar(self) -> list[Workflow]:
        workflows = self._sesion.scalars(select(_Workflow)).all()
        pasos_por_workflow: dict[int, list[PasoWorkflowModelo]] = {w.id: [] for w in workflows}
        for paso in self._sesion.scalars(select(_Paso)):
            pasos_por_workflow.setdefault(paso.workflow_id, []).append(paso)
        entidades = [_a_entidad(w, pasos_por_workflow[w.id]) for w in workflows]
        return sorted(entidades, key=lambda w: (*clave_orden_nombre(w.nombre), w.id))

    # --- Bloqueos -------------------------------------------------------------

    def _workflow_bloqueado(self, id_workflow: int, compartido: bool = False) -> WorkflowModelo:
        workflow = self._workflow_bloqueado_o_nada(id_workflow, compartido)
        if workflow is None:
            raise workflow_no_encontrado(id_workflow)
        return workflow

    def _workflow_bloqueado_o_nada(
        self, id_workflow: int, compartido: bool = False
    ) -> WorkflowModelo | None:
        consulta = (
            select(_Workflow)
            .where(_Workflow.id == id_workflow)
            .with_for_update(read=compartido)
            .execution_options(populate_existing=True)
        )
        return self._sesion.scalars(consulta).one_or_none()

    def _pasos_bloqueados(
        self, id_workflow: int, compartido: bool = False
    ) -> list[PasoWorkflowModelo]:
        """Los pasos del workflow, leídos con bloqueo (lo último confirmado), por
        número. Se bloquean en orden de clave primaria, siempre el mismo, y la
        condición usa el índice de (workflow_id, numero): solo se bloquean los pasos
        de ese workflow. ``populate_existing`` sustituye los datos de los objetos que
        la sesión ya tuviera cargados."""
        consulta = (
            select(_Paso)
            .where(_Paso.workflow_id == id_workflow)
            .order_by(_Paso.id)
            .with_for_update(read=compartido)
            .execution_options(populate_existing=True)
        )
        return sorted(self._sesion.scalars(consulta), key=lambda p: p.numero)

    def _leer(self, workflow: WorkflowModelo) -> Workflow:
        """El workflow con sus pasos tal como los ve esta transacción (sin confirmar
        aún)."""
        consulta = (
            select(_Paso)
            .where(_Paso.workflow_id == workflow.id)
            .execution_options(populate_existing=True)
        )
        return _a_entidad(workflow, self._sesion.scalars(consulta).all())

    def _modificar(
        self,
        id_workflow: int,
        operacion: Callable[[WorkflowModelo, list[PasoWorkflowModelo]], None],
    ) -> Workflow:
        """Ejecuta la operación en una transacción con el workflow y sus pasos
        bloqueados y devuelve el workflow como queda, leído antes de confirmar
        (después, otra petición podría haberlo borrado).

        Si falla, deshace la transacción entera; un interbloqueo o una espera
        agotada se traducen en ``ConflictoDeConcurrenciaError``.
        """
        with traducir_conflictos(self._sesion):
            try:
                workflow = self._workflow_bloqueado(id_workflow)
                operacion(workflow, self._pasos_bloqueados(id_workflow))
                self._sesion.flush()
                resultado = self._leer(workflow)
            except BaseException:
                self._sesion.rollback()
                raise
            self._sesion.commit()
        return resultado

    def _ejecutar(self, sentencia) -> None:
        self._sesion.execute(sentencia.execution_options(synchronize_session=False))

    # --- Workflows --------------------------------------------------------------

    def crear(self, nombre: str) -> Workflow:
        with traducir_conflictos(self._sesion):
            try:
                with nombre_unico(lambda: workflow_duplicado(nombre)):
                    workflow = _Workflow(nombre=nombre)
                    self._sesion.add(workflow)
                    self._sesion.flush()
                resultado = Workflow(id=workflow.id, nombre=workflow.nombre)
            except BaseException:
                self._sesion.rollback()
                raise
            self._sesion.commit()
        return resultado

    def renombrar(self, id_workflow: int, nombre: str) -> Workflow:
        def renombrar(workflow: WorkflowModelo, _: list[PasoWorkflowModelo]) -> None:
            with nombre_unico(lambda: workflow_duplicado(nombre)):
                workflow.nombre = nombre
                self._sesion.flush()

        return self._modificar(id_workflow, renombrar)

    def eliminar(self, id_workflow: int) -> None:
        with traducir_conflictos(self._sesion):
            try:
                workflow = self._workflow_bloqueado(id_workflow)
                # Primero sus tareas quedan sin workflow (la condición usa el índice
                # de la clave ajena: solo se bloquean esas tareas); después el ON
                # DELETE CASCADE borra los pasos con el workflow.
                self._ejecutar(
                    update(TareaModelo)
                    .where(TareaModelo.workflow_id == id_workflow)
                    .values(workflow_id=None)
                )
                self._ejecutar(delete(_Workflow).where(_Workflow.id == id_workflow))
                self._sesion.expunge(workflow)
            except BaseException:
                self._sesion.rollback()
                raise
            self._sesion.commit()

    # --- Pasos ------------------------------------------------------------------

    def anadir_paso(self, id_workflow: int, nombre: str) -> Workflow:
        def anadir(workflow: WorkflowModelo, pasos: list[PasoWorkflowModelo]) -> None:
            numero = (pasos[-1].numero if pasos else 0) + 1
            self._sesion.add(_Paso(workflow_id=workflow.id, nombre=nombre, numero=numero))

        return self._modificar(id_workflow, anadir)

    @staticmethod
    def _paso_del_workflow(
        workflow: WorkflowModelo, pasos: list[PasoWorkflowModelo], id_paso: int
    ) -> PasoWorkflowModelo:
        paso = next((p for p in pasos if p.id == id_paso), None)
        if paso is None:
            raise paso_no_encontrado(workflow.id, id_paso)
        return paso

    def renombrar_paso(self, id_workflow: int, id_paso: int, nombre: str) -> Workflow:
        def renombrar(workflow: WorkflowModelo, pasos: list[PasoWorkflowModelo]) -> None:
            self._paso_del_workflow(workflow, pasos, id_paso).nombre = nombre

        return self._modificar(id_workflow, renombrar)

    def eliminar_paso(self, id_workflow: int, id_paso: int) -> Workflow:
        def eliminar(workflow: WorkflowModelo, pasos: list[PasoWorkflowModelo]) -> None:
            eliminado = self._paso_del_workflow(workflow, pasos, id_paso)
            self._ejecutar(delete(_Paso).where(_Paso.id == id_paso))
            # Los siguientes bajan un número: primero a negativo y después al final.
            siguientes = (_Paso.workflow_id == workflow.id) & (_Paso.numero > eliminado.numero)
            self._ejecutar(update(_Paso).where(siguientes).values(numero=-_Paso.numero))
            negativos = (_Paso.workflow_id == workflow.id) & (_Paso.numero < 0)
            self._ejecutar(update(_Paso).where(negativos).values(numero=-_Paso.numero - 1))
            # Las sentencias no actualizan los objetos de la sesión: se descartan para
            # que la lectura final los cargue de nuevo.
            for paso in pasos:
                self._sesion.expunge(paso)

        return self._modificar(id_workflow, eliminar)

    def reordenar_pasos(self, id_workflow: int, ids: list[int]) -> Workflow:
        def reordenar(workflow: WorkflowModelo, pasos: list[PasoWorkflowModelo]) -> None:
            comprobar_nuevo_orden((p.id for p in pasos), ids)
            if not ids:
                return
            afectados = (_Paso.workflow_id == workflow.id) & _Paso.id.in_(ids)
            # Primero todos a negativo, que no choca con ningún número final: si se
            # asignaran directamente, un paso podría tomar el número que aún tiene otro.
            self._ejecutar(update(_Paso).where(afectados).values(numero=-_Paso.numero))
            numeros = {id_paso: numero for numero, id_paso in enumerate(ids, start=1)}
            self._ejecutar(
                update(_Paso).where(afectados).values(numero=case(numeros, value=_Paso.id))
            )
            for paso in pasos:
                self._sesion.expunge(paso)

        return self._modificar(id_workflow, reordenar)

    # --- Asignación a las tareas -----------------------------------------------

    def leer_para_copiar(self, id_workflow: int) -> Workflow | None:
        # Sin confirmar: el bloqueo compartido dura hasta que se guarde la tarea.
        with traducir_conflictos(self._sesion):
            workflow = self._workflow_bloqueado_o_nada(id_workflow, compartido=True)
            if workflow is None:
                return None
            entidad = _a_entidad(workflow, self._pasos_bloqueados(id_workflow, compartido=True))
            textos = self._comentarios_bloqueados([p.id for p in entidad.pasos])
            for paso in entidad.pasos:
                paso.comentarios_para_copiar = textos[paso.id]
                paso.comentarios = len(paso.comentarios_para_copiar)
            return entidad

    def _comentarios_bloqueados(self, ids_pasos: list[int]) -> dict[int, list[str]]:
        """Los textos de los comentarios de esos pasos, por paso y en orden
        cronológico (``creado`` y, a igual instante, por orden de alta), leídos con
        bloqueo compartido (lo último confirmado) en una sola consulta, después de
        bloquear todos los pasos."""
        textos: dict[int, list[str]] = defaultdict(list)
        if not ids_pasos:
            return textos
        consulta = (
            select(ComentarioPasoModelo.paso_id, ComentarioPasoModelo.texto)
            .where(ComentarioPasoModelo.paso_id.in_(ids_pasos))
            .order_by(
                ComentarioPasoModelo.paso_id, ComentarioPasoModelo.creado, ComentarioPasoModelo.id
            )
            .with_for_update(read=True)
        )
        for id_paso, texto in self._sesion.execute(consulta):
            textos[id_paso].append(texto)
        return textos
