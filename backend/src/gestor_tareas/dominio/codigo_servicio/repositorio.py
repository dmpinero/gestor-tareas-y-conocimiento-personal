from typing import Protocol

from gestor_tareas.dominio.codigo_servicio.entidades import CodigoServicio


class RepositorioCodigosServicio(Protocol):
    """Puerto de persistencia para el catálogo de códigos de servicio."""

    def listar(self) -> list[CodigoServicio]:
        """Devuelve todos los códigos ordenados por nombre sin distinguir mayúsculas."""
        ...

    def crear(self, nombre: str) -> CodigoServicio:
        """Da de alta un código y confirma. ``NombreDuplicadoError`` si ya existe otro
        con ese nombre sin distinguir mayúsculas."""
        ...

    def renombrar(self, id_codigo: int, nombre: str) -> CodigoServicio:
        """Cambia el nombre y confirma. ``EntidadNoEncontradaError`` si no existe y
        ``NombreDuplicadoError`` si otro código ya tiene ese nombre."""
        ...

    def eliminar(self, id_codigo: int) -> None:
        """Borra el código y confirma. ``EntidadNoEncontradaError`` si no existe."""
        ...
