FROM python:3.12-slim AS base

COPY --from=ghcr.io/astral-sh/uv:0.11.21 /uv /uvx /usr/local/bin/

WORKDIR /aplicacion

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY . .
RUN uv sync --frozen --no-dev
RUN chmod +x entrypoint.sh

ENV PATH="/aplicacion/.venv/bin:$PATH"

EXPOSE 8000

# Aplica las migraciones de Alembic antes de arrancar; sin esto, un contenedor
# con una base de datos nueva arrancaría sin tablas.
CMD ["./entrypoint.sh"]
