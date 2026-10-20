# Бэкенд + видимый Chromium на виртуальном экране + noVNC для входа в hh.kz.
# Окно браузера нельзя прятать (headless запрещён), поэтому оно рисуется на Xvfb,
# а пользователь смотрит на него во вкладке http://localhost:6080.
FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright \
    DISPLAY=:99

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        xvfb x11vnc novnc websockify fonts-dejavu-core ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Node нужен только для провайдеров Claude CLI и Codex CLI
COPY --from=node:22-bookworm-slim /usr/local/bin/node /usr/local/bin/node
COPY --from=node:22-bookworm-slim /usr/local/lib/node_modules /usr/local/lib/node_modules
RUN ln -s /usr/local/lib/node_modules/npm/bin/npm-cli.js /usr/local/bin/npm \
    && npm install -g @anthropic-ai/claude-code @openai/codex \
    && npm cache clean --force

WORKDIR /app/backend

COPY requirements.txt .
RUN pip install -r requirements.txt \
    && playwright install --with-deps chromium

COPY . .
RUN sed -i 's/\r$//' docker-entrypoint.sh && chmod +x docker-entrypoint.sh

EXPOSE 8000 6080
ENTRYPOINT ["./docker-entrypoint.sh"]
