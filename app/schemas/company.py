from pydantic import BaseModel, ConfigDict, Field


# =========================================================
# CREATE COMPANY
# =========================================================

class CompanyCreate(BaseModel):
    name: str = Field(
        min_length=2,
        max_length=255,
    )

    industry: str | None = Field(
        default=None,
        max_length=150,
    )

    location: str | None = Field(
        default=None,
        max_length=255,
    )

    website: str | None = Field(
        default=None,
        max_length=500,
    )

    description: str | None = None


# =========================================================
# UPDATE COMPANY
# =========================================================

class CompanyUpdate(BaseModel):
    name: str | None = Field(
        default=None,
        min_length=2,
        max_length=255,
    )

    industry: str | None = Field(
        default=None,
        max_length=150,
    )

    location: str | None = Field(
        default=None,
        max_length=255,
    )

    website: str | None = Field(
        default=None,
        max_length=500,
    )

    description: str | None = None


# =========================================================
# COMPANY RESPONSE
# =========================================================

class CompanyResponse(BaseModel):
    id: int
    employer_id: int | None

    name: str
    industry: str | None
    location: str | None
    website: str | None
    description: str | None

    model_config = ConfigDict(
        from_attributes=True,
    )