# syntax=docker/dockerfile:1.7
FROM python:3.13-slim AS builder

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    HF_HOME=/opt/huggingface \
    MODEL_CACHE_DIR=/opt/huggingface/hub

WORKDIR /build

# Some locked Python packages may require a compiler fallback when a wheel is
# unavailable for the active architecture. These tools remain builder-only.
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.lock requirements.lock
RUN python -m pip install --prefix=/install \
        -r requirements.lock

ARG EMBEDDING_REVISION=1110a243fdf4706b3f48f1d95db1a4f5529b4d41
ARG RERANK_REVISION=233902d25c440f23af6f7d6e94d2946bac0bee0a
RUN PYTHONPATH=/install/lib/python3.13/site-packages python -c "from pathlib import Path; from huggingface_hub import snapshot_download; embedding = snapshot_download('sentence-transformers/all-MiniLM-L6-v2', revision='${EMBEDDING_REVISION}', cache_dir='/opt/huggingface/hub'); reranker = snapshot_download('cross-encoder/ms-marco-MiniLM-L-6-v2', revision='${RERANK_REVISION}', cache_dir='/opt/huggingface/hub'); Path('/opt/huggingface/embedding-model').symlink_to(embedding, target_is_directory=True); Path('/opt/huggingface/reranker-model').symlink_to(reranker, target_is_directory=True)"

FROM python:3.13-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HF_HOME=/opt/huggingface \
    MODEL_CACHE_DIR=/opt/huggingface/hub \
    EMBEDDING_MODEL=/opt/huggingface/embedding-model \
    RERANK_MODEL=/opt/huggingface/reranker-model \
    HF_HUB_OFFLINE=1 \
    TRANSFORMERS_OFFLINE=1 \
    HF_DATASETS_OFFLINE=1 \
    HF_HUB_DISABLE_TELEMETRY=1 \
    FLASK_ENV=production \
    RAG_DATA_DIR=/app/Backend/data

RUN apt-get update \
    && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --system app \
    && useradd --system --gid app --create-home app

COPY --from=builder /install /usr/local
COPY --from=builder --chown=app:app /opt/huggingface /opt/huggingface

WORKDIR /app
COPY --chown=app:app . /app/Backend
RUN mkdir -p /app/Backend/data/sqlite /app/Backend/data/faiss /app/Backend/data/uploads \
    && chown -R app:app /app/Backend/data

USER app
EXPOSE 5000

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "1", "--threads", "4", "--timeout", "180", "Backend.app:create_app()"]
