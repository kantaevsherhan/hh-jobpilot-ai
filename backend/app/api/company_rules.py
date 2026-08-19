"""Правила по компаниям и их проверка (§12, §26)."""

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict, Field

from app.api.deps import Session
from app.core.enums import CompanyRuleAction, MatchType
from app.filters.company import CompanyRuleSpec, matches
from app.storage.models import CompanyRule
from app.storage.repositories import crud

router = APIRouter(prefix="/company-rules", tags=["Правила по компаниям"])


class RuleIn(BaseModel):
    resume_id: int | None = None
    match_type: MatchType = MatchType.CONTAINS
    value: str = Field(min_length=1, max_length=300)
    case_sensitive: bool = False
    action: CompanyRuleAction = CompanyRuleAction.SKIP
    score_delta: int = 0
    note: str | None = None
    enabled: bool = True


class RulePatch(BaseModel):
    match_type: MatchType | None = None
    value: str | None = None
    case_sensitive: bool | None = None
    action: CompanyRuleAction | None = None
    score_delta: int | None = None
    note: str | None = None
    enabled: bool | None = None


class RuleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    resume_id: int | None
    match_type: str
    value: str
    case_sensitive: bool
    action: str
    score_delta: int
    note: str | None
    enabled: bool


@router.get("", response_model=list[RuleOut], summary="Список правил")
async def list_rules(session: Session, resume_id: int | None = None) -> list[CompanyRule]:
    rules = await crud.list_all(session, CompanyRule, order_by=CompanyRule.id)
    if resume_id is None:
        return rules
    # Общие правила (resume_id NULL) действуют для всех резюме
    return [rule for rule in rules if rule.resume_id in (None, resume_id)]


@router.post("", response_model=RuleOut, status_code=201, summary="Добавить правило")
async def create_rule(payload: RuleIn, session: Session) -> CompanyRule:
    return await crud.create(session, CompanyRule, payload.model_dump())


@router.patch("/{rule_id}", response_model=RuleOut, summary="Изменить правило")
async def patch_rule(rule_id: int, payload: RulePatch, session: Session) -> CompanyRule:
    rule = await crud.get_or_404(session, CompanyRule, rule_id, "Правило")
    return await crud.update(session, rule, payload.model_dump(exclude_unset=True))


@router.delete("/{rule_id}", status_code=204, summary="Удалить правило")
async def delete_rule(rule_id: int, session: Session) -> None:
    rule = await crud.get_or_404(session, CompanyRule, rule_id, "Правило")
    await crud.remove(session, rule)


class TestRequest(BaseModel):
    company_name: str
    resume_id: int | None = None


@router.post("/test", summary="Проверить название компании по правилам")
async def test_rules(payload: TestRequest, session: Session) -> dict[str, object]:
    rules = await list_rules(session, payload.resume_id)
    matched = [
        {"id": rule.id, "value": rule.value, "action": rule.action, "score_delta": rule.score_delta}
        for rule in rules
        if rule.enabled
        and matches(
            CompanyRuleSpec(
                match_type=rule.match_type,
                value=rule.value,
                action=rule.action,
                case_sensitive=rule.case_sensitive,
                score_delta=rule.score_delta,
            ),
            payload.company_name,
        )
    ]
    return {"company_name": payload.company_name, "matched": matched}
