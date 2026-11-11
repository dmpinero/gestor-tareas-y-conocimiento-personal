"""Mensajes de los errores de los grupos de estados, comunes a todas las capas."""

from gestor_tareas.dominio.excepciones import (
    EntidadNoEncontradaError,
    NombreDuplicadoError,
)


def grupo_no_encontrado(id_grupo: int) -> EntidadNoEncontradaError:
    return EntidadNoEncontradaError(f"No existe el grupo de estados con id {id_grupo}")


def estado_no_encontrado(id_grupo: int, id_estado: int) -> EntidadNoEncontradaError:
    return EntidadNoEncontradaError(
        f"No existe el estado con id {id_estado} en el grupo de estados con id {id_grupo}"
    )


def grupo_duplicado(nombre: str) -> NombreDuplicadoError:
    return NombreDuplicadoError(f"Ya existe un grupo de estados llamado «{nombre}»")


def estado_duplicado(nombre: str, nombre_grupo: str) -> NombreDuplicadoError:
    return NombreDuplicadoError(
        f"Ya existe un estado llamado «{nombre}» en el grupo de estados «{nombre_grupo}»"
    )
