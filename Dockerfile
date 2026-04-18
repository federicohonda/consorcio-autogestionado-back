FROM python:3.11-slim AS builder

WORKDIR /app

RUN pip install poetry==1.8.3

COPY pyproject.toml poetry.lock* ./
RUN poetry config virtualenvs.in-project true && \
    poetry install --only main --no-root

COPY src/ ./src/

# ── runner ────────────────────────────────────────────────────────────────────
FROM python:3.11-slim AS runner

WORKDIR /app

COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/src /app/src

ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH="/app"

EXPOSE 8000

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
