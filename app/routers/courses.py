from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.resume import Resume
from app.models.resume_skill import ResumeSkill
from app.models.user import User
from app.schemas.course import CourseRecommendationsResponse
from app.services.course_recommender import (
    recommend_courses_for_missing_skills,
)
from app.services.job_matcher import match_jobs_for_resume


router = APIRouter(
    prefix="/api/courses",
    tags=["Course Recommendations"],
)


@router.get(
    "/recommendations/resume/{resume_id}/job/{job_id}",
    response_model=CourseRecommendationsResponse,
)
def get_course_recommendations(
    resume_id: int,
    job_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Only job seekers can request personal recommendations.
    if current_user.role != "JOB_SEEKER":
        raise HTTPException(
            status_code=403,
            detail=(
                "Only job seekers can access course recommendations"
            ),
        )

    # Check that this resume belongs to the logged-in user.
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

    # Check whether skills have already been extracted.
    has_skills = db.scalar(
        select(ResumeSkill.id)
        .where(ResumeSkill.resume_id == resume.id)
        .limit(1)
    )

    if has_skills is None:
        raise HTTPException(
            status_code=400,
            detail=(
                "No extracted skills found. "
                "Extract resume skills first."
            ),
        )

    # Reuse Part 7: find matching jobs and skill gaps.
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
                "No matching report was found for this job. "
                "Check that the job is active and has active "
                "skill requirements."
            ),
        )

    # Get courses for missing required skills.
    missing_skills = job_match["missing_skills"]

    recommendations = recommend_courses_for_missing_skills(
        db=db,
        missing_skills=missing_skills,
    )

    # Count all recommended courses.
    total_courses = sum(
        len(item["courses"])
        for item in recommendations
    )

    return {
        "resume_id": resume.id,
        "job_id": job_match["job_id"],
        "job_title": job_match["job_title"],
        "company": job_match["company"]["name"],
        "match_percentage": job_match["match_percentage"],
        "missing_skill_count": len(missing_skills),
        "total_courses": total_courses,
        "recommendations": recommendations,
    }