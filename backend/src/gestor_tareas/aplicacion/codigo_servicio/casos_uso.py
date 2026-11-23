from gestor_tareas.aplicacion.reintentos import reintentar_si_hay_conflicto
from gestor_tareas.dominio.codigo_servicio.entidades import CodigoServicio
from gestor_tareas.dominio.codigo_servicio.repositorio import RepositorioCodigosServicio


class _CasoDeUsoCodigosServicio:
    def __init__(self, repositorio: RepositorioCodigosServicio) -> None:
        self._repositorio = repositorio


class ListarCodigosServicio(_CasoDeUsoCodigosServicio):
    def ejecutar(self) -> list[CodigoServicio]:
        return self._repositorio.listar()


class CrearCodigoServicio(_CasoDeUsoCodigosServicio):
    """Da de alta un código de servicio; el nombre no puede repetirse (sin
    mayúsculas)."""

    def ejecutar(self, nombre: str) -> CodigoServicio:
        return reintentar_si_hay_conflicto(lambda: self._repositorio.crear(nombre))


class RenombrarCodigoServicio(_CasoDeUsoCodigosServicio):
    """Cambia el nombre del código de servicio."""

    def ejecutar(self, id_codigo: int, nombre: str) -> CodigoServicio:
        return reintentar_si_hay_conflicto(lambda: self._repositorio.renombrar(id_codigo, nombre))


class EliminarCodigoServicio(_CasoDeUsoCodigosServicio):
    """Elimina el código de servicio del catálogo."""

    def ejecutar(self, id_codigo: int) -> None:
        reintentar_si_hay_conflicto(lambda: self._repositorio.eliminar(id_codigo))
