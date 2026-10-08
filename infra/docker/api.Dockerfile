FROM ghcr.io/astral-sh/uv:0.12.23 AS uv
FROM python:3.12-slim-bookworm
COPY --from=uv /uv /usr/local/bin/uv
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy PYTHONDONTWRITEBYTECODE=1
WORKDIR /app
# LightGBM CPU runtime uses Debian's free OpenMP runtime.
RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/*
COPY pyproject.toml uv.lock ./
COPY apps/api/pyproject.toml apps/api/pyproject.toml
COPY ml/data/pyproject.toml ml/data/pyproject.toml
COPY ml/features/pyproject.toml ml/features/pyproject.toml
COPY ml/labels/pyproject.toml ml/labels/pyproject.toml
COPY ml/training/pyproject.toml ml/training/pyproject.toml
COPY ml/evaluation/pyproject.toml ml/evaluation/pyproject.toml
COPY backtesting/pyproject.toml backtesting/pyproject.toml
COPY decision/pyproject.toml decision/pyproject.toml
COPY portfolio/pyproject.toml portfolio/pyproject.toml
COPY apps/api/src apps/api/src
COPY ml/data/src ml/data/src
COPY ml/features/src ml/features/src
COPY ml/labels/src ml/labels/src
COPY ml/training/src ml/training/src
COPY ml/evaluation/src ml/evaluation/src
COPY backtesting/src backtesting/src
COPY decision/src decision/src
COPY portfolio/src portfolio/src
RUN uv sync --frozen --no-dev --no-editable \
    && groupadd --system alphalens \
    && useradd --system --create-home --gid alphalens alphalens
USER alphalens
EXPOSE 8000
CMD ["/app/.venv/bin/uvicorn", "alphalens_api.main:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log"]
