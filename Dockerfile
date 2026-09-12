# syntax=docker/dockerfile:1
#
# Multi-stage (14_estandares_python_moderno.md): la etapa `build` instala
# dependencias con `uv` y cachea la resolución; la etapa `runtime` copia
# únicamente el resultado y corre como usuario sin privilegios.
#
# El entrypoint usa `uvicorn` (no `fastapi run`): el proyecto depende de
# `fastapi` + `uvicorn[standard]` por separado, no del extra `fastapi[standard]`
# que instalaría `fastapi-cli`.
FROM python:3.12-slim AS build

COPY --from=ghcr.io/astral-sh/uv:0.8.21 /uv /uvx /bin/

WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy

# 1. Instalar dependencias con caché, antes de copiar el código fuente:
#    cambios en app/ no invalidan esta capa.
COPY uv.lock pyproject.toml ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --no-install-project --no-dev

# 2. Copiar el resto del repo y resolver contra el lockfile exacto.
COPY . .
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

# --- Etapa de runtime: liviana, sin herramientas de build, usuario no-root ---
FROM python:3.12-slim AS runtime

ENV PATH="/app/.venv/bin:$PATH"

RUN groupadd -g 1001 appgroup && \
    useradd -u 1001 -g appgroup -m -d /app -s /bin/false appuser

WORKDIR /app
COPY --from=build --chown=appuser:appgroup /app .

USER appuser
EXPOSE 8000

ENTRYPOINT ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
