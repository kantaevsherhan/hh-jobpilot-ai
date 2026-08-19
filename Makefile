.PHONY: help up down logs dev test test-backend test-front lint fmt migrate seed backup clean

help:
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'

up:            ## Поднять backend + frontend в докере
	xhost +local:docker >/dev/null 2>&1 || true
	docker compose up -d
	@echo "backend  → http://localhost:8000/docs"
	@echo "frontend → http://localhost:5173"

down:          ## Остановить всё
	docker compose down

logs:          ## Логи всех сервисов
	docker compose logs -f

dev:           ## Запуск без докера (быстрее для разработки)
	@echo "1: cd backend && source .venv/bin/activate && uvicorn app.main:app --reload"
	@echo "2: cd frontend && npm run dev"
	@echo "3: ollama serve"

test: test-backend test-front  ## Все тесты

test-backend:  ## pytest
	cd backend && pytest -q

test-front:    ## vitest (если настроен)
	cd frontend && npm run test --if-present

lint:          ## Линтеры: ruff + mypy + eslint + vue-tsc
	cd backend && ruff check . && mypy app
	cd frontend && npx eslint . && npx vue-tsc --noEmit

fmt:           ## Форматтеры: ruff format + prettier
	cd backend && ruff format . && ruff check --fix .
	cd frontend && npx prettier --write . && npx eslint . --fix

migrate:       ## Применить миграции
	cd backend && alembic upgrade head

seed:          ## Демо-данные и дефолтные промпты
	cd backend && python -m app.cli seed

backup:        ## Резервная копия базы
	cd backend && python -m app.cli backup

clean:         ## Убрать мусор сборки (данные не трогает)
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
	rm -rf frontend/dist backend/.pytest_cache backend/.ruff_cache
