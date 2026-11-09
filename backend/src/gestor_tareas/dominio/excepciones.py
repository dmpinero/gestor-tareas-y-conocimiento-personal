class EntidadNoEncontradaError(Exception):
    """Se lanza cuando se busca una entidad por identificador y no existe."""


class NombreDuplicadoError(Exception):
    """Se lanza al intentar crear una entidad cuyo nombre ya está en uso."""


class EntidadConDependenciasError(Exception):
    """Se lanza al intentar eliminar una entidad que tiene otras entidades asociadas."""


class FiltroDeListadoInvalidoError(Exception):
    """Se lanza cuando un listado recibe una combinación inválida de filtros."""
