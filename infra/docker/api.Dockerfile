FROM ghcr.io/astral-sh/uv:0.12.24@sha256:3af4716e991d6956a41e573eab705d0ee08500cd829ed30293eb8472f372c65a AS uv
FROM python:3.12.15-slim-trixie@sha256:05cda9777409a9c3ffddd94a4c476b79f0769a0b4857f0c7ed9226b6800b0d6f
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy PYTHONDONTWRITEBYTECODE=1
WORKDIR /app
# LightGBM CPU runtime uses Debian's free OpenMP runtime.
RUN apt-get update && apt-get upgrade -y \
    && apt-get install -y --no-install-recommends libgomp1 \
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
# Installer is build-only; no Rust package manager is shipped in the runtime.
# This container toolchain does not change the frozen local research toolchain.
RUN --mount=from=uv,source=/uv,target=/usr/local/bin/uv \
    uv sync --frozen --no-dev --no-editable --no-cache \
    && groupadd --system alphalens \
    && useradd --system --create-home --gid alphalens alphalens
USER alphalens
EXPOSE 8000
CMD ["/app/.venv/bin/uvicorn", "alphalens_api.main:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log"]
