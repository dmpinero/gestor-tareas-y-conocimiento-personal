from typing import Protocol

from gestor_tareas.dominio.subestado.entidades import Subestado


class RepositorioSubestados(Protocol):
    """Puerto de persistencia para el catálogo de subestados."""

    def listar(self) -> list[Subestado]:
        """Devuelve todos los subestados ordenados por nombre sin distinguir mayúsculas."""
        ...

    def obtener_o_crear(self, nombres: list[str]) -> list[Subestado]:
        """Como ``RepositorioEtiquetas.obtener_o_crear``: devuelve, en el mismo orden,
        el subestado de cada nombre, reutilizando el que exista sin distinguir
        mayúsculas y dando de alta los que falten. No confirma la transacción."""
        ...

    def crear(self, nombre: str) -> Subestado:
        """Da de alta un subestado y confirma. ``NombreDuplicadoError`` si ya existe
        otro con ese nombre sin distinguir mayúsculas."""
        ...

    def renombrar(self, id_subestado: int, nombre: str) -> Subestado:
        """Cambia el nombre y confirma (lo ven todas sus tareas).
        ``EntidadNoEncontradaError`` si no existe y ``NombreDuplicadoError`` si otro
        subestado ya tiene ese nombre."""
        ...

    def eliminar(self, id_subestado: int) -> None:
        """Borra el subestado y confirma; sus tareas quedan sin subestado.
        ``EntidadNoEncontradaError`` si no existe."""
        ...
