ARG BASE_IMAGE=ubuntu:24.04@sha256:534baea6a22c03a63003dbc8dbe78fe34bc0d7e595d9a9dc9834884ff530eb55
FROM ghcr.io/astral-sh/uv:0.12.24@sha256:3af4716e991d6956a41e573eab705d0ee08500cd829ed30293eb8472f372c65a AS uv
FROM ${BASE_IMAGE}
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy PYTHONDONTWRITEBYTECODE=1
WORKDIR /app
# Stable Ubuntu Python 3.12 and OpenMP; frozen application dependencies unchanged.
RUN apt-get update && apt-get upgrade -y \
    && apt-get install -y --no-install-recommends libgomp1 \
    && if ! command -v python3.12; then apt-get install -y --no-install-recommends python3.12 python3.12-venv ca-certificates; fi \
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
COPY workers/alerts workers/alerts
COPY workers/daily workers/daily
COPY workers/providers workers/providers
COPY workers/personal workers/personal
COPY workers/intelligence workers/intelligence
COPY workers/experimental_nse workers/experimental_nse
COPY workers/experimental_nse_v2 workers/experimental_nse_v2
COPY workers/nse_market workers/nse_market
COPY workers/observability.py workers/observability.py
COPY db/alerts db/alerts
COPY db/auth db/auth
COPY db/operations db/operations
COPY db/prospective db/prospective
COPY db/providers db/providers
COPY db/personal-workspace.sql db/personal-workspace.sql
COPY db/experimental-nse.sql db/experimental-nse.sql
COPY db/experimental-nse-v2.sql db/experimental-nse-v2.sql
COPY docs/development/ml-v2-registered-protocol.md docs/development/ml-v2-registered-protocol.md
COPY docs/development/ml-v2-price-only-registered-protocol.md docs/development/ml-v2-price-only-registered-protocol.md
COPY docs/development/ml-sequence-v1-registered-protocol.md docs/development/ml-sequence-v1-registered-protocol.md
COPY docs/development/nse-expanded-forward-protocol-v1.md docs/development/nse-expanded-forward-protocol-v1.md
COPY scripts/verify_p21_runtime.py scripts/verify_p21_runtime.py
# P19 imports only identity/checksum helpers from these existing modules.
# Importing them does not execute their guarded acquisition/replay entry points.
COPY scripts/build_tejhq_research.py scripts/acquire_tejhq_research.py scripts/
# Installer is build-only; no Rust package manager is shipped in the runtime.
# This container toolchain does not change the frozen local research toolchain.
RUN --mount=from=uv,source=/uv,target=/usr/local/bin/uv \
    uv sync --frozen --python python3.12 --no-python-downloads --no-dev --no-editable --no-cache \
    && groupadd --system alphalens \
    && useradd --system --create-home --gid alphalens alphalens
# AlphaLens never mounts filesystems. Remove privilege elevation from retained
# helpers; affected package CVEs remain visible to the unchanged strict scanner.
RUN chmod u-s /usr/bin/mount /usr/bin/umount
USER alphalens
EXPOSE 8000
CMD ["/app/.venv/bin/python", "-m", "alphalens_api", "serve"]
