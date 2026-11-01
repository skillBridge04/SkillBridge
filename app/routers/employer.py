
from datetime import datetime, timezone
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import require_employer

from app.models.user import User
from app.models.company import Company
from app.models.job import Job
from app.models.skill import Skill
from app.models.job_skill import JobSkill

from app.schemas.company import (
    CompanyCreate,
    CompanyResponse,
    CompanyUpdate,
)

from app.schemas.job import (
    JobCreate,
    JobResponse,
    JobUpdate,
)

from app.schemas.job_skill import (
    JobSkillCreate,
    JobSkillResponse,
    JobSkillUpdate,
)


# =========================================================
# ROUTER CONFIGURATION
# =========================================================

router = APIRouter(
    prefix="/api/employer",
    tags=["Employer"],
)


# =========================================================
# HELPER FUNCTIONS
# =========================================================

def get_employer_company(
    db: Session,
    employer: User,
) -> Company:
    """
    Return the company belonging to the logged-in employer.
    """

    company = db.scalar(
        select(Company).where(
            Company.employer_id == employer.id
        )
    )

    if company is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="You have not created a company yet.",
        )

    return company


def get_employer_job(
    db: Session,
    employer: User,
    job_id: int,
) -> Job:
    """
    Return a job only if it belongs to the employer's company.
    """

    company = get_employer_company(
        db=db,
        employer=employer,
    )

    job = db.scalar(
        select(Job).where(
            Job.id == job_id,
            Job.company_id == company.id,
        )
    )

    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found in your company.",
        )

    return job


def set_created_by(
    obj,
    user_id: int,
) -> None:
    """
    Set created_by_id when the model supports it.
    """

    if hasattr(obj, "created_by_id"):
        obj.created_by_id = user_id


def set_updated_by(
    obj,
    user_id: int,
) -> None:
    """
    Set updated_by_id when the model supports it.
    """

    if hasattr(obj, "updated_by_id"):
        obj.updated_by_id = user_id


def commit_changes(
    db: Session,
    error_message: str,
) -> None:
    """
    Commit database changes safely.

    Roll back if a database integrity error occurs.
    """

    try:
        db.commit()

    except IntegrityError as exc:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=error_message,
        ) from exc


def validate_salary_range(
    salary_min,
    salary_max,
) -> None:
    """
    Validate the minimum and maximum salary.
    """

    if (
        salary_min is not None
        and salary_max is not None
        and salary_min > salary_max
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Minimum salary cannot exceed maximum salary.",
        )


def validate_optional_http_url(
    value: str | None,
    field_name: str,
) -> str | None:
    """
    Validate optional HTTP/HTTPS URLs.

    Empty values are converted to None.
    """

    if value is None:
        return None

    cleaned_value = value.strip()

    if not cleaned_value:
        return None

    parsed = urlparse(cleaned_value)

    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.netloc
        or any(char.isspace() for char in cleaned_value)
        or any(ord(char) < 32 for char in cleaned_value)
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Enter a valid HTTP or HTTPS {field_name} URL.",
        )

    return cleaned_value


# =========================================================
# COMPANY MANAGEMENT
# =========================================================


# ---------------------------------------------------------
# CREATE COMPANY
# ---------------------------------------------------------

@router.post(
    "/company",
    response_model=CompanyResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_company(
    company_data: CompanyCreate,
    db: Session = Depends(get_db),
    current_employer: User = Depends(require_employer),
):
    """
    Create a company for the logged-in employer.

    Each employer can own only one company.
    """

    existing_company = db.scalar(
        select(Company).where(
            Company.employer_id == current_employer.id
        )
    )

    if existing_company:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You already have a company.",
        )

    # Validate company name.

    company_name = company_data.name.strip()

    if len(company_name) < 2:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Company name must contain at least two characters.",
        )

    # Check for duplicate names without case sensitivity.

    existing_name = db.scalar(
        select(Company).where(
            func.lower(Company.name) == company_name.lower()
        )
    )

    if existing_name:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A company with this name already exists.",
        )

    company = Company(
        employer_id=current_employer.id,
        name=company_name,
        industry=company_data.industry,
        location=company_data.location,
        website=validate_optional_http_url(
            company_data.website,
            "company website",
        ),
        description=company_data.description,
        status="ACTIVE",
    )

    set_created_by(
        company,
        current_employer.id,
    )

    set_updated_by(
        company,
        current_employer.id,
    )

    db.add(company)

    commit_changes(
        db,
        "Unable to create company. The company may already exist.",
    )

    db.refresh(company)

    return company


# ---------------------------------------------------------
# GET MY COMPANY
# ---------------------------------------------------------

@router.get(
    "/company",
    response_model=CompanyResponse,
)
def get_my_company(
    db: Session = Depends(get_db),
    current_employer: User = Depends(require_employer),
):
    """
    Get the logged-in employer's company.
    """

    return get_employer_company(
        db=db,
        employer=current_employer,
    )


# ---------------------------------------------------------
# UPDATE MY COMPANY
# ---------------------------------------------------------

@router.patch(
    "/company",
    response_model=CompanyResponse,
)
def update_my_company(
    company_data: CompanyUpdate,
    db: Session = Depends(get_db),
    current_employer: User = Depends(require_employer),
):
    """
    Update the logged-in employer's company.
    """

    company = get_employer_company(
        db=db,
        employer=current_employer,
    )

    update_data = company_data.model_dump(
        exclude_unset=True
    )

    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Provide at least one field to update.",
        )

    # Validate company name.

    if "name" in update_data:

        new_name = update_data["name"]

        if new_name is None or not new_name.strip():
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Company name cannot be empty.",
            )

        new_name = new_name.strip()

        if len(new_name) < 2:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Company name must contain at least two characters.",
            )

        duplicate = db.scalar(
            select(Company).where(
                func.lower(Company.name) == new_name.lower(),
                Company.id != company.id,
            )
        )

        if duplicate:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A company with this name already exists.",
            )

        update_data["name"] = new_name

    # Validate website if supplied.

    if "website" in update_data:
        update_data["website"] = validate_optional_http_url(
            update_data["website"],
            "company website",
        )

    allowed_fields = {
        "name",
        "industry",
        "location",
        "website",
        "description",
    }

    for field, value in update_data.items():
        if field in allowed_fields:
            setattr(company, field, value)

    set_updated_by(
        company,
        current_employer.id,
    )

    commit_changes(
        db,
        "Unable to update company because of a database conflict.",
    )

    db.refresh(company)

    return company


# =========================================================
# SKILL CATALOG
# =========================================================

# ---------------------------------------------------------
# GET AVAILABLE SKILLS
# ---------------------------------------------------------

@router.get(
    "/skills",
)
def get_available_skills(
    db: Session = Depends(get_db),
    current_employer: User = Depends(require_employer),
):
    """
    Return all active skills.

    The Employer Dashboard uses this endpoint
    to populate the required-skills dropdown.
    """

    skills = db.scalars(
        select(Skill)
        .where(
            Skill.status == "ACTIVE"
        )
        .order_by(Skill.name)
    ).all()

    return [
        {
            "id": skill.id,
            "name": skill.name,
            "category": skill.category,
        }
        for skill in skills
    ]


# =========================================================
# JOB MANAGEMENT
# =========================================================


# ---------------------------------------------------------
# CREATE JOB
# ---------------------------------------------------------

@router.post(
    "/jobs",
    response_model=JobResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_job(
    job_data: JobCreate,
    db: Session = Depends(get_db),
    current_employer: User = Depends(require_employer),
):
    """
    Create a job under the logged-in employer's company.
    """

    company = get_employer_company(
        db=db,
        employer=current_employer,
    )

    # Validate salary.

    validate_salary_range(
        job_data.salary_min,
        job_data.salary_max,
    )

    # Validate job title.

    title = job_data.title.strip()

    if len(title) < 2:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Job title must contain at least two characters.",
        )

    # Validate currency.

    currency = job_data.currency.strip().upper()

    if not currency:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Currency cannot be empty.",
        )

    # Validate application URL.

    application_url = validate_optional_http_url(
        job_data.application_url,
        "application",
    )

    # Create job.

    job = Job(
        company_id=company.id,
        title=title,
        location=job_data.location,
        employment_type=job_data.employment_type,
        salary_min=job_data.salary_min,
        salary_max=job_data.salary_max,
        currency=currency,
        experience_required=job_data.experience_required,
        education_required=job_data.education_required,
        description=job_data.description,
        application_url=application_url,
        posted_at=job_data.posted_at or datetime.now(timezone.utc),
        deadline=job_data.deadline,
        status="ACTIVE",
    )

    set_created_by(
        job,
        current_employer.id,
    )

    set_updated_by(
        job,
        current_employer.id,
    )

    db.add(job)

    commit_changes(
        db,
        "Unable to create the job because of a database conflict.",
    )

    db.refresh(job)

    return job


# ---------------------------------------------------------
# GET ALL MY JOBS
# ---------------------------------------------------------

@router.get(
    "/jobs",
    response_model=list[JobResponse],
)
def get_my_jobs(
    db: Session = Depends(get_db),
    current_employer: User = Depends(require_employer),
):
    """
    List all jobs belonging to the logged-in employer.
    """

    company = get_employer_company(
        db=db,
        employer=current_employer,
    )

    jobs = db.scalars(
        select(Job)
        .where(
            Job.company_id == company.id
        )
        .order_by(Job.id.desc())
    ).all()

    return jobs


# ---------------------------------------------------------
# GET ONE JOB
# ---------------------------------------------------------

@router.get(
    "/jobs/{job_id}",
    response_model=JobResponse,
)
def get_job(
    job_id: int,
    db: Session = Depends(get_db),
    current_employer: User = Depends(require_employer),
):
    """
    Get one job belonging to the logged-in employer.
    """

    return get_employer_job(
        db=db,
        employer=current_employer,
        job_id=job_id,
    )


# ---------------------------------------------------------
# UPDATE JOB
# ---------------------------------------------------------

@router.patch(
    "/jobs/{job_id}",
    response_model=JobResponse,
)
def update_job(
    job_id: int,
    job_data: JobUpdate,
    db: Session = Depends(get_db),
    current_employer: User = Depends(require_employer),
):
    """
    Update a job belonging to the logged-in employer.
    """

    job = get_employer_job(
        db=db,
        employer=current_employer,
        job_id=job_id,
    )

    update_data = job_data.model_dump(
        exclude_unset=True
    )

    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Provide at least one field to update.",
        )

    # Validate final salary range.

    new_salary_min = update_data.get(
        "salary_min",
        job.salary_min,
    )

    new_salary_max = update_data.get(
        "salary_max",
        job.salary_max,
    )

    validate_salary_range(
        new_salary_min,
        new_salary_max,
    )

    # Validate title.

    if "title" in update_data:

        title = update_data["title"]

        if title is None or not title.strip():
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Job title cannot be empty.",
            )

        update_data["title"] = title.strip()

    # Validate currency.

    if "currency" in update_data:

        currency = update_data["currency"]

        if currency is None or not currency.strip():
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Currency cannot be empty.",
            )

        update_data["currency"] = currency.strip().upper()

    # Validate application URL.

    if "application_url" in update_data:
        update_data["application_url"] = validate_optional_http_url(
            update_data["application_url"],
            "application",
        )

    allowed_fields = {
        "title",
        "location",
        "employment_type",
        "salary_min",
        "salary_max",
        "currency",
        "experience_required",
        "education_required",
        "description",
        "application_url",
        "posted_at",
        "deadline",
    }

    # Apply changes.

    for field, value in update_data.items():
        if field in allowed_fields:
            setattr(job, field, value)

    set_updated_by(
        job,
        current_employer.id,
    )

    commit_changes(
        db,
        "Unable to update the job because of a database conflict.",
    )

    db.refresh(job)

    return job


# ---------------------------------------------------------
# DELETE JOB
# ---------------------------------------------------------

@router.delete(
    "/jobs/{job_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_job(
    job_id: int,
    db: Session = Depends(get_db),
    current_employer: User = Depends(require_employer),
):
    """
    Permanently delete a job belonging to the employer.

    The Job model has a cascade relationship with JobSkill,
    so associated job-skill records are deleted as well.
    """

    job = get_employer_job(
        db=db,
        employer=current_employer,
        job_id=job_id,
    )

    try:
        db.delete(job)
        db.commit()

    except IntegrityError as exc:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "This job cannot be deleted because related records "
                "still reference it."
            ),
        ) from exc

    return None


# =========================================================
# JOB SKILL MANAGEMENT
# =========================================================


# ---------------------------------------------------------
# ADD SKILL TO JOB
# ---------------------------------------------------------

@router.post(
    "/jobs/{job_id}/skills",
    response_model=JobSkillResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_skill_to_job(
    job_id: int,
    skill_data: JobSkillCreate,
    db: Session = Depends(get_db),
    current_employer: User = Depends(require_employer),
):
    """
    Add a required or optional skill to an employer-owned job.

    Reactivate an old inactive relationship rather than
    creating a duplicate record.
    """

    job = get_employer_job(
        db=db,
        employer=current_employer,
        job_id=job_id,
    )

    # Check the skill.

    skill = db.get(
        Skill,
        skill_data.skill_id,
    )

    if skill is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Skill not found.",
        )

    if skill.status != "ACTIVE":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This skill is inactive and cannot be assigned.",
        )

    # Check existing relationship.

    existing_link = db.scalar(
        select(JobSkill).where(
            JobSkill.job_id == job.id,
            JobSkill.skill_id == skill.id,
        )
    )

    if existing_link:

        if existing_link.status == "ACTIVE":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This skill is already assigned to the job.",
            )

        # Reactivate existing relationship.

        existing_link.status = "ACTIVE"

        existing_link.is_required = skill_data.is_required

        set_updated_by(
            existing_link,
            current_employer.id,
        )

        commit_changes(
            db,
            "Unable to reactivate this job skill.",
        )

        db.refresh(existing_link)

        return existing_link

    # Create new relationship.

    job_skill = JobSkill(
        job_id=job.id,
        skill_id=skill.id,
        is_required=skill_data.is_required,
        status="ACTIVE",
    )

    set_created_by(
        job_skill,
        current_employer.id,
    )

    set_updated_by(
        job_skill,
        current_employer.id,
    )

    db.add(job_skill)

    commit_changes(
        db,
        "This skill is already assigned to the job.",
    )

    db.refresh(job_skill)

    return job_skill


# ---------------------------------------------------------
# GET ALL SKILLS FOR A JOB
# ---------------------------------------------------------

@router.get(
    "/jobs/{job_id}/skills",
    response_model=list[JobSkillResponse],
)
def get_job_skills(
    job_id: int,
    db: Session = Depends(get_db),
    current_employer: User = Depends(require_employer),
):
    """
    Get active skills assigned to an employer-owned job.
    """

    job = get_employer_job(
        db=db,
        employer=current_employer,
        job_id=job_id,
    )

    job_skills = db.scalars(
        select(JobSkill)
        .where(
            JobSkill.job_id == job.id,
            JobSkill.status == "ACTIVE",
        )
        .order_by(JobSkill.id)
    ).all()

    return job_skills


# ---------------------------------------------------------
# UPDATE A JOB SKILL
# ---------------------------------------------------------

@router.patch(
    "/jobs/{job_id}/skills/{skill_id}",
    response_model=JobSkillResponse,
)
def update_job_skill(
    job_id: int,
    skill_id: int,
    skill_data: JobSkillUpdate,
    db: Session = Depends(get_db),
    current_employer: User = Depends(require_employer),
):
    """
    Update whether a skill is required for an employer-owned job.
    """

    job = get_employer_job(
        db=db,
        employer=current_employer,
        job_id=job_id,
    )

    job_skill = db.scalar(
        select(JobSkill).where(
            JobSkill.job_id == job.id,
            JobSkill.skill_id == skill_id,
            JobSkill.status == "ACTIVE",
        )
    )

    if job_skill is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="This active skill is not assigned to the job.",
        )

    job_skill.is_required = skill_data.is_required

    set_updated_by(
        job_skill,
        current_employer.id,
    )

    commit_changes(
        db,
        "Unable to update this job skill.",
    )

    db.refresh(job_skill)

    return job_skill


# ---------------------------------------------------------
# REMOVE A SKILL FROM A JOB
# ---------------------------------------------------------

@router.delete(
    "/jobs/{job_id}/skills/{skill_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_job_skill(
    job_id: int,
    skill_id: int,
    db: Session = Depends(get_db),
    current_employer: User = Depends(require_employer),
):
    """
    Deactivate a skill assigned to an employer-owned job.

    The record is preserved for audit history.
    """

    job = get_employer_job(
        db=db,
        employer=current_employer,
        job_id=job_id,
    )

    job_skill = db.scalar(
        select(JobSkill).where(
            JobSkill.job_id == job.id,
            JobSkill.skill_id == skill_id,
            JobSkill.status == "ACTIVE",
        )
    )

    if job_skill is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="This active skill is not assigned to the job.",
        )

    job_skill.status = "INACTIVE"

    set_updated_by(
        job_skill,
        current_employer.id,
    )

    try:
        db.commit()

    except IntegrityError as exc:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Unable to remove this skill.",
        ) from exc

    return None
