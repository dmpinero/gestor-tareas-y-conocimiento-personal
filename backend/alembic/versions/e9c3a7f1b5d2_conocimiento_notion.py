"""índice local de Notion para Conocimiento

Revision ID: e9c3a7f1b5d2
Revises: d7f2b9e4a6c1
Create Date: 2026-11-26 18:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e9c3a7f1b5d2"
down_revision: str | Sequence[str] | None = "d7f2b9e4a6c1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Crea el índice local de Notion, vacío: las páginas, sus trozos (con índice
    FULLTEXT sobre el texto y borrado en cascada desde la página) y la fila del
    estado de la sincronización (nunca sincronizado, ninguna en curso). Ningún otro
    dato cambia."""
    op.create_table(
        "notion_paginas",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("titulo", sa.String(length=500), nullable=False),
        sa.Column("url", sa.String(length=2048), nullable=False),
        sa.Column("editada_en", sa.DateTime(timezone=False), nullable=False),
        sa.Column("sincronizada_en", sa.DateTime(timezone=False), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "notion_fragmentos",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("pagina_id", sa.String(length=36), nullable=False),
        sa.Column("orden", sa.Integer(), nullable=False),
        sa.Column("texto", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(
            ["pagina_id"],
            ["notion_paginas.id"],
            name="fk_notion_fragmentos_pagina",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("pagina_id", "orden", name="uq_notion_fragmentos_pagina_orden"),
    )
    op.create_index(
        "ft_notion_fragmentos_texto", "notion_fragmentos", ["texto"], mysql_prefix="FULLTEXT"
    )
    sincronizacion = op.create_table(
        "notion_sincronizacion",
        sa.Column("id", sa.Integer(), autoincrement=False, nullable=False),
        sa.Column("ultima_sincronizacion", sa.DateTime(timezone=False), nullable=True),
        sa.Column("en_curso_desde", sa.DateTime(timezone=False), nullable=True),
        sa.CheckConstraint("id = 1", name="ck_notion_sincronizacion_una_fila"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.bulk_insert(sincronizacion, [{"id": 1}])


def downgrade() -> None:
    """Quita las tablas: se pierde el índice de Notion (se reconstruye
    sincronizando de nuevo)."""
    op.drop_table("notion_sincronizacion")
    op.drop_index("ft_notion_fragmentos_texto", table_name="notion_fragmentos")
    op.drop_table("notion_fragmentos")
    op.drop_table("notion_paginas")
