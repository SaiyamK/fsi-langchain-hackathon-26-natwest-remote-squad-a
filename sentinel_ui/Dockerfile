# Sentinel analyst workspace: one container. Build context = the repo root:
#   docker build -f sentinel_ui/Dockerfile -t sentinel-aml-ui .
# No model keys are baked in. Without them it runs offline, or replays sentinel_ui/recordings/world0.json.

FROM node:22-alpine AS web
WORKDIR /web
RUN corepack enable
COPY sentinel_ui/web/package.json sentinel_ui/web/pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile
COPY sentinel_ui/web/ ./
RUN pnpm build

FROM python:3.13-slim AS deps
COPY --from=ghcr.io/astral-sh/uv:0.8.17 /uv /bin/uv
WORKDIR /src
# uv needs every workspace member's pyproject to read the lock
COPY pyproject.toml uv.lock ./
COPY sentinel_aml_agent/pyproject.toml sentinel_aml_agent/
COPY sentinel_ui/api/pyproject.toml sentinel_ui/api/
RUN uv export --frozen --no-dev --no-hashes --no-emit-workspace --package sentinel-aml-agent -o /req-agent.txt \
 && uv export --frozen --no-dev --no-hashes --no-emit-workspace --package sentinel-ui-api -o /req-api.txt \
 && uv pip install --system --no-cache -r /req-agent.txt -r /req-api.txt

FROM deps AS runtime
WORKDIR /app
COPY sentinel_aml_agent/ sentinel_aml_agent/
COPY sentinel_ui/api/ sentinel_ui/api/
COPY sentinel_ui/recordings/ sentinel_ui/recordings/
COPY --from=web /web/dist sentinel_ui/web/dist
ENV PYTHONUNBUFFERED=1 PYTHONPATH=/app/sentinel_ui/api LANGSMITH_TRACING=false
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/state', timeout=4)"
CMD ["uvicorn", "sentinel_api.app:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"]
