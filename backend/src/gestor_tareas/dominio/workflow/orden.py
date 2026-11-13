from collections import Counter
from collections.abc import Iterable, Sequence

from gestor_tareas.dominio.excepciones import OrdenDePasosInvalidoError


def _enumerar(ids: Iterable[int]) -> str:
    return ", ".join(str(i) for i in sorted(ids))


def comprobar_nuevo_orden(ids_actuales: Iterable[int], ids_nuevos: Sequence[int]) -> None:
    """Comprueba que el nuevo orden incluye cada paso actual exactamente una vez.

    Lanza ``OrdenDePasosInvalidoError`` indicando los ids repetidos, los que faltan
    y los que no son del workflow.
    """
    actuales = set(ids_actuales)
    repetidos = {i for i, veces in Counter(ids_nuevos).items() if veces > 1}
    faltan = actuales - set(ids_nuevos)
    desconocidos = set(ids_nuevos) - actuales
    problemas = [
        f"{etiqueta}: {_enumerar(ids)}"
        for etiqueta, ids in (
            ("repetidos", repetidos),
            ("faltan", faltan),
            ("no son del workflow", desconocidos),
        )
        if ids
    ]
    if problemas:
        raise OrdenDePasosInvalidoError(
            "El nuevo orden debe incluir cada paso del workflow exactamente una vez "
            f"({'; '.join(problemas)})"
        )
