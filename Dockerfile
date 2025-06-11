# Removed -slim since we're using dev containers for development
FROM ghcr.io/astral-sh/uv:python3.13-bookworm

WORKDIR /app

COPY .python-version uv.lock pyproject.toml ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv pip install --system . \
    && uv sync --dev

ENV PATH="/app/.venv/bin:$PATH"

COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload", "--reload-dir", "/app"]
