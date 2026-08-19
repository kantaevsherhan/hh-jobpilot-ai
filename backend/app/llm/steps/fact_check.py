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
    "AWS",
    "Azure",
    "GCP",
    "Kubernetes",
    "Docker",
    "Terraform",
    "Ansible",
    "Kafka",
    "RabbitMQ",
    "Redis",
    "Elasticsearch",
    "ClickHouse",
    "MongoDB",
    "PostgreSQL",
    "MySQL",
    "Oracle",
    "MSSQL",
    "SQLite",
    "Python",
    "Django",
    "FastAPI",
    "Flask",
    "Celery",
    "Node.js",
    "NestJS",
    "Express",
    "TypeScript",
    "JavaScript",
    "Vue",
    "React",
    "Angular",
    "Svelte",
    "Nuxt",
    "Next.js",
    "Go",
    "Rust",
    "Java",
    "Spring",
    "Kotlin",
    "Swift",
    "C#",
    ".NET",
    "PHP",
    "Laravel",
    "Symfony",
    "Yii2",
    "Bitrix",
    "1С",
    "GraphQL",
    "gRPC",
    "REST",
    "Kong",
    "Nginx",
    "GitLab CI",
    "GitHub Actions",
    "Jenkins",
    "ArgoCD",
    "Spark",
    "Airflow",
    "Hadoop",
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


async def fact_check(
    session: AsyncSession,
    *,
    letter: str,
    digest: dict[str, Any] | None,
    allowed_facts: str,
) -> tuple[FactCheckResponse, LLMResult]:
    template = await prompts.get_text(session, PromptKey.FACT_CHECK)
    prompt = prompts.render(
        template,
        {
            "letter": letter,
            "resume_digest": json.dumps(digest, ensure_ascii=False, indent=1) if digest else "—",
            "allowed_facts": allowed_facts,
        },
    )
    provider = await router.provider_for_step(session, PromptKey.FACT_CHECK)
    try:
        return await router.call(provider, prompt, FactCheckResponse)
    finally:
        await provider.close()
