from datetime import datetime, timezone
from urllib.parse import urlparse

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    status,
)
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session, selectinload

from app.core.database import get_db
from app.core.dependencies import require_admin
from app.core.security import hash_password

from app.models.user import User
from app.models.skill import Skill
from app.models.course import Course
from app.models.company import Company
from app.models.job import Job
from app.models.job_skill import JobSkill

from app.schemas.auth import UserResponse

from app.schemas.admin import (
    AdminCreate,
    SkillCreate,
    SkillUpdate,
    SkillAdminResponse,
    CourseCreate,
    CourseUpdate,
    CourseAdminResponse,
    CompanyAdminResponse,
    CompanyAdminUpdate,
    AdminJobCreate,
    AdminJobUpdate,
    AdminJobResponse,
)

from app.schemas.company import CompanyCreate


router = APIRouter(
    prefix="/api/admin",
    tags=["Admin"],
)


# =========================================================
# DATABASE HELPER
# =========================================================

def commit_changes(
    db: Session,
    error_message: str = "Database operation failed.",
):
    """
    Commit database changes safely.

    If a database error occurs, roll back the transaction
    and return a readable HTTP error.
    """

    try:
        db.commit()

    except IntegrityError:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=error_message,
        )

    except SQLAlchemyError:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="A database error occurred.",
        )


# =========================================================
# VIEW PENDING EMPLOYERS
# =========================================================

@router.get(
    "/employers/pending",
    response_model=list[UserResponse],
)
def get_pending_employers(
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_admin),
):
    """
    Get all employers waiting for admin approval.
    """

    pending_employers = db.scalars(
        select(User)
        .where(
            User.role == "EMPLOYER",
            User.account_status == "PENDING",
        )
        .order_by(User.id)
    ).all()

    return pending_employers


# =========================================================
# APPROVE EMPLOYER
# =========================================================

@router.patch(
    "/employers/{user_id}/approve",
    response_model=UserResponse,
)
def approve_employer(
    user_id: int,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_admin),
):
    """
    Approve a pending employer.
    """

    employer = db.get(User, user_id)

    if employer is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )

    if employer.role != "EMPLOYER":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This user is not an employer.",
        )

    if employer.account_status != "PENDING":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This employer is not pending approval.",
        )

    employer.account_status = "ACTIVE"

    commit_changes(
        db,
        "Unable to approve this employer.",
    )

    db.refresh(employer)

    return employer


# =========================================================
# REJECT EMPLOYER
# =========================================================

@router.patch(
    "/employers/{user_id}/reject",
    response_model=UserResponse,
)
def reject_employer(
    user_id: int,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_admin),
):
    """
    Reject a pending employer.
    """

    employer = db.get(User, user_id)

    if employer is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )

    if employer.role != "EMPLOYER":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This user is not an employer.",
        )

    if employer.account_status != "PENDING":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This employer is not pending approval.",
        )

    employer.account_status = "REJECTED"

    commit_changes(
        db,
        "Unable to reject this employer.",
    )

    db.refresh(employer)

    return employer


# =========================================================
# CREATE ANOTHER ADMIN
# =========================================================

@router.post(
    "/admins",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_admin(
    admin_data: AdminCreate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_admin),
):
    """
    Create another admin account.

    Only an existing admin can create another admin.
    """

    email = str(admin_data.email).strip().lower()

    existing_user = db.scalar(
        select(User).where(
            func.lower(User.email) == email
        )
    )

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered.",
        )

    name = admin_data.name.strip()

    if not name:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Admin name cannot be empty.",
        )

    new_admin = User(
        name=name,
        email=email,
        password_hash=hash_password(admin_data.password),
        role="ADMIN",
        account_status="ACTIVE",
    )

    db.add(new_admin)

    commit_changes(
        db,
        "Unable to create admin. The email may already exist.",
    )

    db.refresh(new_admin)

    return new_admin


# =========================================================
# LIST ADMINS
# =========================================================

@router.get(
    "/admins",
    response_model=list[UserResponse],
)
def get_admins(
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_admin),
):
    """
    Get all admin accounts.
    """

    admins = db.scalars(
        select(User)
        .where(User.role == "ADMIN")
        .order_by(User.id)
    ).all()

    return admins


# =========================================================
# DEACTIVATE ADMIN
# =========================================================

@router.patch(
    "/admins/{user_id}/deactivate",
    response_model=UserResponse,
)
def deactivate_admin(
    user_id: int,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_admin),
):
    """
    Deactivate another admin account.
    """

    admin = db.get(User, user_id)

    if admin is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )

    if admin.role != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This user is not an admin.",
        )

    if admin.id == current_admin.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot deactivate your own admin account.",
        )

    admin.account_status = "INACTIVE"

    commit_changes(
        db,
        "Unable to deactivate this admin.",
    )

    db.refresh(admin)

    return admin
# =========================================================
# ACTIVATE ADMIN
# =========================================================

@router.patch(
    "/admins/{user_id}/activate",
    response_model=UserResponse,
)
def activate_admin(
    user_id: int,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_admin),
):
    """
    Activate an admin account.
    """

    admin = db.get(User, user_id)

    if admin is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )

    if admin.role != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This user is not an admin.",
        )

    admin.account_status = "ACTIVE"

    commit_changes(
        db,
        "Unable to activate this admin.",
    )

    db.refresh(admin)

    return admin
# =========================================================
# SKILL MANAGEMENT
# =========================================================

@router.get(
    "/skills",
    response_model=list[SkillAdminResponse],
)
def list_skills(
    include_inactive: bool = Query(default=False),
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_admin),
):
    """
    List skills.

    Inactive skills are excluded by default.
    """

    statement = select(Skill).order_by(Skill.name)

    if not include_inactive:
        statement = statement.where(
            Skill.status == "ACTIVE"
        )

    return db.scalars(statement).all()


# =========================================================
# CREATE SKILL
# =========================================================

@router.post(
    "/skills",
    response_model=SkillAdminResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_skill(
    skill_data: SkillCreate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_admin),
):
    """
    Create a new skill.
    """

    name = skill_data.name.strip()

    if not name:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Skill name cannot be empty.",
        )

    existing = db.scalar(
        select(Skill).where(
            func.lower(Skill.name) == name.lower()
        )
    )

    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A skill with this name already exists.",
        )

    skill = Skill(
        name=name,
        category=(
            skill_data.category.strip()
            if skill_data.category
            else None
        ),
        status="ACTIVE",
        created_by_id=current_admin.id,
        updated_by_id=current_admin.id,
    )

    db.add(skill)

    commit_changes(
        db,
        "Unable to create skill. It may already exist.",
    )

    db.refresh(skill)

    return skill


# =========================================================
# UPDATE SKILL
# =========================================================

@router.patch(
    "/skills/{skill_id}",
    response_model=SkillAdminResponse,
)
def update_skill(
    skill_id: int,
    skill_data: SkillUpdate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_admin),
):
    """
    Update a skill or change its active status.
    """

    skill = db.get(Skill, skill_id)

    if skill is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Skill not found.",
        )

    updates = skill_data.model_dump(
        exclude_unset=True
    )

    if not updates:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Provide at least one field to update.",
        )

    if "name" in updates:
        if updates["name"] is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Skill name cannot be null.",
            )

        new_name = updates["name"].strip()

        if not new_name:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Skill name cannot be empty.",
            )

        duplicate = db.scalar(
            select(Skill).where(
                func.lower(Skill.name) == new_name.lower(),
                Skill.id != skill_id,
            )
        )

        if duplicate:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Another skill already uses this name.",
            )

        updates["name"] = new_name

    if (
        "category" in updates
        and updates["category"] is not None
    ):
        updates["category"] = (
            updates["category"].strip() or None
        )

    for field, value in updates.items():
        setattr(skill, field, value)

    skill.updated_by_id = current_admin.id

    commit_changes(
        db,
        "Unable to update skill.",
    )

    db.refresh(skill)

    return skill


# =========================================================
# COURSE URL VALIDATION
# =========================================================

def validate_course_url(url: str) -> str:
    """
    Validate that a course URL uses HTTP or HTTPS.
    """

    if not isinstance(url, str):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Course URL must be a valid string.",
        )

    cleaned_url = url.strip()

    parsed = urlparse(cleaned_url)

    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.netloc
        or any(char.isspace() for char in cleaned_url)
        or any(ord(char) < 32 for char in cleaned_url)
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Enter a valid HTTP or HTTPS course URL.",
        )

    return cleaned_url


# =========================================================
# LIST COURSES
# =========================================================

@router.get(
    "/courses",
    response_model=list[CourseAdminResponse],
)
def list_courses(
    include_inactive: bool = Query(default=False),
    skill_id: int | None = Query(default=None, gt=0),
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_admin),
):
    """
    List courses, optionally filtered by skill.
    """

    statement = select(Course).order_by(Course.title)

    if not include_inactive:
        statement = statement.where(
            Course.status == "ACTIVE"
        )

    if skill_id is not None:
        statement = statement.where(
            Course.skill_id == skill_id
        )

    return db.scalars(statement).all()


# =========================================================
# CREATE COURSE
# =========================================================

@router.post(
    "/courses",
    response_model=CourseAdminResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_course(
    course_data: CourseCreate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_admin),
):
    """
    Create a course associated with a skill.
    """

    skill = db.get(Skill, course_data.skill_id)

    if skill is None or skill.status != "ACTIVE":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The selected skill does not exist or is inactive.",
        )

    title = course_data.title.strip()
    provider = course_data.provider.strip()

    if not title or not provider:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Course title and provider cannot be empty.",
        )

    course = Course(
        title=title,
        provider=provider,
        skill_id=course_data.skill_id,
        level=course_data.level,
        duration=course_data.duration,
        url=validate_course_url(course_data.url),
        is_free=course_data.is_free,
        description=course_data.description,
        status="ACTIVE",
        created_by_id=current_admin.id,
        updated_by_id=current_admin.id,
    )

    db.add(course)

    commit_changes(
        db,
        "Unable to create course. Check the course information.",
    )

    db.refresh(course)

    return course


# =========================================================
# UPDATE COURSE
# =========================================================

@router.patch(
    "/courses/{course_id}",
    response_model=CourseAdminResponse,
)
def update_course(
    course_id: int,
    course_data: CourseUpdate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_admin),
):
    """
    Update course information or its active status.
    """

    course = db.get(Course, course_id)

    if course is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found.",
        )

    updates = course_data.model_dump(
        exclude_unset=True
    )

    if not updates:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Provide at least one field to update.",
        )

    required_fields = {
        "title",
        "provider",
        "skill_id",
        "url",
        "is_free",
        "status",
    }

    for field in required_fields:
        if field in updates and updates[field] is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"{field} cannot be null.",
            )

    if "title" in updates:
        updates["title"] = updates["title"].strip()

        if not updates["title"]:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Course title cannot be empty.",
            )

    if "provider" in updates:
        updates["provider"] = updates["provider"].strip()

        if not updates["provider"]:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Course provider cannot be empty.",
            )

    if "url" in updates:
        updates["url"] = validate_course_url(
            updates["url"]
        )

    if "skill_id" in updates:
        skill = db.get(Skill, updates["skill_id"])

        if skill is None or skill.status != "ACTIVE":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="The selected skill does not exist or is inactive.",
            )

    for field, value in updates.items():
        setattr(course, field, value)

    course.updated_by_id = current_admin.id

    commit_changes(
        db,
        "Unable to update course.",
    )

    db.refresh(course)

    return course


# =========================================================
# DEACTIVATE COURSE
# =========================================================

@router.delete(
    "/courses/{course_id}",
    response_model=CourseAdminResponse,
)
def deactivate_course(
    course_id: int,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_admin),
):
    """
    Deactivate a course without deleting its database record.
    """

    course = db.get(Course, course_id)

    if course is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found.",
        )

    course.status = "INACTIVE"
    course.updated_by_id = current_admin.id

    commit_changes(
        db,
        "Unable to deactivate course.",
    )

    db.refresh(course)

    return course


# =========================================================
# ADMIN COMPANY MANAGEMENT
# =========================================================

# ---------------------------------------------------------
# LIST COMPANIES
# ---------------------------------------------------------

@router.get(
    "/companies",
    response_model=list[CompanyAdminResponse],
)
def list_companies(
    include_inactive: bool = Query(default=False),
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_admin),
):
    """
    List all companies.
    """

    statement = select(Company).order_by(Company.name)

    if not include_inactive:
        statement = statement.where(
            Company.status == "ACTIVE"
        )

    return db.scalars(statement).all()


# ---------------------------------------------------------
# CREATE COMPANY
# ---------------------------------------------------------

@router.post(
    "/companies",
    response_model=CompanyAdminResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_company(
    company_data: CompanyCreate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_admin),
):
    """
    Create a company from the admin dashboard.
    """

    name = company_data.name.strip()

    if len(name) < 2:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Company name must contain at least two characters.",
        )

    existing = db.scalar(
        select(Company).where(
            func.lower(Company.name) == name.lower()
        )
    )

    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A company with this name already exists.",
        )

    company = Company(
        employer_id=None,
        name=name,
        industry=company_data.industry,
        location=company_data.location,
        website=company_data.website,
        description=company_data.description,
        status="ACTIVE",
        created_by_id=current_admin.id,
        updated_by_id=current_admin.id,
    )

    db.add(company)

    commit_changes(
        db,
        "Unable to create company. Check for duplicate company data.",
    )

    db.refresh(company)

    return company


# ---------------------------------------------------------
# UPDATE COMPANY
# ---------------------------------------------------------

@router.patch(
    "/companies/{company_id}",
    response_model=CompanyAdminResponse,
)
def update_company(
    company_id: int,
    company_data: CompanyAdminUpdate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_admin),
):
    """
    Update company information or status.
    """

    company = db.get(Company, company_id)

    if company is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company not found.",
        )

    updates = company_data.model_dump(
        exclude_unset=True
    )

    if not updates:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Provide at least one field to update.",
        )

    if "name" in updates:
        if updates["name"] is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Company name cannot be null.",
            )

        name = updates["name"].strip()

        if len(name) < 2:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Company name must contain at least two characters.",
            )

        duplicate = db.scalar(
            select(Company).where(
                func.lower(Company.name) == name.lower(),
                Company.id != company_id,
            )
        )

        if duplicate:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Another company already uses this name.",
            )

        updates["name"] = name

    for field, value in updates.items():
        setattr(company, field, value)

    company.updated_by_id = current_admin.id

    commit_changes(
        db,
        "Unable to update company.",
    )

    db.refresh(company)

    return company


# =========================================================
# ADMIN JOB HELPERS
# =========================================================

def _load_admin_job(
    db: Session,
    job_id: int,
) -> Job | None:
    """
    Load a job with its company and required skills.
    """

    return db.scalar(
        select(Job)
        .options(
            selectinload(Job.company),
            selectinload(Job.job_skills).selectinload(
                JobSkill.skill
            ),
        )
        .where(Job.id == job_id)
    )


def _admin_job_response(job: Job) -> dict:
    """
    Build the admin job response with required skills.
    """

    required_skills = []

    for link in job.job_skills:

        skill = link.skill

        if (
            link.status == "ACTIVE"
            and skill is not None
            and skill.status == "ACTIVE"
        ):
            required_skills.append({
                "skill_id": skill.id,
                "name": skill.name,
                "is_required": link.is_required,
            })

    return {
        "id": job.id,
        "company_id": job.company_id,
        "company_name": (
            job.company.name
            if job.company is not None
            else "Company not found"
        ),
        "title": job.title,
        "location": job.location,
        "employment_type": job.employment_type,
        "salary_min": job.salary_min,
        "salary_max": job.salary_max,
        "currency": job.currency,
        "experience_required": job.experience_required,
        "education_required": job.education_required,
        "description": job.description,
        "application_url": job.application_url,
        "posted_at": job.posted_at,
        "deadline": job.deadline,
        "status": job.status,
        "required_skills": required_skills,
    }


def _validate_active_company(
    db: Session,
    company_id: int,
) -> Company:
    """
    Check whether a company exists and is active.
    """

    company = db.get(Company, company_id)

    if company is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company not found.",
        )

    if company.status != "ACTIVE":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot assign a job to an inactive company.",
        )

    return company


def _validate_active_skill_ids(
    db: Session,
    skill_ids: list[int],
) -> list[Skill]:
    """
    Validate selected skills.

    All skill IDs must exist, be active, and be unique.
    """

    if not skill_ids:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Select at least one required skill.",
        )

    if any(skill_id <= 0 for skill_id in skill_ids):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Skill IDs must be positive integers.",
        )

    if len(skill_ids) != len(set(skill_ids)):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="The same skill cannot be selected more than once.",
        )

    skills = db.scalars(
        select(Skill).where(
            Skill.id.in_(skill_ids),
            Skill.status == "ACTIVE",
        )
    ).all()

    if len(skills) != len(skill_ids):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="One or more selected skills do not exist or are inactive.",
        )

    return skills


def _validate_salary_range(
    salary_min,
    salary_max,
) -> None:
    """
    Ensure minimum salary is not greater than maximum salary.
    """

    if (
        salary_min is not None
        and salary_max is not None
        and salary_min > salary_max
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Minimum salary cannot be greater than maximum salary.",
        )


# =========================================================
# LIST JOBS
# =========================================================

@router.get(
    "/jobs",
    response_model=list[AdminJobResponse],
)
def list_admin_jobs(
    include_inactive: bool = Query(default=False),
    company_id: int | None = Query(default=None, gt=0),
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_admin),
):
    """
    List jobs across all companies.
    """

    statement = (
        select(Job)
        .options(
            selectinload(Job.company),
            selectinload(Job.job_skills).selectinload(
                JobSkill.skill
            ),
        )
        .order_by(Job.id.desc())
    )

    if not include_inactive:
        statement = statement.where(
            Job.status == "ACTIVE"
        )

    if company_id is not None:
        statement = statement.where(
            Job.company_id == company_id
        )

    jobs = db.scalars(statement).all()

    if not include_inactive:
        jobs = [
            job for job in jobs
            if (
                job.company is not None
                and job.company.status == "ACTIVE"
            )
        ]

    return [
        _admin_job_response(job)
        for job in jobs
    ]


# =========================================================
# CREATE JOB
# =========================================================

@router.post(
    "/jobs",
    response_model=AdminJobResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_admin_job(
    job_data: AdminJobCreate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_admin),
):
    """
    Create a job for a selected company.
    """

    _validate_active_company(
        db,
        job_data.company_id,
    )

    _validate_salary_range(
        job_data.salary_min,
        job_data.salary_max,
    )

    _validate_active_skill_ids(
        db,
        job_data.required_skill_ids,
    )

    title = job_data.title.strip()

    if not title:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Job title cannot be empty.",
        )

    currency = job_data.currency.strip().upper()

    if not currency:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Currency cannot be empty.",
        )

    job = Job(
        company_id=job_data.company_id,
        title=title,
        location=job_data.location,
        employment_type=job_data.employment_type,
        salary_min=job_data.salary_min,
        salary_max=job_data.salary_max,
        currency=currency,
        experience_required=job_data.experience_required,
        education_required=job_data.education_required,
        description=job_data.description,
        application_url=job_data.application_url,
        posted_at=(
            job_data.posted_at
            or datetime.now(timezone.utc)
        ),
        deadline=job_data.deadline,
        status="ACTIVE",
        created_by_id=current_admin.id,
        updated_by_id=current_admin.id,
    )

    try:
        db.add(job)

        # Save the job first so its ID becomes available.
        db.flush()

        for skill_id in job_data.required_skill_ids:
            db.add(
                JobSkill(
                    job_id=job.id,
                    skill_id=skill_id,
                    is_required=True,
                    status="ACTIVE",
                    created_by_id=current_admin.id,
                    updated_by_id=current_admin.id,
                )
            )

        job_id = job.id

        db.commit()

    except IntegrityError:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unable to create the job. Check the company and required skills.",
        )

    except SQLAlchemyError:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="A database error occurred while creating the job.",
        )

    saved_job = _load_admin_job(db, job_id)

    if saved_job is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="The job was created but could not be retrieved.",
        )

    return _admin_job_response(saved_job)


# =========================================================
# UPDATE JOB
# =========================================================

@router.patch(
    "/jobs/{job_id}",
    response_model=AdminJobResponse,
)
def update_admin_job(
    job_id: int,
    job_data: AdminJobUpdate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_admin),
):
    """
    Update job information and required skills.
    """

    job = _load_admin_job(db, job_id)

    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found.",
        )

    updates = job_data.model_dump(
        exclude_unset=True
    )

    if not updates:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Provide at least one field to update.",
        )

    # -----------------------------------------------------
    # Handle required skills separately.
    # -----------------------------------------------------

    required_skill_ids = updates.pop(
        "required_skill_ids",
        None,
    )

    # -----------------------------------------------------
    # Validate company.
    # -----------------------------------------------------

    if "company_id" in updates:

        if updates["company_id"] is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Company ID cannot be null.",
            )

        _validate_active_company(
            db,
            updates["company_id"],
        )

    # -----------------------------------------------------
    # Validate job title.
    # -----------------------------------------------------

    if "title" in updates:

        if (
            updates["title"] is None
            or not updates["title"].strip()
        ):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Job title cannot be empty.",
            )

        updates["title"] = updates["title"].strip()

    # -----------------------------------------------------
    # Validate currency.
    # -----------------------------------------------------

    if "currency" in updates:

        if updates["currency"] is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Currency cannot be null.",
            )

        updates["currency"] = (
            updates["currency"].strip().upper()
        )

        if not updates["currency"]:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Currency cannot be empty.",
            )

    # -----------------------------------------------------
    # Validate salary range.
    # -----------------------------------------------------

    new_salary_min = updates.get(
        "salary_min",
        job.salary_min,
    )

    new_salary_max = updates.get(
        "salary_max",
        job.salary_max,
    )

    _validate_salary_range(
        new_salary_min,
        new_salary_max,
    )

    # -----------------------------------------------------
    # Validate required skills if supplied.
    # -----------------------------------------------------

    skills_were_supplied = (
        "required_skill_ids" in job_data.model_fields_set
    )

    if (
        skills_were_supplied
        and required_skill_ids is not None
    ):
        _validate_active_skill_ids(
            db,
            required_skill_ids,
        )

    # -----------------------------------------------------
    # Update ordinary job fields.
    # -----------------------------------------------------

    allowed_fields = {
        "company_id",
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
        "status",
    }

    for field, value in updates.items():

        if field in allowed_fields:
            setattr(job, field, value)

    # -----------------------------------------------------
    # Update required skills.
    # -----------------------------------------------------

    if (
        skills_were_supplied
        and required_skill_ids is not None
    ):
        selected_ids = set(required_skill_ids)

        existing_links = {
            link.skill_id: link
            for link in job.job_skills
        }

        # Activate selected skills and deactivate removed ones.
        for skill_id, link in existing_links.items():

            link.status = (
                "ACTIVE"
                if skill_id in selected_ids
                else "INACTIVE"
            )

            link.updated_by_id = current_admin.id

        # Add newly selected skills.
        for skill_id in selected_ids:

            if skill_id not in existing_links:

                db.add(
                    JobSkill(
                        job_id=job.id,
                        skill_id=skill_id,
                        is_required=True,
                        status="ACTIVE",
                        created_by_id=current_admin.id,
                        updated_by_id=current_admin.id,
                    )
                )

    # -----------------------------------------------------
    # Update audit information.
    # -----------------------------------------------------

    job.updated_by_id = current_admin.id

    job_id = job.id

    try:
        db.commit()

    except IntegrityError:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unable to update job. Check the company and required skills.",
        )

    except SQLAlchemyError:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="A database error occurred while updating the job.",
        )

    saved_job = _load_admin_job(db, job_id)

    if saved_job is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="The updated job could not be retrieved.",
        )

    return _admin_job_response(saved_job)
