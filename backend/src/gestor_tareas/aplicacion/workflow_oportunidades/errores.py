from gestor_tareas.dominio.excepciones import EntidadNoEncontradaError


def paso_no_encontrado(id_paso: int) -> EntidadNoEncontradaError:
    return EntidadNoEncontradaError(f"No existe el paso del workflow con id {id_paso}")
