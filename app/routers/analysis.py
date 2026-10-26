from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.core.database import get_db
from app.core.dependencies import get_current_user

from app.models.resume import Resume
from app.models.resume_skill import ResumeSkill
from app.models.user import User

from app.services.job_matcher import match_jobs_for_resume
from app.services.course_recommender import (
    recommend_courses_for_missing_skills,
)


router = APIRouter(
    prefix="/api/analysis",
    tags=["Complete Analysis"],
)


@router.get("/resume/{resume_id}/job/{job_id}")
def get_complete_analysis(
    resume_id: int,
    job_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Step 1: Only job seekers can access personal analysis.
    if current_user.role != "JOB_SEEKER":
        raise HTTPException(
            status_code=403,
            detail="Only job seekers can access this analysis",
        )

    # Step 2: Confirm that the resume belongs to the user.
    resume = db.scalar(
        select(Resume).where(
            Resume.id == resume_id,
            Resume.user_id == current_user.id,
        )
    )

    if not resume:
        raise HTTPException(
            status_code=404,
            detail="Resume not found",
        )

    # Step 3: Load the skills previously extracted for this resume.
    resume_skills = db.scalars(
        select(ResumeSkill)
        .options(joinedload(ResumeSkill.skill))
        .where(ResumeSkill.resume_id == resume.id)
        .order_by(ResumeSkill.id)
    ).all()

    if not resume_skills:
        raise HTTPException(
            status_code=400,
            detail=(
                "No extracted skills found. "
                "Extract resume skills before requesting analysis."
            ),
        )

    extracted_skills = [
        {
            "skill_id": item.skill_id,
            "skill_name": item.skill.name,
            "source": item.source,
            "confidence": item.confidence,
        }
        for item in resume_skills
        if item.skill is not None
    ]

    # Step 4: Calculate job matches using the existing service.
    matches = match_jobs_for_resume(
        db=db,
        resume_id=resume.id,
    )

    job_match = next(
        (
            item
            for item in matches
            if item["job_id"] == job_id
        ),
        None,
    )

    if job_match is None:
        raise HTTPException(
            status_code=404,
            detail=(
                "No analysis is available for this job. "
                "Check that the job and its company are active "
                "and that the job has active skill requirements."
            ),
        )

    # Step 5: Recommend courses for missing required skills.
    missing_skills = job_match["missing_skills"]

    course_recommendations = (
        recommend_courses_for_missing_skills(
            db=db,
            missing_skills=missing_skills,
        )
    )

    total_courses = sum(
        len(item["courses"])
        for item in course_recommendations
    )

    # Step 6: Return the integrated report.
    return {
        "resume_id": resume.id,
        "resume_file_name": resume.file_name,
        "extracted_skills": extracted_skills,
        "job_match": job_match,
        "course_recommendations": {
            "missing_skill_count": len(missing_skills),
            "total_courses": total_courses,
            "recommendations": course_recommendations,
        },
    }