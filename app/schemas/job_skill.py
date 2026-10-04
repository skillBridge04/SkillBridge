from pydantic import BaseModel, ConfigDict


# =========================================================
# ADD SKILL TO JOB
# =========================================================

class JobSkillCreate(BaseModel):
    skill_id: int
    is_required: bool = True


# =========================================================
# UPDATE JOB SKILL
# =========================================================

class JobSkillUpdate(BaseModel):
    is_required: bool


# =========================================================
# JOB SKILL RESPONSE
# =========================================================

class JobSkillResponse(BaseModel):
    id: int
    job_id: int
    skill_id: int
    is_required: bool

    model_config = ConfigDict(
        from_attributes=True,
    )