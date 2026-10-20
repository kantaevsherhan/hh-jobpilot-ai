"""Проверка фактов в письме (§18).

Порядок: словарная проверка → LLM-проверка. Первая находит выдуманную
технологию мгновенно и бесплатно, до всякой модели.
"""

import json
import re
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import PromptKey
from app.llm import prompts, router
from app.llm.base import LLMResult
from app.llm.schemas import FactCheckResponse

# Технологии, о которых кандидат может соврать. Список общий, не про конкретное
# резюме: сверка идёт с тем, что реально указано у кандидата
KNOWN_TECHNOLOGIES = [
    # облака и инфраструктура
    "AWS",
    "Azure",
    "GCP",
    "Kubernetes",
    "Docker",
    "Terraform",
    "Ansible",
    "Nginx",
    "Traefik",
    "Helm",
    "OpenShift",
    # очереди, кэши, поиск
    "Kafka",
    "RabbitMQ",
    "NATS",
    "Redis",
    "Memcached",
    "Elasticsearch",
    "OpenSearch",
    # базы
    "PostgreSQL",
    "MySQL",
    "MariaDB",
    "Oracle",
    "MSSQL",
    "SQLite",
    "MongoDB",
    "ClickHouse",
    "Cassandra",
    "DynamoDB",
    "Neo4j",
    # ORM и работа с данными — про них модель врёт чаще всего, потому что они
    # «подразумеваются» стеком, но в резюме их нет
    "Prisma",
    "TypeORM",
    "Sequelize",
    "Drizzle",
    "Knex",
    "Mongoose",
    "Hibernate",
    "SQLAlchemy",
    "Alembic",
    "Doctrine",
    "Eloquent",
    "GORM",
    # аутентификация
    "OAuth",
    "OAuth2",
    "JWT",
    "Keycloak",
    "SAML",
    "LDAP",
    "Auth0",
    # python
    "Python",
    "Django",
    "FastAPI",
    "Flask",
    "Celery",
    "Pydantic",
    # node и фронт
    "Node.js",
    "NestJS",
    "Express",
    "Fastify",
    "Koa",
    "Deno",
    "Bun",
    "TypeScript",
    "JavaScript",
    "Vue",
    "React",
    "Angular",
    "Svelte",
    "Nuxt",
    "Next.js",
    "Vite",
    "Webpack",
    "Pinia",
    "Redux",
    "Tailwind",
    # прочие языки и фреймворки
    "Go",
    "Fiber",
    "Gin",
    "Rust",
    "Java",
    "Spring",
    "Kotlin",
    "Swift",
    "C#",
    ".NET",
    "Ruby",
    "Rails",
    "Elixir",
    "Scala",
    "PHP",
    "Laravel",
    "Symfony",
    "Yii2",
    "Bitrix",
    "1С",
    # протоколы и API
    "GraphQL",
    "gRPC",
    "REST",
    "WebSocket",
    "Kong",
    "Swagger",
    "OpenAPI",
    # CI/CD и наблюдаемость
    "GitLab CI",
    "GitHub Actions",
    "Jenkins",
    "ArgoCD",
    "TeamCity",
    "CircleCI",
    "Prometheus",
    "Grafana",
    "Sentry",
    "Kibana",
    "Jaeger",
    # тесты
    "Jest",
    "Vitest",
    "Pytest",
    "Playwright",
    "Cypress",
    "Selenium",
    # данные
    "Spark",
    "Airflow",
    "Hadoop",
    "dbt",
    "Tableau",
    "Power BI",
]


def _mentions(text: str, technology: str) -> bool:
    return re.search(rf"(?<!\w){re.escape(technology.lower())}(?!\w)", text.lower()) is not None


def dictionary_check(
    letter: str,
    *,
    resume_text: str,
    allowed_facts: str,
    resume_skills: list[str],
) -> list[str]:
    """Технологии, упомянутые в письме, но отсутствующие у кандидата.

    Находится мгновенно и без затрат, поэтому идёт первой (§18).
    """
    sources = f"{resume_text}\n{allowed_facts}\n{' '.join(resume_skills)}"
    vocabulary = {*KNOWN_TECHNOLOGIES, *resume_skills}

    return [
        technology
        for technology in sorted(vocabulary)
        if _mentions(letter, technology) and not _mentions(sources, technology)
    ]


# «[укажите сумму]», «[Имя]» — модель оставляет такие места, когда работодатель
# спрашивает то, чего нет в резюме. Отправлять письмо с ними нельзя
_PLACEHOLDER = re.compile(r"\[[^\[\]\n]{2,80}\]")


def find_placeholders(letter: str) -> list[str]:
    """Незаполненные места в квадратных скобках, без markdown-ссылок вида [текст](url)."""
    return [
        match.group(0)
        for match in _PLACEHOLDER.finditer(letter)
        if letter[match.end() : match.end() + 1] != "("
    ]


async def fact_check(
    session: AsyncSession,
    *,
    letter: str,
    digest: dict[str, Any] | None,
    resume_text: str,
    allowed_facts: str,
) -> tuple[FactCheckResponse, LLMResult]:
    template = await prompts.get_text(session, PromptKey.FACT_CHECK)
    prompt = prompts.render(
        template,
        {
            "letter": letter,
            "resume_digest": json.dumps(digest, ensure_ascii=False, indent=1) if digest else "—",
            # Без полного текста проверка считала выдумкой всё, чего нет в выжимке:
            # компании, сроки, Flyway — хотя в резюме они есть
            "resume_text": resume_text,
            "allowed_facts": allowed_facts,
        },
    )
    provider = await router.provider_for_step(session, PromptKey.FACT_CHECK)
    try:
        return await router.call(provider, prompt, FactCheckResponse)
    finally:
        await provider.close()
