from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from gestor_tareas.dominio.etiqueta.entidades import Etiqueta
from gestor_tareas.dominio.nombres_catalogo import clave_orden_nombre
from gestor_tareas.dominio.persona.entidades import Persona
from gestor_tareas.infraestructura.persistencia.modelos import EtiquetaModelo, PersonaModelo


class _RepositorioCatalogoSqlAlchemy[E: (Etiqueta, Persona), M: (EtiquetaModelo, PersonaModelo)]:
    """Catálogo de nombres únicos sin distinguir mayúsculas (etiquetas o personas).

    La comparación de nombres la hace MySQL con la intercalación de la columna
    (ver ``INTERCALACION_NOMBRES_CATALOGO``), que también respalda el índice único.
    """

    _modelo: type[M]
    _entidad: type[E]

    def __init__(self, sesion: Session) -> None:
        self._sesion = sesion

    def listar(self) -> list[E]:
        modelos = self._sesion.scalars(select(self._modelo)).all()
        entidades = [self._a_entidad(m) for m in modelos]
        return sorted(entidades, key=lambda e: (*clave_orden_nombre(e.nombre), e.id))

    def obtener_o_crear(self, nombres: list[str]) -> list[E]:
        return [self._a_entidad(self._obtener_o_crear_uno(nombre)) for nombre in nombres]

    def _obtener_o_crear_uno(self, nombre: str) -> M:
        existente = self._buscar(nombre)
        if existente is not None:
            return existente
        try:
            # El SAVEPOINT permite deshacer solo esta inserción si choca con el
            # índice único, sin perder el resto de la transacción de la petición.
            with self._sesion.begin_nested():
                nuevo = self._modelo(nombre=nombre)
                self._sesion.add(nuevo)
            return nuevo
        except IntegrityError:
            # Otra petición dio de alta el mismo nombre entre la búsqueda y la
            # inserción. Con REPEATABLE READ una lectura normal seguiría viendo la
            # instantánea antigua: la lectura con bloqueo (FOR SHARE) lee la fila
            # ya confirmada.
            concurrente = self._buscar(nombre, con_bloqueo=True)
            if concurrente is None:
                raise
            return concurrente

    def _buscar(self, nombre: str, *, con_bloqueo: bool = False) -> M | None:
        consulta = select(self._modelo).where(self._modelo.nombre == nombre)
        if con_bloqueo:
            consulta = consulta.with_for_update(read=True)
        return self._sesion.scalars(consulta).first()

    def _a_entidad(self, modelo: M) -> E:
        return self._entidad(id=modelo.id, nombre=modelo.nombre)


class RepositorioEtiquetasSqlAlchemy(_RepositorioCatalogoSqlAlchemy[Etiqueta, EtiquetaModelo]):
    _modelo = EtiquetaModelo
    _entidad = Etiqueta


class RepositorioPersonasSqlAlchemy(_RepositorioCatalogoSqlAlchemy[Persona, PersonaModelo]):
    _modelo = PersonaModelo
    _entidad = Persona
