"""Casos de uso de los grupos de estados (Ajustes → Grupos de estados).

Cada operación es una transacción completa del repositorio: si choca con otra
petición simultánea, se repite entera.
"""

from gestor_tareas.aplicacion.reintentos import reintentar_si_hay_conflicto
from gestor_tareas.dominio.grupo_estados.entidades import GrupoEstados
from gestor_tareas.dominio.grupo_estados.repositorio import RepositorioGruposEstados


class _CasoDeUsoGrupos:
    def __init__(self, repositorio: RepositorioGruposEstados) -> None:
        self._repositorio = repositorio


class ListarGruposEstados(_CasoDeUsoGrupos):
    """Todos los grupos por nombre, con sus estados por posición y sus tareas."""

    def ejecutar(self) -> list[GrupoEstados]:
        return self._repositorio.listar()


class CrearGrupoEstados(_CasoDeUsoGrupos):
    """Crea un grupo sin estados; el nombre no puede repetirse (sin mayúsculas)."""

    def ejecutar(self, nombre: str) -> GrupoEstados:
        return reintentar_si_hay_conflicto(lambda: self._repositorio.crear(nombre))


class RenombrarGrupoEstados(_CasoDeUsoGrupos):
    """Cambia el nombre del grupo; sus estados y sus tareas no cambian."""

    def ejecutar(self, id_grupo: int, nombre: str) -> GrupoEstados:
        return reintentar_si_hay_conflicto(lambda: self._repositorio.renombrar(id_grupo, nombre))


class EliminarGrupoEstados(_CasoDeUsoGrupos):
    """Elimina el grupo con sus estados; sus tareas quedan sin grupo ni estado."""

    def ejecutar(self, id_grupo: int) -> None:
        reintentar_si_hay_conflicto(lambda: self._repositorio.eliminar(id_grupo))


class AnadirEstado(_CasoDeUsoGrupos):
    """Añade un estado al final del grupo; el nombre no puede repetirse en el grupo."""

    def ejecutar(self, id_grupo: int, nombre: str) -> GrupoEstados:
        return reintentar_si_hay_conflicto(
            lambda: self._repositorio.anadir_estado(id_grupo, nombre)
        )


class RenombrarEstado(_CasoDeUsoGrupos):
    """Cambia el nombre de un estado del grupo; su posición no cambia."""

    def ejecutar(self, id_grupo: int, id_estado: int, nombre: str) -> GrupoEstados:
        return reintentar_si_hay_conflicto(
            lambda: self._repositorio.renombrar_estado(id_grupo, id_estado, nombre)
        )


class EliminarEstado(_CasoDeUsoGrupos):
    """Elimina un estado del grupo y renumera los siguientes.

    Si tiene tareas, hay que indicar en ``mover_a`` otro estado del grupo, al que
    pasan antes de eliminarlo (ver ``comprobar_destino_de_las_tareas``). La
    comprobación la hace el repositorio en la misma transacción, con el número de
    tareas que el estado tiene en ese momento.
    """

    def ejecutar(self, id_grupo: int, id_estado: int, mover_a: int | None) -> GrupoEstados:
        return reintentar_si_hay_conflicto(
            lambda: self._repositorio.eliminar_estado(id_grupo, id_estado, mover_a)
        )


class ReordenarEstados(_CasoDeUsoGrupos):
    """Da a los estados del grupo las posiciones del orden recibido (el primero, la 1).

    ``ids`` debe incluir cada estado del grupo exactamente una vez; si no, se lanza
    ``OrdenDeEstadosInvalidoError`` y no cambia nada.
    """

    def ejecutar(self, id_grupo: int, ids: list[int]) -> GrupoEstados:
        return reintentar_si_hay_conflicto(
            lambda: self._repositorio.reordenar_estados(id_grupo, ids)
        )
