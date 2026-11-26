"""Repositorio del índice local de Notion sobre MySQL (búsqueda FULLTEXT)."""

from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from gestor_tareas.dominio.conocimiento.entidades import (
    EstadoDelIndice,
    FragmentoEncontrado,
    PaginaNotion,
)
from gestor_tareas.infraestructura.persistencia.modelos import (
    FragmentoNotionModelo,
    PaginaNotionModelo,
)
from gestor_tareas.infraestructura.persistencia.repositorios.repositorio_conocimiento_sqlalchemy import (  # noqa: E501
    RepositorioConocimientoSqlAlchemy,
)

_ANTES = datetime(2026, 11, 20, 9, 0, 0, tzinfo=UTC)
_DESPUES = datetime(2026, 11, 25, 9, 0, 0, 500000, tzinfo=UTC)


def _pagina(id_: str, titulo: str, editada_en: datetime = _ANTES) -> PaginaNotion:
    return PaginaNotion(id_, titulo, f"https://www.notion.so/{id_}", editada_en)


def test_guarda_paginas_con_sus_trozos_y_las_sustituye_al_volver_a_guardarlas(
    sesion_bd: Session,
) -> None:
    repositorio = RepositorioConocimientoSqlAlchemy(sesion_bd)

    repositorio.guardar_pagina(_pagina("a", "Receta"), ["uno", "dos", "tres"])
    repositorio.guardar_pagina(_pagina("b", "Reunión"), ["cuatro"])
    repositorio.guardar_pagina(_pagina("a", "Receta nueva", _DESPUES), ["cinco"])

    # La edición se guarda con precisión de segundos y vuelve en UTC.
    assert repositorio.ediciones() == {"a": _DESPUES.replace(microsecond=0), "b": _ANTES}
    filas = sesion_bd.execute(
        select(
            FragmentoNotionModelo.pagina_id,
            FragmentoNotionModelo.orden,
            FragmentoNotionModelo.texto,
        ).order_by(FragmentoNotionModelo.id)
    ).all()
    assert [tuple(f) for f in filas] == [("b", 0, "cuatro"), ("a", 0, "cinco")]
    assert sesion_bd.get(PaginaNotionModelo, "a").titulo == "Receta nueva"
    assert repositorio.estado() == EstadoDelIndice(2, 2, None)


def test_un_titulo_demasiado_largo_se_recorta(sesion_bd: Session) -> None:
    repositorio = RepositorioConocimientoSqlAlchemy(sesion_bd)

    repositorio.guardar_pagina(_pagina("a", "t" * 800), ["x"])

    assert sesion_bd.get(PaginaNotionModelo, "a").titulo == "t" * 500


def test_eliminar_paginas_quita_tambien_sus_trozos(sesion_bd: Session) -> None:
    repositorio = RepositorioConocimientoSqlAlchemy(sesion_bd)
    repositorio.guardar_pagina(_pagina("a", "A"), ["uno", "dos"])
    repositorio.guardar_pagina(_pagina("b", "B"), ["tres"])

    repositorio.eliminar_paginas(["a", "no-existe"])

    assert repositorio.ediciones() == {"b": _ANTES}
    assert sesion_bd.scalar(select(func.count()).select_from(FragmentoNotionModelo)) == 1


def test_busca_por_texto_completo_los_trozos_mas_relevantes_sin_distinguir_tildes(
    sesion_bd: Session,
) -> None:
    repositorio = RepositorioConocimientoSqlAlchemy(sesion_bd)
    repositorio.guardar_pagina(
        _pagina("receta", "Receta de paella"),
        ["La paella lleva arroz bomba y azafrán.", "Se sirve en una paellera grande."],
    )
    repositorio.guardar_pagina(_pagina("reunion", "Reunión"), ["Ana comentó algo de la paella."])
    repositorio.guardar_pagina(_pagina("otra", "Otra"), ["Sin relación con la cocina."])

    encontrados = repositorio.buscar("¿Qué lleva la paella de azafran?", 5)

    assert encontrados[0] == FragmentoEncontrado(
        "receta",
        "Receta de paella",
        "https://www.notion.so/receta",
        "La paella lleva arroz bomba y azafrán.",
    )
    assert {f.pagina_id for f in encontrados} == {"receta", "reunion"}
    assert repositorio.buscar("paella", 1) == encontrados[:1]
    assert repositorio.buscar("dentista", 5) == []
    # Los signos de la búsqueda booleana no rompen la consulta.
    assert repositorio.buscar('+paella -"arroz" *', 5)
    assert repositorio.buscar("* ¿? -", 5) == []


def test_busca_aunque_solo_haya_un_trozo_en_el_indice(sesion_bd: Session) -> None:
    repositorio = RepositorioConocimientoSqlAlchemy(sesion_bd)
    repositorio.guardar_pagina(_pagina("a", "Única"), ["El dentista es el martes."])

    assert [f.texto for f in repositorio.buscar("dentista", 5)] == ["El dentista es el martes."]


def test_solo_una_sincronizacion_a_la_vez_y_la_abandonada_caduca(sesion_bd: Session) -> None:
    repositorio = RepositorioConocimientoSqlAlchemy(sesion_bd)
    ahora = datetime(2026, 11, 26, 12, 0, tzinfo=UTC)
    caducidad = timedelta(minutes=30)

    assert repositorio.empezar_sincronizacion(ahora, caducidad)
    otra = RepositorioConocimientoSqlAlchemy(sesion_bd)
    assert not otra.empezar_sincronizacion(ahora + timedelta(minutes=10), caducidad)
    # Pasada la caducidad, la anterior se da por abandonada.
    assert otra.empezar_sincronizacion(ahora + timedelta(minutes=31), caducidad)

    otra.terminar_sincronizacion(ahora + timedelta(minutes=32))

    assert repositorio.estado().ultima_sincronizacion == ahora + timedelta(minutes=32)
    assert repositorio.empezar_sincronizacion(ahora + timedelta(minutes=33), caducidad)
    repositorio.terminar_sincronizacion(None)
    # Terminar sin éxito libera la sincronización pero no cambia la última.
    assert repositorio.estado().ultima_sincronizacion == ahora + timedelta(minutes=32)
    assert repositorio.empezar_sincronizacion(ahora + timedelta(minutes=34), caducidad)
