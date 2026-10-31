from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
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
# HELPER: GET THE CURRENT EMPLOYER'S COMPANY
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


# =========================================================
# HELPER: GET A JOB OWNED BY THE EMPLOYER
# =========================================================

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


# =========================================================
# HELPER: UPDATE AUDIT FIELD WHEN AVAILABLE
# =========================================================

def set_updated_by(
    obj,
    user_id: int,
) -> None:
    """
    Set updated_by_id if the model has that field.
    """

    if hasattr(obj, "updated_by_id"):
        obj.updated_by_id = user_id


# =========================================================
# HELPER: COMMIT DATABASE CHANGES SAFELY
# =========================================================

def commit_changes(
    db: Session,
    error_message: str,
) -> None:
    """
    Commit changes and handle database integrity errors.
    """

    try:
        db.commit()

    except IntegrityError:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=error_message,
        )


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

    existing_name = db.scalar(
        select(Company).where(
            Company.name == company_data.name
        )
    )

    if existing_name:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A company with this name already exists.",
        )

    company = Company(
        employer_id=current_employer.id,
        name=company_data.name,
        industry=company_data.industry,
        location=company_data.location,
        website=company_data.website,
        description=company_data.description,
    )

    # Populate audit fields if available.
    if hasattr(company, "created_by_id"):
        company.created_by_id = current_employer.id

    if hasattr(company, "updated_by_id"):
        company.updated_by_id = current_employer.id

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

    # Prevent blank company names.
    if "name" in update_data:
        if not update_data["name"] or not update_data["name"].strip():
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Company name cannot be empty.",
            )

        update_data["name"] = update_data["name"].strip()

        existing_name = db.scalar(
            select(Company).where(
                Company.name == update_data["name"],
                Company.id != company.id,
            )
        )

        if existing_name:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A company with this name already exists.",
            )

    # Apply only fields provided by the client.
    for field, value in update_data.items():
        if hasattr(company, field):
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

    # Validate salary range.
    if (
        job_data.salary_min is not None
        and job_data.salary_max is not None
        and job_data.salary_min > job_data.salary_max
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Minimum salary cannot exceed maximum salary.",
        )

    # Validate job title.
    if not job_data.title or not job_data.title.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Job title cannot be empty.",
        )

    job = Job(
        company_id=company.id,
        title=job_data.title.strip(),
        location=job_data.location,
        employment_type=job_data.employment_type,
        salary_min=job_data.salary_min,
        salary_max=job_data.salary_max,
        currency=job_data.currency,
        experience_required=job_data.experience_required,
        education_required=job_data.education_required,
        description=job_data.description,
        application_url=job_data.application_url,
        posted_at=job_data.posted_at or datetime.now(timezone.utc),
        deadline=job_data.deadline,
    )

    if hasattr(job, "created_by_id"):
        job.created_by_id = current_employer.id

    if hasattr(job, "updated_by_id"):
        job.updated_by_id = current_employer.id

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
        .where(Job.company_id == company.id)
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

    # Validate salary range using the final values.
    new_salary_min = update_data.get(
        "salary_min",
        job.salary_min,
    )

    new_salary_max = update_data.get(
        "salary_max",
        job.salary_max,
    )

    if (
        new_salary_min is not None
        and new_salary_max is not None
        and new_salary_min > new_salary_max
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Minimum salary cannot exceed maximum salary.",
        )

    # Validate title if supplied.
    if "title" in update_data:
        title = update_data["title"]

        if not title or not title.strip():
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Job title cannot be empty.",
            )

        update_data["title"] = title.strip()

    # Apply the changes.
    for field, value in update_data.items():
        if hasattr(job, field):
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

    Note: This is a hard delete, not a soft delete.
    """

    job = get_employer_job(
        db=db,
        employer=current_employer,
        job_id=job_id,
    )

    try:
        db.delete(job)
        db.commit()

    except IntegrityError:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "This job cannot be deleted because related records "
                "still reference it. Remove those records first."
            ),
        )

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
    """

    job = get_employer_job(
        db=db,
        employer=current_employer,
        job_id=job_id,
    )

    skill = db.get(
        Skill,
        skill_data.skill_id,
    )

    if skill is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Skill not found.",
        )

    # Do not assign inactive skills when the model has status.
    skill_status = getattr(skill, "status", None)

    if (
        skill_status is not None
        and str(skill_status).upper() != "ACTIVE"
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This skill is not active and cannot be assigned.",
        )

    existing_link = db.scalar(
        select(JobSkill).where(
            JobSkill.job_id == job.id,
            JobSkill.skill_id == skill.id,
        )
    )

    if existing_link:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This skill is already assigned to the job.",
        )

    job_skill = JobSkill(
        job_id=job.id,
        skill_id=skill.id,
        is_required=skill_data.is_required,
    )

    if hasattr(job_skill, "created_by_id"):
        job_skill.created_by_id = current_employer.id

    if hasattr(job_skill, "updated_by_id"):
        job_skill.updated_by_id = current_employer.id

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
    List skills assigned to an employer-owned job.
    """

    job = get_employer_job(
        db=db,
        employer=current_employer,
        job_id=job_id,
    )

    job_skills = db.scalars(
        select(JobSkill)
        .where(JobSkill.job_id == job.id)
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
    Change whether a skill is required for an employer-owned job.
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
        )
    )

    if job_skill is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="This skill is not assigned to the job.",
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
    Remove a skill from an employer-owned job.
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
        )
    )

    if job_skill is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="This skill is not assigned to the job.",
        )

    try:
        db.delete(job_skill)
        db.commit()

    except IntegrityError:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Unable to remove this skill.",
        )

    return None
