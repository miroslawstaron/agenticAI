FROM node:22-bookworm-slim AS frontend
WORKDIR /build
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm test && npm run build

FROM python:3.12-slim-bookworm AS wheel
WORKDIR /build
COPY pyproject.toml requirements-runtime.lock ./
COPY agenticai/ ./agenticai/
COPY agent.py agentC.py agentCompiler.py agentStaticAnalyzer.py ./
COPY --from=frontend /agenticai/static/ ./agenticai/static/
RUN pip wheel --no-cache-dir --constraint requirements-runtime.lock --wheel-dir /wheels .

FROM python:3.12-slim-bookworm
RUN apt-get update && apt-get install -y --no-install-recommends gcc libc6-dev cppcheck bash ca-certificates && rm -rf /var/lib/apt/lists/* \
    && groupadd --gid 1000 studio && useradd --uid 1000 --gid 1000 --create-home studio
COPY --from=frontend /usr/local/bin/node /usr/local/bin/node
COPY --from=frontend /usr/local/lib/node_modules/npm /usr/local/lib/node_modules/npm
RUN ln -s /usr/local/lib/node_modules/npm/bin/npm-cli.js /usr/local/bin/npm && ln -s /usr/local/lib/node_modules/npm/bin/npx-cli.js /usr/local/bin/npx
COPY --from=wheel /wheels/ /wheels/
RUN pip install --no-cache-dir --no-index --find-links=/wheels agenticai-studio && rm -rf /wheels
ENV AGENTICAI_DATA=/data AGENTICAI_CONTAINER=1 PYTHONUNBUFFERED=1
VOLUME ["/data"]
EXPOSE 8765
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8765/health',timeout=3)"
ENTRYPOINT ["python", "-m", "agenticai.container_entrypoint"]
