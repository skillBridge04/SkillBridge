from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.job import Job
from app.models.job_skill import JobSkill
from app.models.resume_skill import ResumeSkill


def match_jobs_for_resume(
    db: Session,
    resume_id: int,
) -> list[dict]:
    """
    Compare the skills detected in a resume with
    the skills required by active jobs.
    """

    # Step 1: Get skills detected in the resume.
    resume_skill_ids = set(
        db.scalars(
            select(ResumeSkill.skill_id).where(
                ResumeSkill.resume_id == resume_id
            )
        ).all()
    )

    if not resume_skill_ids:
        return []

    # Step 2: Load active jobs, their companies and skills.
    statement = (
        select(Job)
        .where(Job.status == "ACTIVE")
        .options(
            selectinload(Job.company),
            selectinload(Job.job_skills).selectinload(
                JobSkill.skill
            ),
        )
    )

    jobs = db.scalars(statement).all()

    recommendations = []

    for job in jobs:

        # Ignore jobs without an active company.
        if (
            job.company is None
            or job.company.status != "ACTIVE"
        ):
            continue

        # Consider only active job-skill records.
        job_skills = [
            item
            for item in job.job_skills
            if item.status == "ACTIVE" and item.skill is not None
        ]

        # A job without skill requirements cannot be scored.
        if not job_skills:
            continue

        # Required skills determine the match percentage.
        required_skills = [
            item for item in job_skills if item.is_required
        ]

        # If no skills are marked required, score against
        # all available skills for that job.
        scoring_skills = required_skills or job_skills

        matched_required = [
            item
            for item in scoring_skills
            if item.skill_id in resume_skill_ids
        ]

        missing_required = [
            item
            for item in scoring_skills
            if item.skill_id not in resume_skill_ids
        ]

        match_percentage = round(
            len(matched_required) / len(scoring_skills) * 100,
            2,
        )

        # Include all matched skills in the response.
        matched_skills = [
            {
                "skill_id": item.skill_id,
                "skill_name": item.skill.name,
                "is_required": item.is_required,
            }
            for item in job_skills
            if item.skill_id in resume_skill_ids
        ]

        # Missing required skills become potential skill gaps.
        missing_skills = [
            {
                "skill_id": item.skill_id,
                "skill_name": item.skill.name,
                "is_required": item.is_required,
            }
            for item in missing_required
        ]

        recommendations.append(
            {
                "job_id": job.id,
                "job_title": job.title,
                "company": {
                    "id": job.company.id,
                    "name": job.company.name,
                    "industry": job.company.industry,
                    "location": job.company.location,
                    "website": job.company.website,
                },
                "location": job.location,
                "employment_type": job.employment_type,
                "salary_min": job.salary_min,
                "salary_max": job.salary_max,
                "currency": job.currency,
                "experience_required": job.experience_required,
                "education_required": job.education_required,
                "application_url": job.application_url,
                "match_percentage": match_percentage,
                "matched_required_skill_count": len(
                    matched_required
                ),
                "required_skill_count": len(scoring_skills),
                "matched_skills": matched_skills,
                "missing_skills": missing_skills,
            }
        )

    # Highest matching percentages appear first.
    recommendations.sort(
        key=lambda item: (
            item["match_percentage"],
            item["matched_required_skill_count"],
        ),
        reverse=True,
    )

    return recommendations