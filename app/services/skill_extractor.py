import re
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models.skill import Skill
from app.models.resume import Resume
from app.models.resume_skill import ResumeSkill
from app.services.ai_skill_extractor import extract_skills_with_ai


def normalize_text(text: str) -> str:
    """Normalize resume text for keyword matching."""

    text = text.lower()
    text = re.sub(r"\s+", " ", text)

    return text.strip()


def skill_exists_in_text(text: str, skill_name: str) -> bool:
    """Check whether a skill appears as a separate word or phrase."""

    skill_name = skill_name.lower().strip()
    escaped_skill = re.escape(skill_name)

    pattern = rf"(?<!\w){escaped_skill}(?!\w)"

    return re.search(pattern, text) is not None


def extract_skills_from_resume(
    db: Session,
    resume: Resume,
) -> list[ResumeSkill]:
    """
    Extract skills using AI and keyword matching.

    AI results take priority when both methods find the same skill.
    Keyword matching remains the fallback.
    """

    if not resume.extracted_text:
        return []

    normalized_text = normalize_text(resume.extracted_text)

    # Step 1: Load active database skills.
    skills = db.scalars(
        select(Skill).where(Skill.status == "ACTIVE")
    ).all()

    if not skills:
        return []

    # Store detected skills as:
    # skill_id -> (source, confidence)
    detected: dict[int, tuple[str, Decimal]] = {}

    # Step 2: Detect exact keyword matches.
    for skill in skills:
        if skill_exists_in_text(normalized_text, skill.name):
            detected[skill.id] = (
                "keyword",
                Decimal("1.0000"),
            )

    # Step 3: Ask AI to detect skill variations.
    ai_results = extract_skills_with_ai(
        resume_text=resume.extracted_text,
        available_skill_names=[
            skill.name for skill in skills
        ],
    )

    skill_by_name = {
        skill.name.casefold(): skill
        for skill in skills
    }

    # AI results take priority for the same skill.
    for skill_name, confidence in ai_results.items():
        skill = skill_by_name.get(skill_name.casefold())

        if skill:
            detected[skill.id] = ("ai", confidence)

    if not detected:
        return []

    detected_skill_ids = list(detected.keys())

    # Step 4: Find existing records to prevent duplicates.
    existing_records = db.scalars(
        select(ResumeSkill).where(
            ResumeSkill.resume_id == resume.id,
            ResumeSkill.skill_id.in_(detected_skill_ids),
        )
    ).all()

    existing_by_skill_id = {
        record.skill_id: record
        for record in existing_records
    }

    # Step 5: Create new records or update existing records.
    for skill_id, (source, confidence) in detected.items():

        existing = existing_by_skill_id.get(skill_id)

        if existing:
            existing.source = source
            existing.confidence = confidence

        else:
            resume_skill = ResumeSkill(
                resume_id=resume.id,
                skill_id=skill_id,
                source=source,
                confidence=confidence,
            )

            db.add(resume_skill)

    # Step 6: Save changes.
    db.commit()

    # Step 7: Reload saved records with their skill names.
    result = db.scalars(
        select(ResumeSkill)
        .options(joinedload(ResumeSkill.skill))
        .where(
            ResumeSkill.resume_id == resume.id,
            ResumeSkill.skill_id.in_(detected_skill_ids),
        )
        .order_by(ResumeSkill.id)
    ).all()

    return result