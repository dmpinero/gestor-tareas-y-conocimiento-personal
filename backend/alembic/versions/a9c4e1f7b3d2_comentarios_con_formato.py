"""comentarios con formato

Revision ID: a9c4e1f7b3d2
Revises: d2a8e5c3f7b1
Create Date: 2026-11-13 12:00:00.000000

"""

import re
from collections.abc import Callable, Sequence
from html import escape, unescape

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a9c4e1f7b3d2"
down_revision: str | Sequence[str] | None = "d2a8e5c3f7b1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Las tres tablas de comentarios: de las tareas, de las subtareas y de los pasos.
_TABLAS = ("comentarios", "comentarios_subtarea", "comentarios_paso_workflow")

# Longitud de la columna antes de esta revisión.
_LONGITUD_ANTERIOR = 500

_SALTO_DE_LINEA = re.compile(r"\r\n|\r|\n")
_FIN_DE_LINEA_HTML = re.compile(r"</p\s*>|</li\s*>|<br\s*/?>", re.IGNORECASE)
_ETIQUETA = re.compile(r"<[^>]*>")


def _a_html(texto: str) -> str:
    """Texto plano a HTML: un párrafo por línea, escapado (una línea vacía es
    ``<p></p>``). Es la misma regla que aplica la API a un texto sin etiquetas; se
    copia aquí para que la migración no dependa del código de la aplicación."""
    return "".join(f"<p>{escape(linea, quote=False)}</p>" for linea in _SALTO_DE_LINEA.split(texto))


def _a_texto(html: str) -> str:
    """HTML a texto plano: el fin de cada párrafo o elemento de lista y cada ``<br>``
    son saltos de línea, el resto de las etiquetas se quitan y las entidades se
    decodifican; se recorta y se trunca a la longitud anterior de la columna."""
    texto = unescape(_ETIQUETA.sub("", _FIN_DE_LINEA_HTML.sub("\n", html)))
    return texto.strip()[:_LONGITUD_ANTERIOR]


def _convertir(tabla: str, conversion: Callable[[str], str]) -> None:
    conexion = op.get_bind()
    filas = conexion.execute(sa.text(f"SELECT id, texto FROM {tabla}")).all()  # noqa: S608
    cambios = [{"id": id_, "texto": conversion(texto)} for id_, texto in filas]
    if cambios:
        conexion.execute(
            sa.text(f"UPDATE {tabla} SET texto = :texto WHERE id = :id"),  # noqa: S608
            cambios,
        )


def upgrade() -> None:
    """Pasa los comentarios de texto plano a HTML saneado.

    La columna ``texto`` de las tres tablas de comentarios pasa de ``VARCHAR(500)``
    a ``TEXT`` (el HTML ocupa más que su texto visible), y cada comentario que ya
    existía se convierte a HTML con la regla del texto plano: se escapan sus
    caracteres especiales (``<``, ``>``, ``&``) y cada línea pasa a ser un párrafo,
    así que se ve igual que antes, con sus saltos de línea. El resto de los datos
    no cambia.
    """
    for tabla in _TABLAS:
        op.alter_column(
            tabla,
            "texto",
            existing_type=sa.String(length=_LONGITUD_ANTERIOR),
            type_=sa.Text(),
            existing_nullable=False,
        )
        _convertir(tabla, _a_html)


def downgrade() -> None:
    """Vuelve a los comentarios de texto plano.

    Cada comentario pasa de HTML a texto plano: los párrafos, los elementos de las
    listas y los ``<br>`` se convierten en saltos de línea, se quitan las demás
    etiquetas y se decodifican las entidades; se recortan los extremos y se trunca
    a 500 caracteres. El formato (negritas, colores, enlaces…) se pierde. Después
    la columna ``texto`` de las tres tablas vuelve a ser ``VARCHAR(500)``.
    """
    for tabla in _TABLAS:
        _convertir(tabla, _a_texto)
        op.alter_column(
            tabla,
            "texto",
            existing_type=sa.Text(),
            type_=sa.String(length=_LONGITUD_ANTERIOR),
            existing_nullable=False,
        )
