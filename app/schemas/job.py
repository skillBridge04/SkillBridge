from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


# =========================================================
# CREATE JOB
# =========================================================

class JobCreate(BaseModel):
    

    title: str = Field(
        min_length=2,
        max_length=255,
    )

    location: str | None = Field(
        default=None,
        max_length=255,
    )

    employment_type: str | None = Field(
        default=None,
        max_length=50,
    )

    salary_min: Decimal | None = None

    salary_max: Decimal | None = None

    currency: str = Field(
        default="BDT",
        max_length=10,
    )

    experience_required: str | None = Field(
        default=None,
        max_length=100,
    )

    education_required: str | None = Field(
        default=None,
        max_length=255,
    )

    description: str | None = None

    application_url: str | None = Field(
        default=None,
        max_length=500,
    )

    posted_at: datetime | None = None

    deadline: datetime | None = None


# =========================================================
# UPDATE JOB
# =========================================================

class JobUpdate(BaseModel):
    title: str | None = Field(
        default=None,
        min_length=2,
        max_length=255,
    )

    location: str | None = Field(
        default=None,
        max_length=255,
    )

    employment_type: str | None = Field(
        default=None,
        max_length=50,
    )

    salary_min: Decimal | None = None

    salary_max: Decimal | None = None

    currency: str | None = Field(
        default=None,
        max_length=10,
    )

    experience_required: str | None = Field(
        default=None,
        max_length=100,
    )

    education_required: str | None = Field(
        default=None,
        max_length=255,
    )

    description: str | None = None

    application_url: str | None = Field(
        default=None,
        max_length=500,
    )

    posted_at: datetime | None = None

    deadline: datetime | None = None


# =========================================================
# JOB RESPONSE
# =========================================================

class JobResponse(BaseModel):
    id: int
    company_id: int

    title: str
    location: str | None
    employment_type: str | None

    salary_min: Decimal | None
    salary_max: Decimal | None
    currency: str

    experience_required: str | None
    education_required: str | None

    description: str | None
    application_url: str | None

    posted_at: datetime | None
    deadline: datetime | None

    model_config = ConfigDict(
        from_attributes=True,
    )