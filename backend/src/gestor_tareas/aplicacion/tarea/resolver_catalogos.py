from gestor_tareas.dominio.etiqueta.repositorio import RepositorioEtiquetas
from gestor_tareas.dominio.nombres_catalogo import deduplicar_nombres, ordenar_nombres
from gestor_tareas.dominio.persona.repositorio import RepositorioPersonas
from gestor_tareas.dominio.subestado.repositorio import RepositorioSubestados

type RepositorioCatalogo = RepositorioEtiquetas | RepositorioPersonas | RepositorioSubestados


def resolver_nombres(repositorio: RepositorioCatalogo, nombres: list[str]) -> list[str]:
    """Convierte los nombres pedidos en los nombres guardados en el catálogo.

    Quita los repetidos sin distinguir mayúsculas (se queda la primera grafía),
    reutiliza los existentes con su grafía guardada, da de alta los nuevos y
    devuelve la lista en orden alfabético. Se deduplica también por id, porque
    la base de datos puede considerar iguales nombres que Python distingue.
    """
    elementos = repositorio.obtener_o_crear(deduplicar_nombres(nombres))
    por_id = {elemento.id: elemento.nombre for elemento in elementos}
    return ordenar_nombres(por_id.values())


def resolver_nombre(repositorio: RepositorioCatalogo | None, nombre: str | None) -> str | None:
    """Como ``resolver_nombres`` para un único nombre opcional (el subestado de una
    tarea): devuelve el nombre guardado en el catálogo, o ``None`` si no se indica."""
    if nombre is None:
        return None
    if repositorio is None:
        raise ValueError(f"Falta el repositorio del catálogo para asignar «{nombre}»")
    [guardado] = resolver_nombres(repositorio, [nombre])
    return guardado
