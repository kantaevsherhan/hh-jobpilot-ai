.DEFAULT_GOAL := help
.PHONY: help setup dev check backend frontend ollama test test-backend test-front lint fmt migrate revision seed backup clean

BACKEND  := backend
FRONTEND := frontend
VENV     := $(BACKEND)/.venv
PY       := $(VENV)/bin/python
PIP      := $(VENV)/bin/pip

help:          ## Показать список команд
	@echo "hh-jobpilot-ai"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'
	@echo ""
	@echo "Первый запуск:  make setup && make dev"

# ─────────────────────────────────────────────────────────────
# Запуск
# ─────────────────────────────────────────────────────────────

dev:           ## Запустить всё одной командой (Ctrl+C останавливает всё)
	@test -f .env || cp .env.example .env
	@test -d $(VENV) || { echo "Нет окружения. Сначала: make setup"; exit 1; }
	@test -d $(FRONTEND)/node_modules || { echo "Нет node_modules. Сначала: make setup"; exit 1; }
	@echo "Проверяю Ollama..."
	@curl -sf http://localhost:11434/api/tags >/dev/null 2>&1 \
		&& echo "  Ollama уже работает" \
		|| { echo "  Запускаю Ollama..."; (ollama serve >/tmp/jobpilot-ollama.log 2>&1 &); sleep 2; }
	@echo ""
	@echo "  backend   → http://localhost:8000/docs"
	@echo "  frontend  → http://localhost:5173"
	@echo "  Ctrl+C останавливает оба"
	@echo ""
	@trap 'kill 0' EXIT INT TERM; \
	( cd $(BACKEND) && .venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload 2>&1 | sed 's/^/[backend ] /' ) & \
	( cd $(FRONTEND) && npm run dev 2>&1 | sed 's/^/[frontend] /' ) & \
	wait

backend:       ## Только backend
	cd $(BACKEND) && .venv/bin/uvicorn app.main:app --reload

frontend:      ## Только frontend
	cd $(FRONTEND) && npm run dev

ollama:        ## Только Ollama
	ollama serve

# ─────────────────────────────────────────────────────────────
# Установка
# ─────────────────────────────────────────────────────────────

setup:         ## Первичная установка: окружение, зависимости, браузер, база
	@test -f .env || { cp .env.example .env; echo "Создан .env"; }
	@mkdir -p data/browser data/screenshots data/backups data/exports
	@echo "→ Python-окружение"
	@if [ ! -d $(VENV) ]; then \
		if command -v uv >/dev/null 2>&1; then \
			uv venv $(VENV); \
		elif python3 -m venv $(VENV) >/dev/null 2>&1; then \
			true; \
		else \
			echo ""; \
			echo "  Не могу создать виртуальное окружение."; \
			echo "  В системе нет ни uv, ни python3-venv. Поставь одно из двух:"; \
			echo ""; \
			echo "    sudo apt install python3.12-venv        # обычный путь"; \
			echo "    curl -LsSf https://astral.sh/uv/install.sh | sh   # быстрее"; \
			echo ""; \
			exit 1; \
		fi; \
	fi
	@$(PIP) install -q --upgrade pip 2>/dev/null || true
	@if [ -f $(BACKEND)/requirements.txt ]; then \
		if command -v uv >/dev/null 2>&1; then uv pip install -q --python $(PY) -r $(BACKEND)/requirements.txt; \
		else $(PIP) install -q -r $(BACKEND)/requirements.txt; fi; \
	else echo "  requirements.txt пока нет"; fi
	@echo "→ Chromium для Playwright"
	@$(VENV)/bin/playwright install chromium 2>/dev/null || echo "  Playwright пока не установлен"
	@echo "→ Зависимости фронтенда"
	@test -f $(FRONTEND)/package.json && (cd $(FRONTEND) && npm install --silent) || echo "  package.json пока нет"
	@echo "→ Миграции"
	@test -f $(BACKEND)/alembic.ini && (cd $(BACKEND) && .venv/bin/alembic upgrade head) || echo "  alembic пока не настроен"
	@echo "→ Модель Ollama"
	@ollama list 2>/dev/null | grep -q qwen3 || echo "  выполни: ollama pull qwen3:4b-instruct"
	@echo ""
	@echo "Готово. Запуск: make dev"

check:         ## Проверить, что всё нужное установлено
	@echo "Окружение:"
	@printf "  python3   "; python3 --version 2>/dev/null || echo "НЕ НАЙДЕН"
	@printf "  node      "; node --version 2>/dev/null || echo "НЕ НАЙДЕН"
	@printf "  npm       "; npm --version 2>/dev/null || echo "НЕ НАЙДЕН"
	@printf "  ollama    "; ollama --version 2>/dev/null | grep -o "version is.*" || echo "НЕ НАЙДЕН"
	@echo "Проект:"
	@printf "  .env              "; test -f .env && echo "есть" || echo "НЕТ (make setup)"
	@printf "  venv              "; test -d $(VENV) && echo "есть" || echo "НЕТ (make setup)"
	@printf "  node_modules      "; test -d $(FRONTEND)/node_modules && echo "есть" || echo "НЕТ (make setup)"
	@printf "  база данных       "; test -f data/jobpilot.db && echo "есть" || echo "нет (создастся миграцией)"
	@printf "  Ollama отвечает   "; curl -sf http://localhost:11434/api/tags >/dev/null 2>&1 && echo "да" || echo "нет (make ollama)"

# ─────────────────────────────────────────────────────────────
# Качество кода
# ─────────────────────────────────────────────────────────────

test: test-backend test-front  ## Все тесты

test-backend:  ## pytest
	cd $(BACKEND) && .venv/bin/pytest -q

test-front:    ## vitest, если настроен
	cd $(FRONTEND) && npm run test --if-present

lint:          ## ruff + mypy + eslint + vue-tsc
	cd $(BACKEND) && .venv/bin/ruff check . && .venv/bin/mypy app
	cd $(FRONTEND) && npx eslint . && npx vue-tsc --noEmit

fmt:           ## ruff format + prettier, с автоисправлениями
	cd $(BACKEND) && .venv/bin/ruff format . && .venv/bin/ruff check --fix .
	cd $(FRONTEND) && npx prettier --write . && npx eslint . --fix

# ─────────────────────────────────────────────────────────────
# База
# ─────────────────────────────────────────────────────────────

migrate:       ## Применить миграции
	cd $(BACKEND) && .venv/bin/alembic upgrade head

revision:      ## Новая миграция: make revision M="описание"
	cd $(BACKEND) && .venv/bin/alembic revision --autogenerate -m "$(M)"

seed:          ## Дефолтные промпты и демо-данные
	cd $(BACKEND) && .venv/bin/python -m app.cli seed

backup:        ## Резервная копия базы
	cd $(BACKEND) && .venv/bin/python -m app.cli backup

clean:         ## Убрать мусор сборки (данные не трогает)
	find . -type d -name __pycache__ -prune -exec rm -rf {} + 2>/dev/null || true
	rm -rf $(FRONTEND)/dist $(BACKEND)/.pytest_cache $(BACKEND)/.ruff_cache $(BACKEND)/.mypy_cache
