FROM ghcr.io/astral-sh/uv:0.11.25 AS uv
FROM python:3.12-slim-bookworm
COPY --from=uv /uv /usr/local/bin/uv
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy PYTHONDONTWRITEBYTECODE=1
WORKDIR /app
COPY pyproject.toml uv.lock ./
COPY apps/api/pyproject.toml apps/api/pyproject.toml
COPY ml/data/pyproject.toml ml/data/pyproject.toml
COPY apps/api/src apps/api/src
COPY ml/data/src ml/data/src
RUN uv sync --frozen --no-dev --no-editable \
    && groupadd --system alphalens \
    && useradd --system --gid alphalens alphalens
USER alphalens
EXPOSE 8000
CMD ["/app/.venv/bin/uvicorn", "alphalens_api.main:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log"]
