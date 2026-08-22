# Правила работы над hh-jobpilot-ai

Этот файл про то, **как** работать над проектом, а не **что** делать. Что делает продукт — в [README.md](README.md).

---

## 1. Главное правило: не пиши то, что генерируется командой

Никогда не создавай структуру проекта вручную файл за файлом. Сначала ищи официальную команду создания, потом уже правь результат.

```bash
# Фронтенд
npm create vite@latest frontend -- --template vue-ts

# Бэкенд
uv init backend            # если есть uv
python -m venv .venv       # если нет

# Компоненты и библиотеки
npx nuxi@latest module add ...
npx shadcn-vue@latest init
alembic init alembic
```

Правило распространяется на всё: миграции создаются `alembic revision --autogenerate`, а не руками; зависимости добавляются `uv add` / `npm i`, а не вписыванием строки в `pyproject.toml`.

Если команды создания не существует — скажи об этом прямо, потом пиши руками.

---

## 2. Цикл работы над задачей

Одна задача — один законченный цикл. Не начинай следующую, пока не закрыл текущую:

```
1. Понял задачу, при неясности — спросил
2. Написал код
3. Написал тест (§4)
4. Прогнал тесты          → зелёные
5. Прогнал форматтер      → чисто
6. Прогнал линтер         → чисто
7. Коммит                 → одна задача = один коммит
```

Пункты 4–6 не пропускаются никогда, даже если правка на одну строку. Пункт 7 не пропускается, даже если задача маленькая.

---

## 3. Git

Репозиторий уже создан. Ветка — `main`, работаем прямо в ней (проект локальный, один разработчик).

**Коммит после каждой задачи.** Смысл — чтобы по `git log` было видно, что именно сделано и когда.

Формат сообщения:

```
<область>: <что сделано в одну строку>

<если нужно — 2-3 строки почему именно так>
```

Области: `backend`, `frontend`, `db`, `llm`, `browser`, `filters`, `pipeline`, `docs`, `test`, `chore`.

Примеры:

```
db: таблицы resumes и resume_skills + первая миграция
filters: фильтр зарплаты с конвертацией валют и gross/net
llm: провайдер ollama и интерфейс LLMProvider
browser: извлечение вакансии из встроенного JSON с фолбэком на DOM
```

Чего не делать:

- не коммитить `data/`, `.env`, `node_modules`, `.venv` — они в `.gitignore`, проверь перед `git add`;
- не делать коммит с падающими тестами;
- не сваливать три задачи в один коммит «доработки»;
- не писать `git add .` вслепую — посмотри `git status` сначала;
- не пушить никуда без прямой просьбы (удалённого репозитория пока нет).

---

## 4. Тесты — простые и быстрые

Тест нужен, чтобы **проверить, что система работает**, а не чтобы набрать покрытие. Никаких моков ради моков и никаких тестов на геттеры.

**Обязательные требования:**

- тест не требует запущенного Ollama;
- тест не требует запущенного браузера;
- тест не требует интернета;
- весь прогон укладывается в несколько секунд.

Провайдер LLM и Playwright мокаются. Для провайдера — фейковая реализация `LLMProvider`, возвращающая заранее заготовленный JSON. Для браузера — сохранённые HTML-страницы в `backend/tests/fixtures/`.

**Что покрывать в первую очередь:**

```
фильтры: зарплата с валютами и gross/net, формат, свежесть, стоп-слова
правило компании CONTAINS и регистронезависимость
дедупликация: повторный hh_id не создаёт вторую строку
валидация ответа модели + повторная попытка при мусоре
движок решений: каждая ветка отдельным тестом
скрытые инструкции: находятся и проверяются в письме
идемпотентность отклика: второй раз не проходит
очередь: остановка и возобновление не теряют и не дублируют задачи
```

Стиль теста — прямой, без абстракций:

```python
def test_salary_filter_rejects_below_minimum():
    vacancy = make_vacancy(salary_from=80_000, currency="KZT")
    profile = make_search_profile(min_salary=100_000, currency="KZT")

    result = check_salary(vacancy, profile)

    assert result.passed is False
    assert result.reason == SkipReason.SALARY_TOO_LOW
```

Фабрики `make_vacancy` / `make_search_profile` — в `backend/tests/factories.py`, с разумными дефолтами, чтобы тест указывал только то, что проверяет.

Запуск:

```bash
make test          # всё
make test-backend  # pytest
make test-front    # vitest, когда появится
```

Проект запускается без докера, локально. Первый раз — `make setup`, дальше `make dev` поднимает бэкенд, фронт и Ollama одной командой. `make check` показывает, чего не хватает.

---

## 5. Форматтеры и линтеры

Прогоняются после каждой задачи. Не «в конце», не «перед коммитом когда-нибудь».

```bash
make fmt     # ruff format + prettier --write
make lint    # ruff check + mypy + eslint + vue-tsc
```

### Python

**Ruff** — и форматтер, и линтер. `backend/pyproject.toml`:

```toml
[tool.ruff]
line-length = 100
target-version = "py312"

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B", "SIM", "ASYNC", "RUF"]
ignore = ["E501"]

[tool.ruff.format]
quote-style = "double"

[tool.mypy]
python_version = "3.12"
strict = true
ignore_missing_imports = true
```

Type hints обязательны везде. `Any` — только если реально невозможно иначе, с комментарием почему.

### TypeScript / Vue

**Prettier** — `frontend/.prettierrc` (твой конфиг, без изменений):

```json
{
  "tabWidth": 2,
  "useTabs": false,
  "semi": false,
  "singleQuote": true,
  "singleAttributePerLine": false,
  "trailingComma": "none",
  "quoteProps": "as-needed",
  "printWidth": 100
}
```

**ESLint** — `frontend/eslint.config.mjs`. Это твой набор правил, переложенный с Nuxt на Vite + Vue: `withNuxt` и `./.nuxt/eslint.config.mjs` заменены на `eslint-plugin-vue`, потому что Nuxt в проекте нет. Правила и комментарии сохранены один в один.

```js
import js from '@eslint/js'
import tseslint from 'typescript-eslint'
import pluginVue from 'eslint-plugin-vue'
import vueParser from 'vue-eslint-parser'
import prettier from 'eslint-config-prettier'

// Проект на Vue, поэтому react-hooks / react-refresh из исходного набора правил
// не подключаются — их аналог здесь даёт eslint-plugin-vue.
// Правила с проверкой типов включены только для .ts: в .vue они требуют
// полного разбора SFC-скриптов и заметно замедляют прогон.
export default [
  {
    ignores: ['dist', 'node_modules', 'coverage', 'src/types/api.generated.ts']
  },

  js.configs.recommended,
  ...pluginVue.configs['flat/recommended'],

  {
    files: ['**/*.vue'],
    languageOptions: {
      parser: vueParser,
      parserOptions: {
        parser: tseslint.parser,
        ecmaVersion: 'latest',
        sourceType: 'module'
      }
    },
    rules: {
      'vue/multi-word-component-names': 'off',
      'vue/block-order': ['error', { order: ['script', 'template', 'style'] }]
    }
  },

  {
    files: ['**/*.ts'],
    ignores: ['vite.config.ts'],
    extends: [
      tseslint.configs.strictTypeChecked,
      tseslint.configs.stylisticTypeChecked
    ],
    languageOptions: {
      parserOptions: {
        projectService: true,
        tsconfigRootDir: import.meta.dirname
      }
    },
    rules: {
      '@typescript-eslint/consistent-type-imports': [
        'error',
        { prefer: 'type-imports', fixStyle: 'inline-type-imports' }
      ],

      '@typescript-eslint/no-floating-promises': 'error',
      '@typescript-eslint/no-misused-promises': [
        'error',
        { checksVoidReturn: { attributes: false } }
      ],
      '@typescript-eslint/await-thenable': 'error',
      '@typescript-eslint/require-await': 'error',

      '@typescript-eslint/no-explicit-any': 'error',
      '@typescript-eslint/no-unsafe-argument': 'error',
      '@typescript-eslint/no-unsafe-assignment': 'error',
      '@typescript-eslint/no-unsafe-call': 'error',
      '@typescript-eslint/no-unsafe-member-access': 'error',
      '@typescript-eslint/no-unsafe-return': 'error',
      '@typescript-eslint/no-unnecessary-condition': 'warn',
      '@typescript-eslint/no-unnecessary-type-assertion': 'error',
      '@typescript-eslint/no-non-null-assertion': 'error',

      '@typescript-eslint/no-unused-vars': [
        'error',
        { argsIgnorePattern: '^_', varsIgnorePattern: '^_' }
      ],
      '@typescript-eslint/prefer-nullish-coalescing': 'error',
      '@typescript-eslint/prefer-optional-chain': 'error',
      '@typescript-eslint/no-unnecessary-boolean-literal-compare': 'error'
    }
  },

  prettier
]
```

Пакеты для этого конфига ставятся при создании фронта:

```bash
npm i -D eslint @eslint/js typescript-eslint eslint-plugin-vue vue-eslint-parser \
         eslint-config-prettier prettier vue-tsc
```

Правило `no-explicit-any` — `error`, а не `warn`. Если тип от бэкенда неизвестен — опиши его в `src/schemas/` через Zod, а не ставь `any`.

---

## 6. Границы слоёв — их нельзя нарушать

Повторяю здесь, потому что это ломается чаще всего:

```
browser/   не знает про LLM, про API и про схемы ответов модели
filters/   чистые функции, без обращений к БД внутри проверок
llm/       не управляет браузером и не ходит в БД напрямую
pipeline/  единственный слой, который знает обо всех остальных
api/       без бизнес-логики, только валидация и вызов сервиса
frontend/  ходит только в собственный API — не в Ollama, не в SQLite, не на hh.kz
```

Все селекторы HH — только `backend/app/browser/selectors.py`. Ни одного `page.locator("...")` со строкой где-либо ещё.

---

## 7. Чего не делать никогда

```
не обходить капчу и антибот-защиту HH
не подменять fingerprint, не крутить прокси
не автоматизировать веб-интерфейсы chatgpt.com и claude.ai
не выдумывать факты о кандидате ни в одном промпте
не заполнять поля с личными данными (паспорт, ИИН, адрес, банковские)
не отправлять отклик в неизвестном состоянии браузера
не отправлять два отклика на одну вакансию
не хардкодить: резюме, модель, провайдера, промпты, правила, пороги
не запускать параллельные LLM-вызовы (4 ГБ VRAM)
```

---

## 8. Язык

Интерфейс, сообщения об ошибках для пользователя, комментарии — **на русском**.
Коды в БД, имена переменных, названия таблиц и полей — **на английском**.

Комментарии пишутся там, где неочевидно **почему**, а не там, где видно **что**.

---

## 9. Порядок фаз

После каждой фазы проект должен запускаться и делать что-то полезное. Не начинать фазу N+1, пока в фазе N есть красные тесты или незакоммиченные изменения.

Перед началом фазы — короткий план: что за задачи входят, в каком порядке, что будет коммитом. План показать, дождаться подтверждения.
