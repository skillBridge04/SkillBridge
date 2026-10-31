from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.resume import Resume
from app.models.resume_skill import ResumeSkill
from app.models.user import User
from app.services.job_matcher import match_jobs_for_resume


router = APIRouter(
    prefix="/api/matching",
    tags=["Job Matching"],
)


@router.get("/resume/{resume_id}/jobs")
def get_job_matches(
    resume_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Only job seekers can use their resume for matching.
    if current_user.role != "JOB_SEEKER":
        raise HTTPException(
            status_code=403,
            detail="Only job seekers can access job matching",
        )

    # Verify that this resume belongs to the logged-in user.
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

    # Verify that skills have already been extracted.
    has_skills = db.scalar(
        select(ResumeSkill.id)
        .where(ResumeSkill.resume_id == resume.id)
        .limit(1)
    )

    if has_skills is None:
        raise HTTPException(
            status_code=400,
            detail="No extracted skills found. Extract resume skills first.",
        )

    matches = match_jobs_for_resume(
        db=db,
        resume_id=resume.id,
    )

    return {
        "resume_id": resume.id,
        "total_jobs_matched_or_scored": len(matches),
        "recommendations": matches,
    }

@router.get("/resume/{resume_id}/jobs/{job_id}/skill-gaps")
def get_job_skill_gaps(
    resume_id: int,
    job_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Only job seekers can access their skill-gap report.
    if current_user.role != "JOB_SEEKER":
        raise HTTPException(
            status_code=403,
            detail="Only job seekers can access skill-gap analysis",
        )

    # Confirm that the resume belongs to the logged-in user.
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

    # Reuse the existing job-matching service.
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
                "No matching report is available for this job. "
                "Check that the job is active and has active skill requirements."
            ),
        )

    matched_skills = job_match["matched_skills"]

    matched_required_skills = [
        skill
        for skill in matched_skills
        if skill["is_required"]
    ]

    matched_optional_skills = [
        skill
        for skill in matched_skills
        if not skill["is_required"]
    ]

    missing_required_skills = job_match["missing_skills"]

    return {
        "resume_id": resume.id,
        "job_id": job_match["job_id"],
        "job_title": job_match["job_title"],
        "company": job_match["company"]["name"],
        "match_percentage": job_match["match_percentage"],
        "required_skill_count": job_match["required_skill_count"],
        "matched_required_skills": matched_required_skills,
        "matched_optional_skills": matched_optional_skills,
        "missing_required_skills": missing_required_skills,
        "skill_gap_count": len(missing_required_skills),
    }