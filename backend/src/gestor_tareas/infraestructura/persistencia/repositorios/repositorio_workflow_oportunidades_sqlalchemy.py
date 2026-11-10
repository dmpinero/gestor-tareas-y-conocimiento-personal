"""Pasos del workflow de las oportunidades sobre MySQL.

Las altas, bajas y reordenaciones cambian los números de varios pasos a la vez y
deben dejarlos en 1..n, sin huecos ni repetidos, aunque lleguen a la vez. Para
ello cada una:

1. Toma un bloqueo con nombre de MySQL (``GET_LOCK``), que pone en fila a todas
   las que cambian números. Sin él, dos altas sobre el workflow vacío solo toman
   bloqueos de hueco, que son compatibles entre sí, y acaban en interbloqueo.
2. Lee todos los pasos con ``SELECT ... FOR UPDATE``. La lectura con bloqueo ve lo
   último confirmado (no la instantánea de la transacción) y espera a que termine
   quien aún tenga los pasos bloqueados.
3. Renumera en dos fases (números negativos y después los finales), porque la
   restricción única de ``numero`` se comprueba fila a fila.

El bloqueo con nombre es de la conexión, no de la transacción: se libera justo
antes de confirmar, mientras la conexión sigue siendo la de la sesión (al
confirmar vuelve al pool). Quien lo toma a continuación espera en el paso 2 a que
se confirme la transacción anterior, que ya no pide ningún otro bloqueo, así que
no puede haber interbloqueo entre ellas.
"""

from collections.abc import Callable, Iterator, Sequence
from contextlib import contextmanager

from sqlalchemy import Connection, case, delete, select, text, update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from gestor_tareas.dominio.excepciones import ConflictoDeConcurrenciaError
from gestor_tareas.dominio.workflow_oportunidades.entidades import PasoWorkflowOportunidad
from gestor_tareas.dominio.workflow_oportunidades.orden import comprobar_nuevo_orden
from gestor_tareas.infraestructura.persistencia.modelos import PasoWorkflowOportunidadModelo
from gestor_tareas.infraestructura.persistencia.repositorios.conflictos import traducir_conflictos

_Modelo = PasoWorkflowOportunidadModelo

NOMBRE_BLOQUEO_WORKFLOW = "gestor_tareas.pasos_workflow_oportunidades"
_ESPERA_BLOQUEO_SEGUNDOS = 10


def _a_entidad(
    modelo: PasoWorkflowOportunidadModelo, numero: int | None = None
) -> PasoWorkflowOportunidad:
    return PasoWorkflowOportunidad(
        id=modelo.id, numero=modelo.numero if numero is None else numero, nombre=modelo.nombre
    )


def _liberar_bloqueo(conexion: Connection) -> None:
    """Libera el bloqueo con nombre; si no se puede, cierra la conexión.

    MySQL libera los bloqueos con nombre de una conexión al cerrarla: así una
    conexión que vuelve al pool nunca se queda con el bloqueo.
    """
    try:
        conexion.execute(text("DO RELEASE_LOCK(:nombre)"), {"nombre": NOMBRE_BLOQUEO_WORKFLOW})
    except SQLAlchemyError:
        conexion.invalidate()


class RepositorioWorkflowOportunidadesSqlAlchemy:
    def __init__(self, sesion: Session) -> None:
        self._sesion = sesion

    @contextmanager
    def _workflow_bloqueado(self) -> Iterator[None]:
        """Ejecuta el bloque con el bloqueo con nombre del workflow."""
        conexion = self._sesion.connection()
        obtenido = conexion.execute(
            text("SELECT GET_LOCK(:nombre, :espera)"),
            {"nombre": NOMBRE_BLOQUEO_WORKFLOW, "espera": _ESPERA_BLOQUEO_SEGUNDOS},
        ).scalar()
        if obtenido != 1:
            raise ConflictoDeConcurrenciaError(
                "Otra operación sobre el workflow tiene el bloqueo desde hace demasiado"
            )
        try:
            yield
            self._sesion.flush()
        finally:
            _liberar_bloqueo(conexion)

    def _modificar[T](self, operacion: Callable[[], T]) -> T:
        """Ejecuta la operación en una transacción con el workflow bloqueado.

        Si falla, deshace la transacción entera; un interbloqueo o una espera
        agotada se traducen en ``ConflictoDeConcurrenciaError``.
        """
        with traducir_conflictos(self._sesion):
            try:
                with self._workflow_bloqueado():
                    resultado = operacion()
            except BaseException:
                self._sesion.rollback()
                raise
            self._sesion.commit()
        return resultado

    def _pasos_bloqueados(self) -> list[PasoWorkflowOportunidadModelo]:
        """Todos los pasos, leídos con bloqueo (lo último confirmado), por número.

        Se bloquean en orden de clave primaria, siempre el mismo. ``populate_existing``
        sustituye los datos de los objetos que la sesión ya tuviera cargados.
        """
        consulta = (
            select(_Modelo)
            .order_by(_Modelo.id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        return sorted(self._sesion.scalars(consulta), key=lambda paso: paso.numero)

    def _ejecutar(self, sentencia) -> None:
        self._sesion.execute(sentencia.execution_options(synchronize_session=False))

    def listar_pasos(self) -> list[PasoWorkflowOportunidad]:
        modelos = self._sesion.scalars(select(_Modelo).order_by(_Modelo.numero)).all()
        return [_a_entidad(m) for m in modelos]

    def anadir_paso(self, nombre: str) -> PasoWorkflowOportunidad:
        def anadir() -> PasoWorkflowOportunidad:
            pasos = self._pasos_bloqueados()
            modelo = _Modelo(nombre=nombre, numero=(pasos[-1].numero if pasos else 0) + 1)
            self._sesion.add(modelo)
            self._sesion.flush()
            return _a_entidad(modelo)

        return self._modificar(anadir)

    def renombrar_paso(self, id_paso: int, nombre: str) -> PasoWorkflowOportunidad | None:
        # No cambia números: basta con bloquear la fila del paso.
        with traducir_conflictos(self._sesion):
            consulta = (
                select(_Modelo)
                .where(_Modelo.id == id_paso)
                .with_for_update()
                .execution_options(populate_existing=True)
            )
            modelo = self._sesion.scalars(consulta).one_or_none()
            if modelo is None:
                self._sesion.rollback()
                return None
            modelo.nombre = nombre
            self._sesion.flush()
            # Antes de confirmar: después, leerlo de nuevo podría no encontrarlo.
            paso = _a_entidad(modelo)
            self._sesion.commit()
        return paso

    def eliminar_paso(self, id_paso: int) -> bool:
        def eliminar() -> bool:
            eliminado = next((p for p in self._pasos_bloqueados() if p.id == id_paso), None)
            if eliminado is None:
                return False
            self._ejecutar(delete(_Modelo).where(_Modelo.id == id_paso))
            # Los siguientes bajan un número: primero a negativo y después al final.
            self._ejecutar(
                update(_Modelo)
                .where(_Modelo.numero > eliminado.numero)
                .values(numero=-_Modelo.numero)
            )
            self._ejecutar(
                update(_Modelo).where(_Modelo.numero < 0).values(numero=-_Modelo.numero - 1)
            )
            self._sesion.expunge(eliminado)
            return True

        return self._modificar(eliminar)

    def reordenar_pasos(self, ids: list[int]) -> list[PasoWorkflowOportunidad]:
        def reordenar() -> list[PasoWorkflowOportunidad]:
            pasos = self._pasos_bloqueados()
            comprobar_nuevo_orden((p.id for p in pasos), ids)
            if not ids:
                return []
            self._renumerar(ids)
            por_id = {p.id: p for p in pasos}
            return [_a_entidad(por_id[i], numero) for numero, i in enumerate(ids, start=1)]

        return self._modificar(reordenar)

    def _renumerar(self, ids: Sequence[int]) -> None:
        """Da a cada paso su posición en ``ids`` (desde 1).

        Primero pasan todos a negativo, que no choca con ningún número final: si se
        asignaran directamente, un paso podría tomar el número que aún tiene otro.
        """
        afectados = _Modelo.id.in_(ids)
        self._ejecutar(update(_Modelo).where(afectados).values(numero=-_Modelo.numero))
        posiciones = {id_paso: numero for numero, id_paso in enumerate(ids, start=1)}
        self._ejecutar(
            update(_Modelo).where(afectados).values(numero=case(posiciones, value=_Modelo.id))
        )
