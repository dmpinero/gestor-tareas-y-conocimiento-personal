import re
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, func, insert, or_, select, update
from sqlalchemy.dialects.mysql import match
from sqlalchemy.orm import Session

from gestor_tareas.dominio.conocimiento.entidades import (
    EstadoDelIndice,
    FragmentoEncontrado,
    PaginaNotion,
)
from gestor_tareas.infraestructura.persistencia.modelos import (
    FragmentoNotionModelo,
    PaginaNotionModelo,
    SincronizacionNotionModelo,
)

_ID_ESTADO = 1
_LONGITUD_TITULO = 500
# Lo que no es letra, número o "_" se quita de la búsqueda: el analizador de
# FULLTEXT de InnoDB rechaza algunos signos sueltos (p. ej. "*") incluso en el modo
# de lenguaje natural.
_NO_PALABRA = re.compile(r"[^\w]+")


def _a_bd(instante: datetime) -> datetime:
    """UTC sin zona y con precisión de segundos, como se guarda."""
    return instante.astimezone(UTC).replace(tzinfo=None, microsecond=0)


def _de_bd(instante: datetime | None) -> datetime | None:
    return None if instante is None else instante.replace(tzinfo=UTC)


class RepositorioConocimientoSqlAlchemy:
    """Adaptador de ``RepositorioConocimiento`` sobre MySQL.

    La búsqueda usa el índice FULLTEXT de ``notion_fragmentos.texto`` con
    ``MATCH ... AGAINST (... IN NATURAL LANGUAGE MODE)``: no distingue tildes ni
    mayúsculas (por la intercalación) y los signos de la búsqueda booleana se tratan
    como texto. InnoDB actualiza ese índice al confirmar, por eso cada escritura
    confirma enseguida.

    Que solo haya una sincronización a la vez lo garantiza la fila única de
    ``notion_sincronizacion``: empezar es un ``UPDATE`` condicionado a que no haya
    otra en curso (o a que haya caducado), atómico también entre procesos.
    """

    def __init__(self, sesion: Session) -> None:
        self._sesion = sesion

    def ediciones(self) -> dict[str, datetime]:
        consulta = select(PaginaNotionModelo.id, PaginaNotionModelo.editada_en)
        return {i: editada.replace(tzinfo=UTC) for i, editada in self._sesion.execute(consulta)}

    def guardar_pagina(self, pagina: PaginaNotion, fragmentos: Sequence[str]) -> None:
        self._sesion.execute(
            delete(FragmentoNotionModelo).where(FragmentoNotionModelo.pagina_id == pagina.id)
        )
        self._sesion.merge(
            PaginaNotionModelo(
                id=pagina.id,
                titulo=pagina.titulo[:_LONGITUD_TITULO],
                url=pagina.url,
                editada_en=_a_bd(pagina.editada_en),
                sincronizada_en=_a_bd(datetime.now(UTC)),
            )
        )
        self._sesion.flush()
        if fragmentos:
            self._sesion.execute(
                insert(FragmentoNotionModelo),
                [
                    {"pagina_id": pagina.id, "orden": orden, "texto": texto}
                    for orden, texto in enumerate(fragmentos)
                ],
            )
        self._sesion.commit()

    def eliminar_paginas(self, ids: Sequence[str]) -> None:
        if ids:
            # Los trozos se borran en cascada (clave ajena ON DELETE CASCADE).
            self._sesion.execute(delete(PaginaNotionModelo).where(PaginaNotionModelo.id.in_(ids)))
        self._sesion.commit()

    def buscar(self, consulta: str, limite: int) -> list[FragmentoEncontrado]:
        palabras = _NO_PALABRA.sub(" ", consulta).strip()
        if not palabras:
            return []
        relevancia = match(FragmentoNotionModelo.texto, against=palabras).in_natural_language_mode()
        filas = self._sesion.execute(
            select(
                FragmentoNotionModelo.pagina_id,
                PaginaNotionModelo.titulo,
                PaginaNotionModelo.url,
                FragmentoNotionModelo.texto,
                FragmentoNotionModelo.orden,
            )
            .join(PaginaNotionModelo, PaginaNotionModelo.id == FragmentoNotionModelo.pagina_id)
            .where(relevancia > 0)
            .order_by(relevancia.desc(), FragmentoNotionModelo.id)
            .limit(limite)
        )
        return [
            FragmentoEncontrado(pagina_id=p, titulo=t, url=u, texto=x, orden=o)
            for p, t, u, x, o in filas
        ]

    def estado(self) -> EstadoDelIndice:
        paginas = self._sesion.scalar(select(func.count()).select_from(PaginaNotionModelo))
        fragmentos = self._sesion.scalar(select(func.count()).select_from(FragmentoNotionModelo))
        ultima = self._sesion.scalar(
            select(SincronizacionNotionModelo.ultima_sincronizacion).where(
                SincronizacionNotionModelo.id == _ID_ESTADO
            )
        )
        self._sesion.commit()
        return EstadoDelIndice(
            paginas=paginas or 0, fragmentos=fragmentos or 0, ultima_sincronizacion=_de_bd(ultima)
        )

    def empezar_sincronizacion(self, ahora: datetime, caducidad: timedelta) -> bool:
        # La migración crea la fila; si falta (p. ej., tras vaciar las tablas), se crea.
        self._sesion.execute(
            insert(SincronizacionNotionModelo).prefix_with("IGNORE").values(id=_ID_ESTADO)
        )
        resultado = self._sesion.execute(
            update(SincronizacionNotionModelo)
            .where(
                SincronizacionNotionModelo.id == _ID_ESTADO,
                or_(
                    SincronizacionNotionModelo.en_curso_desde.is_(None),
                    SincronizacionNotionModelo.en_curso_desde < _a_bd(ahora - caducidad),
                ),
            )
            .values(en_curso_desde=_a_bd(ahora))
        )
        self._sesion.commit()
        return resultado.rowcount == 1

    def terminar_sincronizacion(self, terminada_en: datetime | None) -> None:
        valores: dict[str, datetime | None] = {"en_curso_desde": None}
        if terminada_en is not None:
            valores["ultima_sincronizacion"] = _a_bd(terminada_en)
        self._sesion.execute(
            update(SincronizacionNotionModelo)
            .where(SincronizacionNotionModelo.id == _ID_ESTADO)
            .values(**valores)
        )
        self._sesion.commit()
