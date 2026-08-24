# ---- Build stage ----
FROM python:3.14-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_NO_DEV=1

WORKDIR /app

# Install dependencies first, separately from the project code, so this
# (slow) layer is only rebuilt when uv.lock/pyproject.toml actually change.
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-install-project

# Now add the project itself and sync again.
COPY . /app
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked

# ---- Runtime stage ----
FROM python:3.14-slim

RUN useradd --create-home --uid 1000 app
WORKDIR /app

COPY --from=builder --chown=app:app /app /app

USER app
ENV PATH="/app/.venv/bin:$PATH"

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

CMD ["fastapi", "run", "app/main.py", "--port", "8000"]
