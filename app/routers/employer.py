from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import require_employer
from app.models.company import Company
from app.models.user import User
from app.schemas.company import (
    CompanyCreate,
    CompanyResponse,
    CompanyUpdate,
)


router = APIRouter(
    prefix="/api/employer",
    tags=["Employer"],
)

from datetime import datetime, timezone

from app.models.job import Job
from app.schemas.job import (
    JobCreate,
    JobResponse,
    JobUpdate,
)

from app.models.skill import Skill
from app.models.job_skill import JobSkill

from app.schemas.job_skill import (
    JobSkillCreate,
    JobSkillResponse,
    JobSkillUpdate,
)

# =========================================================
# CREATE COMPANY
# =========================================================

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
    Create a company for the currently logged-in Employer.
    """

    # -----------------------------------------------------
    # Check whether this Employer already owns a company
    # -----------------------------------------------------

    existing_company = db.scalar(
        select(Company).where(
            Company.employer_id == current_employer.id
        )
    )

    if existing_company:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You already have a company",
        )

    # -----------------------------------------------------
    # Check company name
    # -----------------------------------------------------

    existing_name = db.scalar(
        select(Company).where(
            Company.name == company_data.name
        )
    )

    if existing_name:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Company name already exists",
        )

    # -----------------------------------------------------
    # Create company
    # -----------------------------------------------------

    company = Company(
        employer_id=current_employer.id,
        name=company_data.name,
        industry=company_data.industry,
        location=company_data.location,
        website=company_data.website,
        description=company_data.description,
    )

    db.add(company)

    try:
        db.commit()
        db.refresh(company)

    except IntegrityError:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Unable to create company. The company may already exist.",
        )

    return company


# =========================================================
# GET MY COMPANY
# =========================================================

@router.get(
    "/company",
    response_model=CompanyResponse,
)
def get_my_company(
    db: Session = Depends(get_db),
    current_employer: User = Depends(require_employer),
):
    """
    Get the company owned by the currently logged-in Employer.
    """

    company = db.scalar(
        select(Company).where(
            Company.employer_id == current_employer.id
        )
    )

    if company is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="You have not created a company yet",
        )

    return company


# =========================================================
# UPDATE MY COMPANY
# =========================================================

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
    Update the company owned by the currently logged-in Employer.
    """

    company = db.scalar(
        select(Company).where(
            Company.employer_id == current_employer.id
        )
    )

    if company is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="You have not created a company yet",
        )

    # -----------------------------------------------------
    # Update only provided fields
    # -----------------------------------------------------

    update_data = company_data.model_dump(
        exclude_unset=True
    )

    # -----------------------------------------------------
    # Check company name if it is being changed
    # -----------------------------------------------------

    if "name" in update_data:
        existing_name = db.scalar(
            select(Company).where(
                Company.name == update_data["name"],
                Company.id != company.id,
            )
        )

        if existing_name:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Company name already exists",
            )

    # -----------------------------------------------------
    # Apply changes
    # -----------------------------------------------------

    for field, value in update_data.items():
        setattr(company, field, value)

    try:
        db.commit()
        db.refresh(company)

    except IntegrityError:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Unable to update company",
        )

    return company

# =========================================================
# CREATE JOB
# =========================================================

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
    Create a job for the currently logged-in Employer's company.
    """

    # Find the employer's company
    company = db.scalar(
        select(Company).where(
            Company.employer_id == current_employer.id
        )
    )

    if company is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="You must create a company before creating a job",
        )

    # Validate salary range
    if (
        job_data.salary_min is not None
        and job_data.salary_max is not None
        and job_data.salary_min > job_data.salary_max
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Minimum salary cannot be greater than maximum salary",
        )

    # Create job
    job = Job(
        company_id=company.id,
        title=job_data.title,
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

    db.add(job)
    db.commit()
    db.refresh(job)

    return job

# =========================================================
# GET MY JOBS
# =========================================================

@router.get(
    "/jobs",
    response_model=list[JobResponse],
)
def get_my_jobs(
    db: Session = Depends(get_db),
    current_employer: User = Depends(require_employer),
):
    """
    Get all jobs belonging to the currently logged-in Employer.
    """

    company = db.scalar(
        select(Company).where(
            Company.employer_id == current_employer.id
        )
    )

    if company is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="You have not created a company yet",
        )

    jobs = db.scalars(
        select(Job)
        .where(Job.company_id == company.id)
        .order_by(Job.id.desc())
    ).all()

    return jobs

# =========================================================
# GET ONE JOB
# =========================================================

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
    Get one job belonging to the current Employer.
    """

    company = db.scalar(
        select(Company).where(
            Company.employer_id == current_employer.id
        )
    )

    if company is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company not found",
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
            detail="Job not found",
        )

    return job

# =========================================================
# UPDATE JOB
# =========================================================

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
    Update a job belonging to the current Employer.
    """

    company = db.scalar(
        select(Company).where(
            Company.employer_id == current_employer.id
        )
    )

    if company is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company not found",
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
            detail="Job not found",
        )

    update_data = job_data.model_dump(
        exclude_unset=True
    )

    # Check salary range after update
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
            detail="Minimum salary cannot be greater than maximum salary",
        )

    for field, value in update_data.items():
        setattr(job, field, value)

    db.commit()
    db.refresh(job)

    return job

# =========================================================
# DELETE JOB
# =========================================================

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
    Delete a job belonging to the current Employer.
    """

    company = db.scalar(
        select(Company).where(
            Company.employer_id == current_employer.id
        )
    )

    if company is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company not found",
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
            detail="Job not found",
        )

    db.delete(job)
    db.commit()

    return None

# =========================================================
# ADD SKILL TO JOB
# =========================================================

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
    Add a skill to a job belonging to the current Employer.
    """

    # Find employer's company
    company = db.scalar(
        select(Company).where(
            Company.employer_id == current_employer.id
        )
    )

    if company is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company not found",
        )

    # Check whether the job belongs to this employer
    job = db.scalar(
        select(Job).where(
            Job.id == job_id,
            Job.company_id == company.id,
        )
    )

    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found",
        )

    # Check whether skill exists
    skill = db.get(Skill, skill_data.skill_id)

    if skill is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Skill not found",
        )

    # Check duplicate skill
    existing_job_skill = db.scalar(
        select(JobSkill).where(
            JobSkill.job_id == job_id,
            JobSkill.skill_id == skill_data.skill_id,
        )
    )

    if existing_job_skill:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This skill is already added to the job",
        )

    # Create job-skill relationship
    job_skill = JobSkill(
        job_id=job_id,
        skill_id=skill_data.skill_id,
        is_required=skill_data.is_required,
    )

    db.add(job_skill)
    db.commit()
    db.refresh(job_skill)

    return job_skill

# =========================================================
# GET JOB SKILLS
# =========================================================

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
    Get all skills belonging to a job owned by the current Employer.
    """

    # Find employer's company
    company = db.scalar(
        select(Company).where(
            Company.employer_id == current_employer.id
        )
    )

    if company is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company not found",
        )

    # Check job ownership
    job = db.scalar(
        select(Job).where(
            Job.id == job_id,
            Job.company_id == company.id,
        )
    )

    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found",
        )

    # Get skills
    job_skills = db.scalars(
        select(JobSkill)
        .where(JobSkill.job_id == job_id)
        .order_by(JobSkill.id)
    ).all()

    return job_skills

# =========================================================
# UPDATE JOB SKILL
# =========================================================

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
    Change a job skill between required and optional.
    """

    # Find employer's company
    company = db.scalar(
        select(Company).where(
            Company.employer_id == current_employer.id
        )
    )

    if company is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company not found",
        )

    # Check job ownership
    job = db.scalar(
        select(Job).where(
            Job.id == job_id,
            Job.company_id == company.id,
        )
    )

    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found",
        )

    # Find job skill
    job_skill = db.scalar(
        select(JobSkill).where(
            JobSkill.job_id == job_id,
            JobSkill.skill_id == skill_id,
        )
    )

    if job_skill is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Skill is not assigned to this job",
        )

    # Update
    job_skill.is_required = skill_data.is_required

    db.commit()
    db.refresh(job_skill)

    return job_skill

# =========================================================
# DELETE SKILL FROM JOB
# =========================================================

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
    Remove a skill from a job owned by the current Employer.
    """

    # Find employer's company
    company = db.scalar(
        select(Company).where(
            Company.employer_id == current_employer.id
        )
    )

    if company is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company not found",
        )

    # Check job ownership
    job = db.scalar(
        select(Job).where(
            Job.id == job_id,
            Job.company_id == company.id,
        )
    )

    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found",
        )

    # Find job skill
    job_skill = db.scalar(
        select(JobSkill).where(
            JobSkill.job_id == job_id,
            JobSkill.skill_id == skill_id,
        )
    )

    if job_skill is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Skill is not assigned to this job",
        )

    db.delete(job_skill)
    db.commit()

    return None

