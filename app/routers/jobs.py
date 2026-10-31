from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user

from app.models.user import User
from app.models.resume import Resume
from app.models.resume_skill import ResumeSkill
from app.models.skill import Skill
from app.models.company import Company
from app.models.job import Job
from app.models.job_skill import JobSkill


# =========================================
# ROUTER CONFIGURATION
# =========================================

router = APIRouter(
    prefix="/api/jobs",
    tags=["Job Recommendations"],
)


# =========================================
# HELPER: READ A MODEL FIELD
# =========================================

def get_field(obj, *field_names, default=None):
    """
    Return the first available, non-None field value.

    This helper allows the code to safely read optional
    fields without raising an AttributeError.
    """

    if obj is None:
        return default

    for field_name in field_names:
        value = getattr(obj, field_name, None)

        if value is not None:
            return value

    return default


# =========================================
# HELPER: NORMALIZE A VALUE
# =========================================

def normalize_value(value):
    """
    Convert a value, including an Enum value, into
    a normalized lowercase string.
    """

    if value is None:
        return ""

    # Support Enum values if a model uses an Enum.
    if hasattr(value, "value"):
        value = value.value

    return str(value).strip().lower()


# =========================================
# HELPER: CHECK WHETHER A RECORD IS ACTIVE
# =========================================

def is_record_active(
    record,
    unavailable_statuses=None,
):
    """
    Check whether a job, company, skill, or relationship
    record is available.

    Records with explicit inactive/unavailable values
    are excluded. Records without a status field are
    not automatically excluded.
    """

    if record is None:
        return False

    if unavailable_statuses is None:
        unavailable_statuses = {
            "inactive",
            "closed",
            "deleted",
            "draft",
            "cancelled",
            "canceled",
            "disabled",
        }

    # Check boolean-style fields, if available.
    active_value = get_field(
        record,
        "is_active",
        "active",
    )

    if active_value is not None:
        normalized_active = normalize_value(active_value)

        if normalized_active in {
            "false",
            "0",
            "no",
            "inactive",
            "disabled",
        }:
            return False

    # Check the record's status field.
    record_status = get_field(
        record,
        "status",
        "job_status",
        "company_status",
    )

    normalized_status = normalize_value(record_status)

    if normalized_status in unavailable_statuses:
        return False

    return True


# =========================================
# HELPER: CHECK WHETHER A JOB SKILL IS REQUIRED
# =========================================

def is_required_skill(link):
    """
    Return True when a job-skill relationship represents
    a required skill.

    Optional skills are not included in the match-score
    denominator or missing-required-skills list.
    """

    value = get_field(
        link,
        "is_required",
        default=True,
    )

    normalized_value = normalize_value(value)

    if normalized_value in {
        "false",
        "0",
        "no",
        "optional",
    }:
        return False

    return True


# =========================================
# HELPER: CHECK USER ROLE
# =========================================

def get_normalized_role(user):
    """
    Return the user's role in a consistent format.
    """

    role = get_field(
        user,
        "role",
        default="",
    )

    if hasattr(role, "value"):
        role = role.value

    return (
        str(role)
        .strip()
        .upper()
        .replace(" ", "_")
        .replace("-", "_")
    )


# =========================================
# GET RECOMMENDED JOBS
# =========================================

@router.get("/recommended")
def get_recommended_jobs(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Recommend jobs using skills extracted from the
    authenticated job seeker's latest uploaded resume.

    Match percentage:
        Matched required skills / Total required skills * 100

    A job is recommended only when at least one required
    skill matches the user's resume.

    Inactive jobs and inactive companies are excluded.
    Optional job skills are excluded from the match score.
    """

    # -----------------------------------------
    # 1. Verify the user's role
    # -----------------------------------------

    if get_normalized_role(current_user) != "JOB_SEEKER":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "Only job seekers can access personalized "
                "job recommendations."
            ),
        )

    # -----------------------------------------
    # 2. Find the latest resume belonging to this user
    # -----------------------------------------

    resume = db.scalar(
        select(Resume)
        .where(
            Resume.user_id == current_user.id
        )
        .order_by(
            Resume.id.desc()
        )
        .limit(1)
    )

    if resume is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                "No uploaded resume was found. "
                "Upload a resume first."
            ),
        )

    # -----------------------------------------
    # 3. Load skills extracted from the latest resume
    # -----------------------------------------

    resume_skill_rows = db.scalars(
        select(ResumeSkill)
        .where(
            ResumeSkill.resume_id == resume.id
        )
    ).all()

    resume_skill_ids = {
        row.skill_id
        for row in resume_skill_rows
        if get_field(row, "skill_id") is not None
    }

    if not resume_skill_ids:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "No extracted skills were found for this resume. "
                "Please analyze your resume before requesting "
                "job recommendations."
            ),
        )

    # -----------------------------------------
    # 4. Load jobs and job-skill relationships
    # -----------------------------------------

    jobs = db.scalars(
        select(Job)
    ).all()

    job_skill_rows = db.scalars(
        select(JobSkill)
    ).all()

    # Remove inactive job-skill relationships.
    job_skill_rows = [
        row
        for row in job_skill_rows
        if is_record_active(row)
    ]

    # -----------------------------------------
    # 5. Collect skill IDs used by the resume and jobs
    # -----------------------------------------

    job_skill_ids = {
        row.skill_id
        for row in job_skill_rows
        if get_field(row, "skill_id") is not None
    }

    all_skill_ids = resume_skill_ids | job_skill_ids

    # -----------------------------------------
    # 6. Load skill records
    # -----------------------------------------

    skill_name_by_id = {}

    if all_skill_ids:
        skill_records = db.scalars(
            select(Skill)
            .where(
                Skill.id.in_(all_skill_ids)
            )
        ).all()

        for skill in skill_records:

            # Ignore skills that have been deactivated.
            if not is_record_active(skill):
                continue

            skill_id = get_field(
                skill,
                "id",
            )

            skill_name = get_field(
                skill,
                "name",
            )

            if skill_id is None or skill_name is None:
                continue

            skill_name_by_id[skill_id] = str(skill_name)

    # Keep only active skills for matching.
    active_skill_ids = set(skill_name_by_id.keys())

    resume_skill_ids = (
        resume_skill_ids & active_skill_ids
    )

    if not resume_skill_ids:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "No active extracted skills were found "
                "for this resume. Please analyze your "
                "resume again."
            ),
        )

    # -----------------------------------------
    # 7. Group required skill IDs by job
    # -----------------------------------------

    required_skills_by_job = {}

    for link in job_skill_rows:

        # Ignore optional job skills when scoring.
        if not is_required_skill(link):
            continue

        job_id = get_field(
            link,
            "job_id",
        )

        skill_id = get_field(
            link,
            "skill_id",
        )

        if job_id is None or skill_id is None:
            continue

        # Ignore skills that are inactive or unavailable.
        if skill_id not in active_skill_ids:
            continue

        required_skills_by_job.setdefault(
            job_id,
            set(),
        ).add(skill_id)

    # -----------------------------------------
    # 8. Load company information
    # -----------------------------------------

    companies = db.scalars(
        select(Company)
    ).all()

    companies_by_id = {
        company.id: company
        for company in companies
        if get_field(company, "id") is not None
    }

    # -----------------------------------------
    # 9. Compare resume skills against each job
    # -----------------------------------------

    recommendations = []

    for job in jobs:

        # Exclude inactive, closed, deleted, or draft jobs.
        if not is_record_active(job):
            continue

        job_id = get_field(
            job,
            "id",
        )

        if job_id is None:
            continue

        # Get the job's required skills.
        required_skill_ids = required_skills_by_job.get(
            job_id,
            set(),
        )

        # A job without required skills cannot be scored.
        if not required_skill_ids:
            continue

        # -------------------------------------
        # 10. Find the associated company
        # -------------------------------------

        company = get_field(
            job,
            "company",
        )

        if company is None:
            company_id = get_field(
                job,
                "company_id",
            )

            if company_id is not None:
                company = companies_by_id.get(company_id)

        # Exclude jobs belonging to inactive companies.
        if company is not None and not is_record_active(company):
            continue

        # -------------------------------------
        # 11. Calculate matched and missing skills
        # -------------------------------------

        matched_skill_ids = (
            resume_skill_ids & required_skill_ids
        )

        missing_skill_ids = (
            required_skill_ids - resume_skill_ids
        )

        # Recommend only jobs with at least one matching
        # required skill.
        if not matched_skill_ids:
            continue

        # -------------------------------------
        # 12. Calculate match percentage
        # -------------------------------------

        match_score = round(
            (
                len(matched_skill_ids)
                / len(required_skill_ids)
            ) * 100
        )

        # -------------------------------------
        # 13. Convert skill IDs into skill names
        # -------------------------------------

        matched_skills = sorted(
            skill_name_by_id[skill_id]
            for skill_id in matched_skill_ids
            if skill_id in skill_name_by_id
        )

        missing_skills = sorted(
            skill_name_by_id[skill_id]
            for skill_id in missing_skill_ids
            if skill_id in skill_name_by_id
        )

        required_skills = sorted(
            skill_name_by_id[skill_id]
            for skill_id in required_skill_ids
            if skill_id in skill_name_by_id
        )

        # -------------------------------------
        # 14. Read company information
        # -------------------------------------

        company_name = get_field(
            company,
            "name",
            "company_name",
            "title",
            default="Company not specified",
        )

        company_id = get_field(
            company,
            "id",
            default=get_field(job, "company_id"),
        )

        company_website = get_field(
            company,
            "website",
            "website_url",
            default=None,
        )

        # -------------------------------------
        # 15. Read job information
        # -------------------------------------

        job_title = get_field(
            job,
            "title",
            "job_title",
            "name",
            default="Untitled job",
        )

        description = get_field(
            job,
            "description",
            "job_description",
            default="",
        )

        location = get_field(
            job,
            "location",
            "job_location",
            default=None,
        )

        employment_type = get_field(
            job,
            "employment_type",
            "job_type",
            "type",
            default=None,
        )

        salary_min = get_field(
            job,
            "salary_min",
            "min_salary",
            default=None,
        )

        salary_max = get_field(
            job,
            "salary_max",
            "max_salary",
            default=None,
        )

        currency = get_field(
            job,
            "currency",
            "salary_currency",
            default="BDT",
        )

        experience_required = get_field(
            job,
            "experience_required",
            default=None,
        )

        education_required = get_field(
            job,
            "education_required",
            default=None,
        )

        application_url = get_field(
            job,
            "application_url",
            default=None,
        )

        deadline = get_field(
            job,
            "deadline",
            default=None,
        )

        # -------------------------------------
        # 16. Prepare the recommendation record
        # -------------------------------------

        recommendations.append({
            # Job and company details
            "job_id": job_id,
            "company_id": company_id,
            "title": str(job_title),
            "company_name": str(company_name),
            "company_website": company_website,

            # Job information
            "description": str(description or ""),
            "location": location,
            "employment_type": employment_type,
            "salary_min": salary_min,
            "salary_max": salary_max,
            "currency": currency,
            "experience_required": experience_required,
            "education_required": education_required,
            "application_url": application_url,
            "deadline": deadline,

            # Matching information
            "match_score": match_score,
            "required_skills": required_skills,
            "matched_skills": matched_skills,
            "missing_skills": missing_skills,
            "matched_skills_count": len(matched_skill_ids),
            "required_skills_count": len(required_skill_ids),
        })

    # -----------------------------------------
    # 17. Rank the best matches first
    # -----------------------------------------

    recommendations.sort(
        key=lambda item: (
            item["match_score"],
            item["matched_skills_count"],
        ),
        reverse=True,
    )

    # -----------------------------------------
    # 18. Return recommendations to the frontend
    # -----------------------------------------

    return {
        "resume_id": resume.id,
        "resume_skills_count": len(resume_skill_ids),
        "total_matches": len(recommendations),
        "jobs": recommendations,
    }