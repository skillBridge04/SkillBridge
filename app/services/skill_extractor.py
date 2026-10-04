import re
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.skill import Skill
from app.models.resume import Resume
from app.models.resume_skill import ResumeSkill


def normalize_text(text: str) -> str:
    """
    Convert resume text into a simpler format for skill matching.
    """

    text = text.lower()

    # Replace multiple spaces/newlines with one space
    text = re.sub(r"\s+", " ", text)

    return text.strip()


def skill_exists_in_text(text: str, skill_name: str) -> bool:
    """
    Check whether a skill exists in the resume text.

    Word-boundary matching helps reduce false matches.
    """

    skill_name = skill_name.lower().strip()

    # Escape special regex characters such as + in C++
    escaped_skill = re.escape(skill_name)

    # Search for the skill as a separate word/phrase
    pattern = rf"(?<!\w){escaped_skill}(?!\w)"

    return re.search(pattern, text) is not None


def extract_skills_from_resume(
    db: Session,
    resume: Resume,
) -> list[ResumeSkill]:
    """
    Extract skills from a resume and save them into resume_skills.
    """

    if not resume.extracted_text:
        return []

    normalized_text = normalize_text(resume.extracted_text)

    # Get all active skills from the database
    skills = db.scalars(
        select(Skill).where(Skill.status == "ACTIVE")
    ).all()

    detected_resume_skills = []

    for skill in skills:

        if skill_exists_in_text(normalized_text, skill.name):

            # Check whether this skill is already attached
            existing = db.scalar(
                select(ResumeSkill).where(
                    ResumeSkill.resume_id == resume.id,
                    ResumeSkill.skill_id == skill.id,
                )
            )

            if existing:
                detected_resume_skills.append(existing)
                continue

            resume_skill = ResumeSkill(
                resume_id=resume.id,
                skill_id=skill.id,
                source="keyword",
                confidence=Decimal("1.0000"),
            )

            db.add(resume_skill)

            detected_resume_skills.append(resume_skill)

    db.commit()

    # Refresh newly created records
    for resume_skill in detected_resume_skills:
        db.refresh(resume_skill)

    return detected_resume_skills