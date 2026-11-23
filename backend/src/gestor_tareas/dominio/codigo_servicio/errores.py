"""Mensajes de los errores de los códigos de servicio, comunes a todas las capas."""

from gestor_tareas.dominio.excepciones import EntidadNoEncontradaError, NombreDuplicadoError


def codigo_servicio_no_encontrado(id_codigo: int) -> EntidadNoEncontradaError:
    return EntidadNoEncontradaError(f"No existe el código de servicio con id {id_codigo}")


def codigo_servicio_duplicado(nombre: str) -> NombreDuplicadoError:
    return NombreDuplicadoError(f"Ya existe un código de servicio llamado «{nombre}»")
