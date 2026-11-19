"""Mensajes de los errores de los subestados, comunes a todas las capas."""

from gestor_tareas.dominio.excepciones import EntidadNoEncontradaError, NombreDuplicadoError


def subestado_no_encontrado(id_subestado: int) -> EntidadNoEncontradaError:
    return EntidadNoEncontradaError(f"No existe el subestado con id {id_subestado}")


def subestado_duplicado(nombre: str) -> NombreDuplicadoError:
    return NombreDuplicadoError(f"Ya existe un subestado llamado «{nombre}»")
