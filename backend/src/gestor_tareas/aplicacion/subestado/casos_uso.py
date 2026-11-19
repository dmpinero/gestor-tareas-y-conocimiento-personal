from gestor_tareas.aplicacion.reintentos import reintentar_si_hay_conflicto
from gestor_tareas.dominio.subestado.entidades import Subestado
from gestor_tareas.dominio.subestado.repositorio import RepositorioSubestados


class _CasoDeUsoSubestados:
    def __init__(self, repositorio: RepositorioSubestados) -> None:
        self._repositorio = repositorio


class ListarSubestados(_CasoDeUsoSubestados):
    def ejecutar(self) -> list[Subestado]:
        return self._repositorio.listar()


class CrearSubestado(_CasoDeUsoSubestados):
    """Da de alta un subestado; el nombre no puede repetirse (sin mayúsculas)."""

    def ejecutar(self, nombre: str) -> Subestado:
        return reintentar_si_hay_conflicto(lambda: self._repositorio.crear(nombre))


class RenombrarSubestado(_CasoDeUsoSubestados):
    """Cambia el nombre del subestado; sus tareas lo ven con el nombre nuevo."""

    def ejecutar(self, id_subestado: int, nombre: str) -> Subestado:
        return reintentar_si_hay_conflicto(
            lambda: self._repositorio.renombrar(id_subestado, nombre)
        )


class EliminarSubestado(_CasoDeUsoSubestados):
    """Elimina el subestado; sus tareas quedan sin subestado."""

    def ejecutar(self, id_subestado: int) -> None:
        reintentar_si_hay_conflicto(lambda: self._repositorio.eliminar(id_subestado))
