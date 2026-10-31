from typing import Literal
from datetime import datetime
from decimal import Decimal

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    field_validator,
)


# =========================================
# CREATE ADMIN ACCOUNT
# =========================================

class AdminCreate(BaseModel):
    name: str = Field(
        min_length=2,
        max_length=100,
    )

    email: EmailStr

    password: str = Field(
        min_length=8,
        max_length=128,
    )

    model_config = ConfigDict(extra="forbid")

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        value = value.strip()

        if len(value) < 2:
            raise ValueError(
                "Name must contain at least 2 non-space characters."
            )

        return value


# =========================================
# SKILL SCHEMAS
# =========================================

class SkillCreate(BaseModel):
    name: str = Field(
        min_length=1,
        max_length=100,
    )

    category: str | None = Field(
        default=None,
        max_length=100,
    )

    model_config = ConfigDict(extra="forbid")

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        value = value.strip()

        if not value:
            raise ValueError("Skill name cannot be empty.")

        return value

    @field_validator("category")
    @classmethod
    def validate_category(cls, value: str | None) -> str | None:
        if value is None:
            return None

        return value.strip() or None


class SkillUpdate(BaseModel):
    name: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
    )

    category: str | None = Field(
        default=None,
        max_length=100,
    )

    status: Literal["ACTIVE", "INACTIVE"] | None = None

    model_config = ConfigDict(extra="forbid")

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str | None) -> str | None:
        if value is None:
            return None

        value = value.strip()

        if not value:
            raise ValueError("Skill name cannot be empty.")

        return value

    @field_validator("category")
    @classmethod
    def validate_category(cls, value: str | None) -> str | None:
        if value is None:
            return None

        return value.strip() or None


class SkillAdminResponse(BaseModel):
    id: int
    name: str
    category: str | None
    status: str

    model_config = ConfigDict(from_attributes=True)


# =========================================
# COURSE SCHEMAS
# =========================================

class CourseCreate(BaseModel):
    title: str = Field(
        min_length=2,
        max_length=255,
    )

    provider: str = Field(
        min_length=2,
        max_length=100,
    )

    skill_id: int = Field(gt=0)

    level: str | None = Field(
        default=None,
        max_length=50,
    )

    duration: str | None = Field(
        default=None,
        max_length=100,
    )

    url: str = Field(
        min_length=8,
        max_length=500,
    )

    is_free: bool = False

    description: str | None = None

    model_config = ConfigDict(extra="forbid")

    @field_validator("title", "provider")
    @classmethod
    def validate_required_text(cls, value: str) -> str:
        value = value.strip()

        if len(value) < 2:
            raise ValueError(
                "This field must contain at least 2 non-space characters."
            )

        return value

    @field_validator("level", "duration")
    @classmethod
    def normalize_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None

        return value.strip() or None

    @field_validator("url")
    @classmethod
    def normalize_url(cls, value: str) -> str:
        value = value.strip()

        if not value:
            raise ValueError("Course URL cannot be empty.")

        return value

    @field_validator("description")
    @classmethod
    def normalize_description(cls, value: str | None) -> str | None:
        if value is None:
            return None

        return value.strip() or None


class CourseUpdate(BaseModel):
    title: str | None = Field(
        default=None,
        min_length=2,
        max_length=255,
    )

    provider: str | None = Field(
        default=None,
        min_length=2,
        max_length=100,
    )

    skill_id: int | None = Field(
        default=None,
        gt=0,
    )

    level: str | None = Field(
        default=None,
        max_length=50,
    )

    duration: str | None = Field(
        default=None,
        max_length=100,
    )

    url: str | None = Field(
        default=None,
        min_length=8,
        max_length=500,
    )

    is_free: bool | None = None

    description: str | None = None

    status: Literal["ACTIVE", "INACTIVE"] | None = None

    model_config = ConfigDict(extra="forbid")

    @field_validator("title", "provider")
    @classmethod
    def validate_required_text(cls, value: str | None) -> str | None:
        if value is None:
            return None

        value = value.strip()

        if len(value) < 2:
            raise ValueError(
                "This field must contain at least 2 non-space characters."
            )

        return value

    @field_validator("level", "duration")
    @classmethod
    def normalize_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None

        return value.strip() or None

    @field_validator("url")
    @classmethod
    def normalize_url(cls, value: str | None) -> str | None:
        if value is None:
            return None

        return value.strip()

    @field_validator("description")
    @classmethod
    def normalize_description(cls, value: str | None) -> str | None:
        if value is None:
            return None

        return value.strip() or None


class CourseAdminResponse(BaseModel):
    id: int
    title: str
    provider: str
    skill_id: int
    level: str | None
    duration: str | None
    url: str
    is_free: bool
    description: str | None
    status: str

    model_config = ConfigDict(from_attributes=True)

    # =========================================
# ADMIN COMPANY SCHEMAS
# =========================================

class CompanyAdminUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=255)
    industry: str | None = Field(default=None, max_length=150)
    location: str | None = Field(default=None, max_length=255)
    website: str | None = Field(default=None, max_length=500)
    description: str | None = None
    status: Literal["ACTIVE", "INACTIVE"] | None = None

    model_config = ConfigDict(extra="forbid")


class CompanyAdminResponse(BaseModel):
    id: int
    employer_id: int | None
    name: str
    industry: str | None
    location: str | None
    website: str | None
    description: str | None
    status: str

    model_config = ConfigDict(from_attributes=True)


# =========================================
# ADMIN JOB SCHEMAS
# =========================================

class AdminJobCreate(BaseModel):
    company_id: int = Field(gt=0)
    title: str = Field(min_length=2, max_length=255)

    location: str | None = Field(default=None, max_length=255)
    employment_type: str | None = Field(default=None, max_length=50)

    salary_min: Decimal | None = Field(default=None, ge=0)
    salary_max: Decimal | None = Field(default=None, ge=0)
    currency: str = Field(default="BDT", min_length=1, max_length=10)

    experience_required: str | None = Field(default=None, max_length=100)
    education_required: str | None = Field(default=None, max_length=255)

    description: str | None = None
    application_url: str | None = Field(default=None, max_length=500)

    posted_at: datetime | None = None
    deadline: datetime | None = None

    # At least one skill is required for meaningful job matching.
    required_skill_ids: list[int] = Field(min_length=1, max_length=50)

    model_config = ConfigDict(extra="forbid")


class AdminJobUpdate(BaseModel):
    company_id: int | None = Field(default=None, gt=0)
    title: str | None = Field(default=None, min_length=2, max_length=255)

    location: str | None = Field(default=None, max_length=255)
    employment_type: str | None = Field(default=None, max_length=50)

    salary_min: Decimal | None = Field(default=None, ge=0)
    salary_max: Decimal | None = Field(default=None, ge=0)
    currency: str | None = Field(default=None, min_length=1, max_length=10)

    experience_required: str | None = Field(default=None, max_length=100)
    education_required: str | None = Field(default=None, max_length=255)

    description: str | None = None
    application_url: str | None = Field(default=None, max_length=500)

    posted_at: datetime | None = None
    deadline: datetime | None = None

    required_skill_ids: list[int] | None = Field(
        default=None,
        min_length=1,
        max_length=50,
    )

    status: Literal["ACTIVE", "INACTIVE"] | None = None

    model_config = ConfigDict(extra="forbid")


class AdminJobSkillResponse(BaseModel):
    skill_id: int
    name: str
    is_required: bool


class AdminJobResponse(BaseModel):
    id: int
    company_id: int
    company_name: str

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

    status: str
    required_skills: list[AdminJobSkillResponse]

    model_config = ConfigDict(from_attributes=True)
