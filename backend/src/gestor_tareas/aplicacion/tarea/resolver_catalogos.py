from gestor_tareas.dominio.etiqueta.repositorio import RepositorioEtiquetas
from gestor_tareas.dominio.nombres_catalogo import deduplicar_nombres, ordenar_nombres
from gestor_tareas.dominio.persona.repositorio import RepositorioPersonas


def resolver_nombres(
    repositorio: RepositorioEtiquetas | RepositorioPersonas, nombres: list[str]
) -> list[str]:
    """Convierte los nombres pedidos en los nombres guardados en el catálogo.

    Quita los repetidos sin distinguir mayúsculas (se queda la primera grafía),
    reutiliza los existentes con su grafía guardada, da de alta los nuevos y
    devuelve la lista en orden alfabético. Se deduplica también por id, porque
    la base de datos puede considerar iguales nombres que Python distingue.
    """
    elementos = repositorio.obtener_o_crear(deduplicar_nombres(nombres))
    por_id = {elemento.id: elemento.nombre for elemento in elementos}
    return ordenar_nombres(por_id.values())
