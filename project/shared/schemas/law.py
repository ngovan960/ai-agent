from uuid import UUID

from pydantic import BaseModel


class Law(BaseModel):
    id: str
    name: str
    severity: str
    description: str
    check_rule: str
    category: str


class LawViolationResponse(BaseModel):
    task_id: UUID | None = None
    law_id: str
    law_name: str
    severity: str
    violation_details: str
    location: str | None = None


class LawListResponse(BaseModel):
    laws: list[Law]
    total: int


class ViolationReport(BaseModel):
    task_id: UUID | None = None
    violations: list[LawViolationResponse]
    total_violations: int
    critical_count: int
    high_count: int
    medium_count: int
