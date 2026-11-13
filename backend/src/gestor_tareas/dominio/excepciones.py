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
    """Se lanza al reordenar un workflow con una lista que no es una permutación
    exacta de sus pasos (con repetidos, con pasos de menos o con ids que no son del
    workflow)."""


class OrdenDeEstadosInvalidoError(Exception):
    """Se lanza al reordenar los estados de un grupo con una lista que no es una
    permutación exacta de sus estados (con repetidos, con estados de menos o con ids
    que no son del grupo)."""


class AsignacionDeEstadoInvalidaError(Exception):
    """Se lanza al dar a una tarea un grupo de estados o un estado que no admite: un
    grupo que no existe o sin estados, o un estado que no es del grupo de la tarea."""


class AsignacionDeWorkflowInvalidaError(Exception):
    """Se lanza al dar a una tarea un workflow que no existe."""
