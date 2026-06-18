# ── Stage 1: base ─────────────────────────────────────────────────────────────
FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src

WORKDIR /app

# ── Stage 2: builder ──────────────────────────────────────────────────────────
FROM base AS builder

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --no-cache-dir --prefix=/install -r requirements.txt

# ── Stage 3: production ───────────────────────────────────────────────────────
FROM base AS production

# Copy installed packages from builder
COPY --from=builder /install /usr/local

COPY . .

# Non-root user for security
RUN groupadd -r appuser && useradd -r -g appuser appuser
USER appuser

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

# ── Stage 4: test ─────────────────────────────────────────────────────────────
FROM base AS test

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements-dev.txt .
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements-dev.txt

COPY . .

CMD ["pytest", "--tb=short", "-v"]
