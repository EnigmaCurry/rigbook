FROM node:22-slim AS frontend
WORKDIR /app
COPY frontend/package.json frontend/package-lock.json frontend/
RUN cd frontend && npm ci
COPY frontend/ frontend/
COPY src/ src/
RUN cd frontend && npm run build

FROM python:3.12-slim AS backend
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
WORKDIR /app
COPY pyproject.toml uv.lock ./
COPY src/ src/
RUN uv sync --no-dev --frozen

FROM python:3.12-slim
WORKDIR /app
COPY --from=backend /app /app
COPY --from=frontend /app/src/rigbook/static src/rigbook/static
EXPOSE 8073
CMD [".venv/bin/rigbook", "--server"]
