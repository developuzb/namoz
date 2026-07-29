# syntax=docker/dockerfile:1.7
# =====================================================================
# TAQVIMbot — Production Dockerfile (uv + Python 3.12)
# =====================================================================

# ---- Builder ----
FROM python:3.12-slim-bookworm AS builder

# uv ni o'rnatamiz (rasmiy binary)
COPY --from=ghcr.io/astral-sh/uv:0.5 /uv /uvx /bin/

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Tizim bog'liqliklari (Pillow uchun)
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        libjpeg-dev \
        zlib1g-dev \
        libfreetype6-dev \
    && rm -rf /var/lib/apt/lists/*

# Bog'liqliklarni alohida qatlamga (cache uchun)
COPY pyproject.toml ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --no-dev --no-install-project

# Loyiha kodi
COPY app ./app
COPY alembic ./alembic
COPY alembic.ini ./
COPY static ./static

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --no-dev

# =====================================================================
# ---- Runtime ----
# =====================================================================
FROM python:3.12-slim-bookworm AS runtime

# Runtime kutubxonalari (Pillow uchun)
RUN apt-get update && apt-get install -y --no-install-recommends \
        libjpeg62-turbo \
        zlib1g \
        libfreetype6 \
        tzdata \
        curl \
    && rm -rf /var/lib/apt/lists/*

# Tashkent vaqt zonasi
ENV TZ=Asia/Tashkent
RUN ln -sf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# Non-root foydalanuvchi (xavfsizlik)
RUN groupadd --system --gid 1000 botuser \
    && useradd --system --uid 1000 --gid botuser --create-home botuser

WORKDIR /app

# Builder dan to'liq nusxa (venv + kod)
COPY --from=builder --chown=botuser:botuser /app /app

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONPATH="/app" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Volume kataloglarini tayyorlaymiz
RUN mkdir -p /app/data/images /app/logs \
    && chown -R botuser:botuser /app/data /app/logs

# Entrypoint (avtomatik migratsiya + start)
COPY --chown=botuser:botuser docker-entrypoint.sh /app/docker-entrypoint.sh
RUN chmod +x /app/docker-entrypoint.sh

USER botuser

# Healthcheck — log faylga qarab
HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
    CMD test -f /app/logs/bot.log || exit 1

ENTRYPOINT ["/app/docker-entrypoint.sh"]
