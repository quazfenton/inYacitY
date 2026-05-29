FROM python:3.11-slim AS builder

WORKDIR /app

RUN apt-get update && apt-get install -y \
    gcc g++ make libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt


FROM python:3.11-slim AS runner

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /install /usr/local

WORKDIR /app

RUN pip install --no-cache-dir playwright \
    && playwright install --with-deps chromium \
    && rm -rf /root/.cache/pip

COPY . .

RUN mkdir -p logs

RUN useradd --create-home --shell /bin/bash --uid 1000 --user-group appuser

RUN chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

CMD ["gunicorn", "main:app", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "-b", "0.0.0.0:8000"]