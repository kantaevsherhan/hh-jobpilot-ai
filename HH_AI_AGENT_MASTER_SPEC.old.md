# HH AI Agent — Master Specification / Prompt for AI Coding Agent

> Полное техническое задание для создания локальной системы поиска, анализа и управления откликами на вакансии hh.kz.
>
> Этот файл нужно положить в корень репозитория и передать AI coding agent как главный источник требований.
>
> Рабочее название: **HH AI Agent**
>
> Интерфейс первой версии: русский.
>
> Основной принцип: **Collect → Filter → Understand → Decide → Personalize → Verify → Apply → Track**.

---

## 1. Цель проекта

Создать локальное приложение с Web UI, которое помогает кандидату искать подходящие вакансии на hh.kz и управлять откликами.

Система должна:

- запускать видимый Chromium через Playwright (`headless=False`);
- хранить постоянную browser session, чтобы не логиниться при каждом запуске;
- позволять вручную войти в HH при первом запуске или после истечения сессии;
- искать вакансии по нескольким настраиваемым поисковым профилям;
- сохранять каждую найденную вакансию в SQLite;
- давать прямую ссылку на оригинал вакансии HH;
- применять hard filters до обращения к LLM;
- фильтровать зарплату, удалёнку, формат, опыт, ключевые слова и компании;
- анализировать прошедшие фильтры вакансии через Ollama;
- определять, действительно ли вакансия относится к профессии кандидата;
- определять, может ли кандидат реально выполнять работу;
- оценивать соответствие по шкале 0–100;
- выделять совпадающие, отсутствующие и критически отсутствующие навыки;
- сохранять red flags / green flags;
- генерировать **отдельное персонализированное сопроводительное письмо для каждой вакансии**;
- использовать примеры писем пользователя только как ориентир стиля;
- никогда не придумывать навыки, опыт, проекты, достижения или годы опыта;
- проверять AI-письмо отдельным Fact Checker;
- позволять написать письмо вручную;
- позволять редактировать, регенерировать и переписывать AI-письмо;
- поддерживать `MANUAL`, `SEMI_AUTO`, `AUTO`;
- сохранять всю историю решений, писем, откликов, запусков и ошибок;
- управляться через полноценную Vue SPA;
- показывать работу бота в real time;
- поддерживать несколько профилей кандидата / HH-резюме.

Это не должен быть простой скрипт "найти → кликнуть откликнуться". Это должен быть локальный **AI Job Search Control Center**.

---

# 2. Основной стек

## Backend

```text
Python 3.12+
FastAPI
Uvicorn
SQLAlchemy 2.x
Alembic
Pydantic 2
pydantic-settings
SQLite
aiosqlite
httpx
Playwright Python
asyncio
WebSocket
orjson
```

Для тестов:

```text
pytest
pytest-asyncio
```

## Frontend

Обязательный стек:

```text
Vue 3
Vite
TypeScript
PrimeVue 4
TailwindCSS
lucide-vue-next
Axios
@tanstack/vue-query
Vue Router
Pinia
Zod
dayjs
```

Не использовать Nuxt. Это локальная SPA/admin panel, SEO не нужно.

## AI

```text
Ollama
Qwen Instruct
```

Стартовая модель:

```text
qwen3:4b-instruct
```

Модель не должна быть hardcoded: настройки доступны из Web UI.

---

# 3. Архитектура

```text
                    ┌─────────────────────────────┐
                    │         Vue 3 Web UI        │
                    │ PrimeVue / Tailwind / Query │
                    └──────────────┬──────────────┘
                                   │ REST + WS
                    ┌──────────────▼──────────────┐
                    │           FastAPI           │
                    └──────────────┬──────────────┘
                                   │
        ┌──────────────────────────┼───────────────────────────┐
        │                          │                           │
┌───────▼────────┐        ┌────────▼────────┐         ┌────────▼───────┐
│  Bot Manager   │        │     SQLite      │         │     Ollama     │
│ Queue / Runs   │        │ SQLAlchemy      │         │ Qwen Instruct │
└───────┬────────┘        └─────────────────┘         └────────────────┘
        │
┌───────▼────────┐
│   Playwright   │
│ Visible Chrome │
│ Persistent     │
└───────┬────────┘
        │
      hh.kz
```

Основные независимые слои:

```text
Browser Automation
Vacancy Collector
Hard Filters
Company Rules
Candidate Knowledge Base
AI Pipeline
Decision Engine
Cover Letter Engine
Application Engine
Persistence
Realtime Events
Web UI
Analytics
```

Playwright не должен знать детали UI frontend.
Frontend не должен обращаться напрямую к SQLite или Ollama.
AI layer не должен напрямую управлять браузером.

---

# 4. Рекомендуемая структура репозитория

```text
hh-ai-agent/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── api/
│   │   │   ├── bot.py
│   │   │   ├── browser.py
│   │   │   ├── profiles.py
│   │   │   ├── resumes.py
│   │   │   ├── vacancies.py
│   │   │   ├── applications.py
│   │   │   ├── search_profiles.py
│   │   │   ├── company_rules.py
│   │   │   ├── cover_letters.py
│   │   │   ├── ai.py
│   │   │   ├── stats.py
│   │   │   ├── runs.py
│   │   │   └── settings.py
│   │   ├── agent/
│   │   │   ├── manager.py
│   │   │   ├── worker.py
│   │   │   ├── queue.py
│   │   │   ├── scheduler.py
│   │   │   ├── state.py
│   │   │   ├── events.py
│   │   │   └── recovery.py
│   │   ├── browser/
│   │   │   ├── manager.py
│   │   │   ├── auth.py
│   │   │   ├── selectors.py
│   │   │   ├── search.py
│   │   │   ├── vacancy.py
│   │   │   ├── parser.py
│   │   │   ├── application.py
│   │   │   ├── questions.py
│   │   │   └── screenshots.py
│   │   ├── ai/
│   │   │   ├── client.py
│   │   │   ├── prompt_service.py
│   │   │   ├── schemas.py
│   │   │   ├── requirements_extractor.py
│   │   │   ├── matcher.py
│   │   │   ├── decision_engine.py
│   │   │   ├── cover_letter.py
│   │   │   ├── fact_checker.py
│   │   │   ├── summarizer.py
│   │   │   └── vacancy_chat.py
│   │   ├── filters/
│   │   │   ├── engine.py
│   │   │   ├── salary.py
│   │   │   ├── work_format.py
│   │   │   ├── keywords.py
│   │   │   ├── company.py
│   │   │   ├── experience.py
│   │   │   └── duplicates.py
│   │   ├── database/
│   │   │   ├── base.py
│   │   │   ├── session.py
│   │   │   ├── models/
│   │   │   └── repositories/
│   │   ├── services/
│   │   ├── websocket/
│   │   └── core/
│   ├── alembic.ini
│   ├── pyproject.toml
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── api/
│   │   ├── components/
│   │   ├── layouts/
│   │   ├── pages/
│   │   ├── queries/
│   │   ├── stores/
│   │   ├── router/
│   │   ├── schemas/
│   │   ├── types/
│   │   └── utils/
│   ├── package.json
│   └── vite.config.ts
├── data/
│   ├── hh-agent.db
│   ├── browser/
│   ├── screenshots/
│   ├── backups/
│   └── exports/
├── .env.example
├── .gitignore
├── README.md
└── MASTER_SPEC.md
```

---

# 5. Хранение данных

Использовать **одну SQLite базу**:

```text
data/hh-agent.db
```

Не создавать отдельный `.db` на каждое резюме.

Все профильные данные связывать через:

```text
account_id
profile_id
```

Плюсы:

- единая статистика;
- дедупликация;
- один Alembic;
- простые backup;
- сравнение профилей;
- защита от повторного отклика одной вакансии через другое резюме.

---

# 6. HH Account и Browser Session

Один HH Account может иметь несколько резюме.

```text
HH Account
├── Persistent Browser Session
├── Fullstack Resume
├── Backend Resume
└── Go Resume
```

Использовать persistent browser context:

```python
context = await playwright.chromium.launch_persistent_context(
    user_data_dir="data/browser/account_1",
    headless=False,
)
```

Профиль браузера хранит cookies/local storage/session.

При первом запуске пользователь вручную логинится в открытом Chromium.

При последующих запусках используется сохранённая сессия.

Если HH требует повторный вход, CAPTCHA, SMS или другую проверку:

```text
NEEDS_USER_ACTION
```

Бот не пытается обходить защиту.

В UI:

```text
HH account: Login required
[Open Browser]
```

---

# 7. Candidate Profiles

Можно создать несколько профилей:

```text
Strong Middle Fullstack
Backend Node.js
Go Backend
```

В header интерфейса:

```text
Profile: [Backend Node.js ▼]
```

После переключения профиля UI показывает связанные с ним:

- vacancy matches;
- search profiles;
- filters;
- company rules;
- AI prompts;
- cover-letter examples;
- applications;
- runs;
- statistics.

## Duplicate Profile

Поддержать:

```text
Edit
Duplicate
Archive
Delete Permanently
```

Предпочтительно архивировать:

```text
is_archived = true
```

---

# 8. Candidate Knowledge Base

Каждый профиль имеет:

```text
General
Skills
Experience
Projects
Achievements
Education
Languages
Preferences
Allowed Facts
Letter Examples
```

## Skills

Поля:

```text
name
level
years_optional
category
is_core
notes
```

## Experience

```text
company
position
date_from
date_to
description
technologies
achievements
```

## Projects

```text
name
description
role
technologies
url_optional
achievements
```

## Allowed Facts

Очень важный раздел.

Это список утверждений, которые AI разрешено использовать в письмах.

Пример:

```text
Работаю с TypeScript и Node.js.
Есть опыт проектирования REST API.
Работал с PostgreSQL.
Есть опыт Docker.
Работал с event-driven системами.
```

AI не должен придумывать факты за пределами Candidate Profile и Allowed Facts.

---

# 9. HH Resume Manager

Candidate Profile связывается с конкретным HH Resume.

```text
hh_resumes

id
account_id
profile_id
hh_resume_id
title
url
is_active
last_synced_at
```

При отклике использовать резюме текущего профиля.

Если одна vacancy подходит двум профилям, её AI-анализ может храниться отдельно по каждому профилю, но реальный application должен иметь глобальную защиту от дубля.

---

# 10. Search Profiles

Внутри Candidate Profile можно создать несколько Search Profiles:

```text
Backend Remote
NestJS Remote
Fullstack Remote
Go Remote
High Salary
```

Поля:

```text
name
enabled
queries[]
remote_mode
allowed_work_formats
minimum_salary
currency
allow_unknown_salary
experience_filters
locations
max_age_days
include_keywords[]
exclude_keywords[]
max_results_per_run
priority
```

Пример:

```text
Name: Backend Remote

Queries:
- Backend Developer
- Node.js Developer
- NestJS Developer

Remote: Required
Minimum salary: 100000 KZT
Unknown salary: Allow
Max age: 7 days
```

Одна vacancy, найденная несколькими запросами, хранится один раз.

Дополнительная таблица:

```text
vacancy_search_matches
```

---

# 11. Vacancy

Сохранять максимум доступных данных:

```text
hh_id
url
alternate_url
title
company_hh_id
company_name
description
salary_from
salary_to
currency
salary_gross
work_format
remote
experience
employment
schedule
location
published_at
found_at
updated_at
status
skip_reason
skip_details
```

`url` обязателен.

В Web UI и таблице всегда иметь:

```text
Open HH ↗
```

---

# 12. Hard Filters

Простые проверки выполнять без AI.

## Salary

Настройки:

```text
minimum_salary
currency
allow_unknown_salary
```

Пример:

```text
minimum = 100000 KZT
```

Если зарплата ниже → `SKIPPED / SALARY_TOO_LOW`.

Если зарплата неизвестна:

```text
allow_unknown_salary = true → дальше
false → SKIPPED
```

## Work Format

```text
REMOTE_ONLY
REMOTE_OR_HYBRID
ANY
```

## Keywords

Exclude:

```text
1С
Bitrix
WordPress
Delphi
```

Positive:

```text
NestJS
TypeScript
PostgreSQL
Kafka
Go
```

## Experience

Настраиваемые диапазоны HH.

## Vacancy Age

Например:

```text
max_age_days = 7
```

---

# 13. Company Rules

Отдельный модуль.

Пример требования:

```text
если в названии компании есть "vash" → не рассматривать
```

Rule:

```text
type = CONTAINS
value = vash
action = SKIP
case_sensitive = false
```

Подойдут:

```text
Vash Group
VASH COMPANY
ООО Vash
```

Вакансия не удаляется.

Она сохраняется:

```text
status = SKIPPED
skip_reason = COMPANY_FILTER
skip_details = "Company name contains: vash"
```

Типы:

```text
CONTAINS
EQUALS
REGEX
```

Действия:

```text
SKIP
ALWAYS_REVIEW
PRIORITY_BOOST
SCORE_PENALTY
```

Примеры:

```text
contains "vash" -> SKIP
equals "ABC" -> ALWAYS_REVIEW
contains "Google" -> PRIORITY_BOOST +20
contains "Outsource" -> SCORE_PENALTY -10
```

В UI должна быть функция `Test Rule`.

---

# 14. AI Pipeline

Не делать один гигантский prompt.

Использовать:

```text
Raw Vacancy
↓
Requirements Extractor
↓
Candidate Matcher
↓
Decision Engine
↓
Cover Letter Generator
↓
Fact Checker
↓
Apply / Review
```

---

# 15. Requirements Extractor

Из вакансии получить JSON:

```json
{
  "required_skills": ["Node.js", "PostgreSQL"],
  "preferred_skills": ["Kafka"],
  "responsibilities": ["API development", "microservices"],
  "experience_requirements": ["3+ years"],
  "language_requirements": ["English B2"],
  "work_format": "remote",
  "critical_requirements": ["Node.js commercial experience"]
}
```

Валидировать Pydantic.

---

# 16. Candidate Matcher

Сравнивает requirements и Candidate Profile.

Возвращает:

```json
{
  "profession_match": true,
  "can_do_job": true,
  "overall_score": 91,
  "profession_score": 100,
  "stack_score": 94,
  "experience_score": 85,
  "responsibilities_score": 90,
  "work_format_score": 100,
  "salary_score": 100,
  "matched_skills": ["TypeScript", "NestJS", "PostgreSQL"],
  "missing_skills": ["AWS"],
  "critical_missing": [],
  "red_flags": [],
  "green_flags": ["Remote", "Core stack match"],
  "reason": "..."
}
```

Важно: `can_do_job` означает не "совпало много слов", а реальную способность выполнять основные обязанности.

---

# 17. Decision Engine

Учитывает:

```text
hard filters
company rules
profession_match
can_do_job
overall_score
critical_missing
mode
minimum_ai_score
auto_apply_score
```

Возможные решения:

```text
SKIP
REVIEW
APPLY
```

---

# 18. Режимы

## MANUAL

```text
Search
↓
Save
↓
Filters
↓
AI Analysis (optional/automatic)
↓
WAIT USER
```

Бот **никогда сам не отправляет отклик**.

Пользователь может:

```text
Open Details
Open HH
Write manually
Generate with AI
Edit
Save
Apply
Skip
```

## SEMI_AUTO

Пример:

```text
minimum_ai_score = 75
auto_apply_score = 90
```

Логика:

```text
0–74   → SKIP
75–89  → REVIEW_REQUIRED
90–100 → AUTO APPLY
```

Но auto apply только при выполнении всех обязательных условий.

## AUTO

```text
Search
↓
Hard Filters
↓
Company Rules
↓
Requirements Extract
↓
Candidate Match
↓
Decision
↓
Generate Unique Letter
↓
Fact Check
↓
Check Duplicate Application
↓
Apply
↓
Save Result
```

AUTO Apply разрешён только если:

```text
profession_match = true
can_do_job = true
overall_score >= configured threshold
critical_missing = []
hard filters passed
company rules passed
fact_checker.valid = true
session active
not already applied
application form recognized
```

---

# 19. Сопроводительные письма

На **каждую vacancy отдельное письмо**.

Нельзя использовать один шаблон для всех.

AI получает:

```text
Candidate Profile
Allowed Facts
Vacancy
Requirements
AI Analysis
2–3 relevant Human Letter Examples
```

Письмо сохраняется до отправки.

Пользователь может:

```text
Write manually
Generate with AI
Regenerate
Make shorter
More technical
More natural
Custom AI instruction
Edit manually
```

---

# 20. Human Letter Examples

CRUD в UI.

Поля:

```text
title
category
tone
content
is_active
is_preferred
```

Категории:

```text
Backend
Fullstack
Go
Startup
Enterprise
General
```

Примеры нужны для тона и структуры, но не должны копироваться дословно.

---

# 21. Cover Letter Versions

Хранить все версии:

```text
v1 AI Generated
v2 AI Regenerated
v3 User Edited
v4 AI Shortened
v5 Final Sent
```

Источники:

```text
AI
MANUAL
AI_EDITED_BY_USER
AI_REWRITE
```

Сохранять, какая версия реально была отправлена.

---

# 22. Fact Checker

После AI generation второй AI-проход.

Пример:

```json
{
  "valid": false,
  "unsupported_claims": [
    "У меня большой опыт AWS"
  ],
  "suggested_fixes": [
    "Удалить утверждение об AWS"
  ]
}
```

В `AUTO` нельзя отправлять письмо с `valid=false`.

---

# 23. AI Studio

Отдельный пункт sidebar.

Вкладки:

```text
General
Vacancy Analysis
Cover Letter
Fact Checker
Vacancy Actions
```

Настройки:

```text
Ollama URL
Model
Temperature
Context Size
Timeout
Fallback Model
```

Кнопка:

```text
Test Connection
```

Prompts редактируются через UI.

---

# 24. Prompt Variables

Поддержать:

```text
{{candidate_profile}}
{{candidate_skills}}
{{candidate_experience}}
{{candidate_projects}}
{{candidate_achievements}}
{{allowed_facts}}

{{vacancy}}
{{vacancy_title}}
{{vacancy_description}}
{{vacancy_salary}}
{{vacancy_company}}

{{requirements}}
{{vacancy_analysis}}
{{cover_letter_examples}}
{{cover_letter}}
{{search_profile}}
```

В prompt editor показывать список переменных и позволять вставить их кликом.

---

# 25. Prompt Versioning

Хранить версии:

```text
Vacancy Analyzer v1
Vacancy Analyzer v2
Vacancy Analyzer v3 ACTIVE
```

Каждый `ai_run` хранит:

```text
model
prompt_version
input
raw_output
parsed_output
duration
success
error
```

---

# 26. Suggested System Prompt

```text
Ты AI-ассистент кандидата для анализа вакансий и создания сопроводительных писем.

Используй только факты, которые явно присутствуют в профиле кандидата, опыте, проектах, достижениях и Allowed Facts.

Никогда не придумывай:
- технологии;
- опыт;
- компании;
- проекты;
- годы работы;
- достижения;
- образование;
- языки;
- сертификаты.

Если данных недостаточно, укажи это.

При анализе оценивай реальную способность кандидата выполнять работу, а не простое количество совпавших ключевых слов.

Различай обязательные и желательные требования.

Критическое обязательное требование должно иметь значительно больший вес, чем необязательный навык.

Не создавай ложных утверждений ради повышения шансов отклика.
```

---

# 27. Suggested Vacancy Analysis Prompt

```text
Проанализируй вакансию относительно профиля кандидата.

Определи:
1. Относится ли работа к целевой профессии.
2. Может ли кандидат реально выполнять основные обязанности.
3. Какие обязательные требования совпадают.
4. Какие обязательные требования отсутствуют.
5. Какие желательные навыки отсутствуют.
6. Насколько совпадает core stack.
7. Подходит ли уровень.
8. Подходит ли формат работы.
9. Есть ли red flags.
10. Есть ли green flags.

Не придумывай факты о кандидате.
Верни строго JSON по заданной schema.

Candidate:
{{candidate_profile}}

Allowed Facts:
{{allowed_facts}}

Requirements:
{{requirements}}

Vacancy:
{{vacancy}}
```

---

# 28. Suggested Cover Letter Prompt

```text
Напиши отдельное персонализированное сопроводительное письмо именно для текущей вакансии.

Используй только реальные факты кандидата.

Не придумывай опыт, технологии, годы работы, компании, проекты или достижения.

Не перечисляй весь стек. Выбери только факты, реально связанные с этой вакансией.

Не копируй описание вакансии.

Human Examples используй только как ориентир по стилю, длине и тону.

Candidate:
{{candidate_profile}}

Allowed Facts:
{{allowed_facts}}

Vacancy:
{{vacancy}}

Analysis:
{{vacancy_analysis}}

Human Examples:
{{cover_letter_examples}}
```

---

# 29. Suggested Fact Checker Prompt

```text
Проверь сопроводительное письмо на фактическую достоверность.

Каждое утверждение о кандидате сравни с Candidate Profile и Allowed Facts.

Если обнаружен навык, опыт, проект, достижение или год опыта, которого нет в данных, добавь его в unsupported_claims.

Не оценивай стиль.
Проверяй только факты.

Candidate:
{{candidate_profile}}

Allowed Facts:
{{allowed_facts}}

Letter:
{{cover_letter}}
```

---

# 30. AI Playground

Страница:

```text
/ai/playground
```

Выбор:

```text
Model
Prompt
Candidate Profile
Vacancy
```

Кнопка:

```text
Run Test
```

Показывать:

```text
Raw Output
Parsed JSON
Validation Errors
Duration
Model
Prompt Version
```

---

# 31. Vacancy AI Actions

На Details:

```text
Analyze Vacancy
Generate Cover Letter
Regenerate Letter
Summarize
Explain Why It Matches
Find Red Flags
Find Missing Skills
Prepare Interview Questions
Suggest What To Emphasize
```

---

# 32. AI Chat по вакансии

Контекст:

```text
Candidate Profile
Vacancy
Requirements
Analysis
```

Пользователь может спросить:

```text
Почему score 72?
Стоит ли всё равно откликнуться?
Что лучше подчеркнуть?
Сделай письмо менее формальным.
```

AI Chat сам не вызывает Apply.

---

# 33. Дополнительные вопросы работодателя

Если при отклике есть вопросы:

```text
How many years...?
Why do you want...?
English level?
```

Настройка:

```text
REVIEW
AI_ANSWER
SKIP
```

Default:

```text
REVIEW
```

Если ответа нет в профиле, AI не должен придумывать.

---

# 34. Vacancy Statuses

```text
DISCOVERED
FILTERING
FILTERED_OUT
AI_PENDING
AI_ANALYZED
AI_REJECTED
REVIEW_REQUIRED
READY
SKIPPED
APPLYING
APPLIED
VIEWED
INVITED
REJECTED
FAILED
NEEDS_USER_ACTION
```

Skip reasons:

```text
SALARY_TOO_LOW
SALARY_UNKNOWN
NOT_REMOTE
WORK_FORMAT
EXPERIENCE
COMPANY_FILTER
KEYWORD_FILTER
PROFESSION_MISMATCH
CRITICAL_SKILL_MISSING
AI_REJECTED
USER_SKIPPED
DUPLICATE
ALREADY_APPLIED
VACANCY_CLOSED
OTHER
```

---

# 35. Idempotency

Один реальный отклик не должен отправляться дважды.

Перед Apply:

1. проверить SQLite;
2. проверить existing application;
3. по возможности проверить UI HH;
4. только потом submit.

Retry сетевой ошибки не должен вслепую повторять настоящий Submit.

---

# 36. Bot Runs

Каждый `Start` создаёт Run.

Поля:

```text
id
profile_id
mode
status
started_at
ended_at
found_count
new_count
filtered_count
analyzed_count
suitable_count
review_count
applied_count
skipped_count
error_count
stop_reason
```

---

# 37. Bot Events

Сохранять:

```text
BOT_STARTED
SEARCH_STARTED
VACANCY_FOUND
FILTER_PASSED
FILTER_REJECTED
AI_STARTED
AI_COMPLETED
LETTER_STARTED
LETTER_COMPLETED
APPLY_STARTED
APPLICATION_SENT
APPLICATION_FAILED
BOT_PAUSED
BOT_RESUMED
BOT_STOPPED
```

Поля:

```text
run_id
profile_id
vacancy_id
event_type
message
payload_json
created_at
```

---

# 38. Управление ботом

Кнопки:

```text
Start
Pause
Resume
Stop
```

Pause:

```text
finish current safe operation
do not dequeue next job
status = PAUSED
```

Stop:

```text
stop new work
flush events
save run state
close/idle browser safely
finish run
```

---

# 39. Queue

Для MVP использовать:

```text
asyncio.Queue
```

Jobs:

```text
SEARCH
FETCH_VACANCY
FILTER
ANALYZE
GENERATE_LETTER
FACT_CHECK
APPLY
SYNC_STATUS
```

Redis не нужен в первой версии.

---

# 40. Scheduler

Поддержать:

```text
Manual Run
Run Selected Search Profile
Run All Enabled Profiles
Scheduled Runs
```

Scheduler должен отключаться.

---

# 41. Rate Limits

Использовать delays как rate limiting, а не как stealth bypass.

Настройки:

```text
delay_between_vacancies
delay_before_apply
delay_after_apply
max_applications_per_hour
max_applications_per_day
```

Редактируются через UI.

---

# 42. Runtime Modes

Обязательны:

```text
DEVELOPMENT
DRY_RUN
LIVE
```

## DEVELOPMENT

Тестовые данные, никакого реального submit.

## DRY_RUN

Реальный HH и реальные AI-процессы, но финальный submit запрещён.

## LIVE

Разрешены реальные отклики.

В UI режим должен быть хорошо заметен.

---

# 43. Web UI Navigation

```text
Dashboard

BOT
├── Vacancies
├── Review Queue
├── Applications
├── Browser
└── Activity

SEARCH
├── Search Profiles
└── Companies

CANDIDATE
├── Profiles
├── Resume
├── Experience
├── Projects
└── Letter Examples

AI
├── AI Studio
├── Playground
└── AI History

ANALYTICS
├── Overview
├── Technologies
├── Salaries
└── Runs

SYSTEM
├── Settings
├── Logs
└── Backups
```

---

# 44. Header

```text
Profile: [Backend Node.js ▼]

BOT     ● Running
HH      ● Connected
OLLAMA  ● Online

[Pause] [Stop]
```

---

# 45. Dashboard

Карточки:

```text
Found
AI Suitable
Applied
Skipped
Errors
```

Current Run:

```text
Run #142
Backend Node.js
● Running
Duration 00:18:24

Found        42
New          19
Analyzed     12
Suitable      8
Applied       5
Skipped      14
```

---

# 46. Live Activity

Через WebSocket:

```text
01:34:12 SEARCH   Found 20 vacancies
01:34:13 VACANCY  Backend Developer
01:34:14 FILTER   Passed
01:34:14 AI       Analysis started
01:34:18 AI       Score 91
01:34:19 LETTER   Generating
01:34:23 BROWSER  Opening form
01:34:31 APPLY    Submitted
```

Фильтры:

```text
All
Search
AI
Browser
Apply
Errors
```

---

# 47. Vacancies Table

PrimeVue DataTable, server-side pagination.

Колонки:

```text
Status
Vacancy
Company
Salary
Format
AI Score
Decision
Found At
Applied At
Actions
```

Название vacancy и отдельная кнопка должны открывать оригинал HH в новой вкладке.

Filters:

```text
Search
Status
Decision
Score
Salary From
Work Format
Date
Company
Profile
```

Bulk actions:

```text
Analyze
Generate Letters
Apply
Skip
Blacklist Company
```

---

# 48. Vacancy Details

Route:

```text
/vacancies/:id
```

Header:

```text
Backend Developer
ABC Company
600000–900000 KZT
Remote
3–6 years

[Open on HH.kz ↗]
```

Tabs:

```text
Overview
Description
Requirements
AI Analysis
Cover Letter
Application
History
```

---

# 49. Cover Letter UI

Если письма нет:

```text
[Write Manually]
[Generate with AI]
```

Если есть:

```text
[Edit]
[Regenerate]
[Shorter]
[More Technical]
[More Natural]
[Custom AI Instruction]
[Save]
[Apply]
```

Manual mode должен позволять полностью написать письмо самостоятельно, а Playwright только вставит готовый текст.

---

# 50. Review Queue

Карточка:

```text
Backend Developer
Score 86
700–900k
Remote

Matched:
TypeScript
NestJS
PostgreSQL

Reason:
...

Letter:
...

[Open HH]
[Edit Letter]
[Skip]
[Apply]
[Apply & Next]
[Skip & Next]
```

---

# 51. Browser Page

```text
Browser: Chromium
Status: Running
HH Account: Logged In
Session: Active

[Open Browser]
[Login]
[Restart Browser]
[Close Browser]
```

---

# 52. Company Page

Показывать:

```text
Company Name
Vacancies Found
Applications
Views
Invites
Rejections
Notes
Rules
```

---

# 53. Analytics

Funnel:

```text
Found
↓
Passed Filters
↓
AI Suitable
↓
Applied
↓
Viewed
↓
Invited
↓
Interview
↓
Offer
```

`Interview` и `Offer` можно отмечать вручную.

Technologies:

```text
PostgreSQL 84
Docker     77
TypeScript 69
NestJS     48
Kafka      32
Go         27
```

Salary:

```text
min
max
average
median
```

Conversion:

```text
View Rate
Invite Rate
Interview Rate
```

По профилям:

```text
Backend Node.js
Fullstack
Go Backend
```

---

# 54. Notification Center

Примеры:

```text
HH session expired
7 vacancies waiting review
Ollama offline
Application failed
```

Также использовать PrimeVue Toast.

---

# 55. Error Screenshots

При browser error сохранять:

```text
data/screenshots/
```

- screenshot;
- error;
- vacancy;
- run;
- timestamp;
- optional HTML snapshot.

UI:

```text
[View Screenshot]
[Open HH]
[Retry Safe Operation]
```

---

# 56. Database Tables

Основной набор:

```text
accounts
candidate_profiles
candidate_skills
candidate_experiences
candidate_projects
candidate_achievements
candidate_allowed_facts

hh_resumes

search_profiles
search_queries
company_rules

vacancies
vacancy_search_matches
vacancy_profile_matches

ai_prompts
ai_prompt_versions
ai_runs

cover_letter_examples
cover_letters
cover_letter_versions

applications

bot_runs
bot_events

settings
```

Ключевые связи:

```text
Account 1 → N Candidate Profiles
Candidate Profile 1 → N Search Profiles
Candidate Profile 1 → N Skills
Candidate Profile 1 → N Letter Examples

Vacancy N ↔ N Candidate Profiles via vacancy_profile_matches
Vacancy 1 → N AI Runs
Vacancy 1 → N Cover Letter Versions
Vacancy 1 → 0/1 real application per account according to idempotency rules
```

---

# 57. API

Base:

```text
/api/v1
```

Bot:

```http
GET  /bot/status
POST /bot/start
POST /bot/pause
POST /bot/resume
POST /bot/stop
```

Browser:

```http
GET  /browser/status
POST /browser/start
POST /browser/login
POST /browser/restart
POST /browser/close
```

Profiles:

```http
GET    /profiles
POST   /profiles
GET    /profiles/{id}
PATCH  /profiles/{id}
POST   /profiles/{id}/duplicate
POST   /profiles/{id}/archive
DELETE /profiles/{id}
```

Vacancies:

```http
GET  /vacancies
GET  /vacancies/{id}
POST /vacancies/{id}/analyze
POST /vacancies/{id}/generate-letter
POST /vacancies/{id}/apply
POST /vacancies/{id}/skip
POST /vacancies/{id}/mark-later
```

Bulk:

```http
POST /vacancies/bulk/analyze
POST /vacancies/bulk/generate-letters
POST /vacancies/bulk/apply
POST /vacancies/bulk/skip
```

Search Profiles:

```http
GET    /search-profiles
POST   /search-profiles
GET    /search-profiles/{id}
PATCH  /search-profiles/{id}
DELETE /search-profiles/{id}
POST   /search-profiles/{id}/run
```

Company Rules:

```http
GET    /company-rules
POST   /company-rules
PATCH  /company-rules/{id}
DELETE /company-rules/{id}
POST   /company-rules/test
```

AI:

```http
GET  /ai/status
GET  /ai/models
POST /ai/test
GET  /ai/prompts
POST /ai/prompts
PATCH /ai/prompts/{id}
POST /ai/playground/run
POST /ai/vacancies/{id}/chat
```

Letters:

```http
GET  /vacancies/{id}/cover-letters
POST /vacancies/{id}/cover-letters/manual
POST /vacancies/{id}/cover-letters/generate
POST /cover-letters/{id}/rewrite
POST /cover-letters/{id}/select-version
```

Runs:

```http
GET /runs
GET /runs/{id}
GET /runs/{id}/events
```

Stats:

```http
GET /stats/overview
GET /stats/funnel
GET /stats/technologies
GET /stats/salaries
GET /stats/conversion
GET /stats/runs
```

---

# 58. WebSocket

```text
/ws/events
```

Events:

```text
bot.status
bot.run.started
bot.run.finished
browser.status
browser.user_action_required
vacancy.discovered
vacancy.filtered
vacancy.analysis.started
vacancy.analysis.completed
letter.generated
application.started
application.sent
application.failed
ollama.status
```

WebSocket используется для live updates.
TanStack Query остаётся источником server state и recovery.

---

# 59. Frontend Architecture

TanStack Query:

```text
profiles
vacancies
applications
searchProfiles
companyRules
stats
runs
aiPrompts
```

Pinia использовать только для:

```text
selectedProfile
theme
sidebar
client UI preferences
websocket connection state
```

Axios:

```ts
const api = axios.create({
  baseURL: '/api/v1',
  timeout: 30000,
})
```

Frontend не общается с Ollama напрямую.

---

# 60. PrimeVue Components

Использовать:

```text
DataTable
Column
Button
Tag
Badge
InputText
InputNumber
Select
MultiSelect
Slider
DatePicker
Dialog
Drawer
Tabs
Textarea
Toast
ConfirmDialog
Skeleton
Paginator
ProgressBar
Menu
Tooltip
```

Иконки — `lucide-vue-next`.

---

# 61. Browser Selectors

Все HH selectors централизовать:

```python
class HHSelectors:
    ...
```

Не размазывать селекторы по бизнес-логике.

Если HH меняет UI, селекторы должны чиниться в одном месте.

---

# 62. Safe Browser Behaviour

Если:

```text
CAPTCHA
unknown page
unknown application form
session expired
required confirmation
selector mismatch
```

AUTO mode не должен импровизировать.

Статус:

```text
NEEDS_USER_ACTION
```

или:

```text
REVIEW_REQUIRED
```

---

# 63. Error Handling

Каждая ошибка:

```text
error_code
human_message
technical_details
recoverable
```

Пример:

```text
BROWSER_SELECTOR_NOT_FOUND
OLLAMA_OFFLINE
INVALID_AI_RESPONSE
APPLICATION_STATE_UNKNOWN
```

---

# 64. AI Validation

Все JSON outputs от LLM валидировать через Pydantic.

Если response invalid:

1. один repair retry;
2. если снова invalid → AI failure;
3. AUTO Apply запрещён.

---

# 65. Crash Recovery

После падения приложения:

- данные не теряются;
- Run может быть отмечен interrupted;
- `APPLYING` перепроверяется;
- реальный Apply не повторяется без idempotency check;
- queue восстанавливается только безопасно.

---

# 66. Backup / Export

В UI:

```text
Backup Database
Export Vacancies CSV
Export Applications CSV
```

Backup в:

```text
data/backups/
```

---

# 67. Security

`.gitignore`:

```gitignore
.env
data/browser/
data/*.db
data/screenshots/
data/backups/
data/exports/
.venv/
__pycache__/
node_modules/
dist/
```

Browser profile фактически содержит авторизованную HH session и не должен попадать в Git.

---

# 68. .env.example

```env
APP_ENV=development

DATABASE_URL=sqlite+aiosqlite:///./data/hh-agent.db

OLLAMA_URL=http://localhost:11434
OLLAMA_DEFAULT_MODEL=qwen3:4b-instruct

BACKEND_HOST=127.0.0.1
BACKEND_PORT=8000
FRONTEND_URL=http://localhost:5173

BROWSER_HEADLESS=false
```

`BROWSER_HEADLESS=false` для реального проекта не должен меняться через AUTO mode.

---

# 69. Local Development

Backend:

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

Ollama:

```bash
ollama serve
ollama pull qwen3:4b-instruct
```

---

# 70. Первый MVP

Не реализовывать всё сразу.

## Phase 1

```text
Repository scaffold
FastAPI
SQLite
SQLAlchemy
Alembic
Vue 3
PrimeVue 4
Tailwind
Router
TanStack Query
Candidate Profiles CRUD
```

## Phase 2

```text
Playwright persistent Chromium
Visible browser
Login/session detection
Browser page
```

## Phase 3

```text
Search Profiles
Search HH
Vacancy parser
SQLite save
Deduplication
Vacancies DataTable
HH links
```

## Phase 4

```text
Salary filter
Remote filter
Keyword filter
Company rules
Skip reasons
```

## Phase 5

```text
Ollama client
AI Studio
Requirements Extractor
Candidate Matcher
Pydantic validation
AI score
```

## Phase 6

```text
Human letter examples
Unique cover letter generation
Versions
Fact checker
Manual editor
```

## Phase 7

```text
Manual Apply
Application idempotency
Application history
```

## Phase 8

```text
Bot Manager
Bot Runs
WebSocket
Live Activity
Pause/Resume/Stop
```

## Phase 9

```text
SEMI_AUTO
AUTO
DRY_RUN
LIVE safety
```

## Phase 10

```text
Analytics
Company intelligence
Backup/export
```

---

# 71. MVP Acceptance Criteria

MVP готов, когда:

1. Backend и frontend запускаются локально.
2. Alembic создаёт SQLite schema.
3. Можно создать Candidate Profile.
4. Можно создать Search Profile.
5. Можно открыть видимый Chromium.
6. Пользователь может вручную войти в HH.
7. Сессия переживает restart.
8. Можно запустить поиск.
9. Найденные вакансии сохраняются.
10. В DataTable видны title/company/salary/status/HH link.
11. Company contains rule `vash` корректно отправляет vacancy в SKIPPED.
12. Salary filter работает.
13. Remote filter работает.
14. Duplicate vacancy не создаётся.
15. Ollama status отображается.
16. Vacancy можно проанализировать.
17. AI JSON валидируется.
18. Score и reason видны в UI.
19. Можно написать письмо вручную.
20. Можно сгенерировать отдельное письмо AI.
21. Версии письма сохраняются.
22. Fact checker работает.
23. Можно вручную нажать Apply из UI.
24. Playwright выполняет применение выбранного письма.
25. Application сохраняется в SQLite.
26. Duplicate apply блокируется.
27. Bot Run сохраняется.
28. Live Activity обновляется.
29. Pause / Resume / Stop работают.
30. Есть DRY_RUN, в котором final Submit невозможен.

---

# 72. Seed Example

Candidate Profile:

```text
Strong Middle Fullstack

Target:
Fullstack Developer
Backend Developer

Core:
TypeScript
Node.js
NestJS
Vue 3
Nuxt
React
PostgreSQL

Additional:
Go
Python
FastAPI
Java
Spring Boot
Redis
Kafka
RabbitMQ
Docker

Preference:
Remote
Middle+ / Strong Middle
```

Search:

```text
Fullstack Developer
Backend Developer
Node.js Developer
NestJS Developer
TypeScript Developer
Go Developer

Remote:
Required

Minimum salary:
100000 KZT

Unknown salary:
Allow

Max age:
7 days
```

Company Rule:

```text
CONTAINS "vash" → SKIP
```

AI:

```text
Ollama URL: http://localhost:11434
Model: qwen3:4b-instruct
Temperature: 0.3
Timeout: 120
Minimum suitable score: 75
Auto apply score: 90
```

Seed должен быть optional/demo, не hardcoded production data.

---

# 73. Coding Rules for AI Agent

AI coding agent должен:

1. Прочитать этот документ полностью.
2. Сначала создать implementation plan.
3. Работать фазами.
4. После каждой фазы оставлять проект запускаемым.
5. Не создавать giant god classes.
6. Использовать type hints.
7. Использовать Pydantic schemas.
8. Использовать Alembic migrations.
9. Не хардкодить Candidate Profile.
10. Не хардкодить одну Ollama model.
11. Не хардкодить company rules.
12. Не создавать отдельную SQLite на каждый профиль.
13. Не выполнять real Apply в DEVELOPMENT/DRY_RUN.
14. Изолировать browser automation.
15. Изолировать AI logic.
16. Изолировать persistence.
17. Frontend должен работать только через API.
18. Frontend не обращается к Ollama напрямую.
19. Все critical state transitions писать в DB.
20. Любой реальный Apply должен быть idempotent.
21. Не обходить CAPTCHA/anti-bot.
22. Не отправлять AUTO Apply в неизвестной browser state.
23. Не придумывать candidate facts.
24. Создать README.
25. Создать `.env.example`.
26. Создать `.gitignore`.
27. Добавить default prompts как seed.
28. Добавить тесты для critical logic.

---

# 74. Минимальные тесты

Backend:

```text
salary filter
remote filter
company CONTAINS rule
deduplication
AI Pydantic validation
decision engine
cover letter fact-check parser
application idempotency
profile isolation
```

---

# 75. Главная философия

Нельзя строить проект вокруг идеи:

```text
найти → сразу кликнуть откликнуться
```

Нужно строить:

```text
Collect
↓
Persist
↓
Hard Validate
↓
Understand Requirements
↓
Match Candidate
↓
Decide
↓
Create Personalized Letter
↓
Fact Check
↓
Apply Safely
↓
Track Result
↓
Analyze Statistics
```

---

# 76. Конечный результат

После реализации пользователь должен открыть Web UI и иметь возможность:

1. Создать несколько Candidate Profiles.
2. Связать профиль с HH Resume.
3. Настроить skills, experience, projects, achievements и Allowed Facts.
4. Добавить свои примеры сопроводительных.
5. Создать несколько Search Profiles.
6. Настроить удалёнку и зарплату.
7. Настроить blacklist/priority rules по компаниям.
8. Настроить модель Ollama.
9. Изменить System Prompt.
10. Изменить Vacancy Analysis Prompt.
11. Изменить Cover Letter Prompt.
12. Изменить Fact Checker Prompt.
13. Запустить поиск.
14. Видеть открытый Chromium.
15. Видеть найденные вакансии в Web UI в реальном времени.
16. Открыть оригинальную вакансию HH по ссылке.
17. Посмотреть детали вакансии.
18. Посмотреть извлечённые требования.
19. Посмотреть AI score и причину.
20. Самому написать письмо.
21. Сгенерировать письмо нейронкой.
22. Переписать письмо через AI.
23. Выбрать нужную версию.
24. В Manual Mode самому решить, отправлять ли отклик.
25. В Semi Auto использовать Review Queue.
26. В Auto Mode разрешить системе самой решать и отправлять только безопасные подходящие отклики.
27. Остановить/поставить на паузу/продолжить бота.
28. Видеть live events.
29. Видеть историю запусков.
30. Видеть всю историю откликов.
31. Видеть причины Skip.
32. Видеть статистику вакансий, стеков, зарплат и конверсии.
33. Не потерять данные после restart.
34. Не получить повторный отклик из-за duplicate job или crash.

Главный результат проекта — **управляемый, наблюдаемый и настраиваемый AI-агент поиска работы**, а не бесконтрольный массовый бот.
