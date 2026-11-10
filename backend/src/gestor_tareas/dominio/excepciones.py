class EntidadNoEncontradaError(Exception):
    """Se lanza cuando se busca una entidad por identificador y no existe."""


class NombreDuplicadoError(Exception):
    """Se lanza al intentar crear una entidad cuyo nombre ya está en uso."""


class EntidadConDependenciasError(Exception):
    """Se lanza al intentar eliminar una entidad que tiene otras entidades asociadas."""


class FiltroDeListadoInvalidoError(Exception):
    """Se lanza cuando un listado recibe una combinación inválida de filtros."""


class ConflictoDeConcurrenciaError(Exception):
    """Se lanza cuando la operación chocó con otra simultánea y se deshizo entera.

    Por ejemplo, un interbloqueo en la base de datos. Ya no queda nada a medias:
    puede reintentarse la operación completa desde el principio.
    """


class OrdenDePasosInvalidoError(Exception):
    """Se lanza al reordenar el workflow con una lista que no es una permutación
    exacta de sus pasos (con repetidos, con pasos de menos o con ids que no existen)."""
