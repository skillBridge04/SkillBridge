from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class ResumeSkillResponse(BaseModel):
    id: int
    resume_id: int
    skill_id: int
    skill_name: str
    source: str
    confidence: Decimal | None

    model_config = ConfigDict(from_attributes=True)