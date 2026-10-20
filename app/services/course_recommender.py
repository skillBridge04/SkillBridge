from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models.course import Course
from app.models.skill import Skill


def recommend_courses_for_missing_skills(
    db: Session,
    missing_skills: list[dict],
) -> list[dict]:
    """
    Find active courses for the missing required skills.

    Only courses linked to active skills are returned.
    """

    if not missing_skills:
        return []

    # Get unique skill IDs from the missing-skills list.
    skill_ids = list(
        dict.fromkeys(
            item["skill_id"]
            for item in missing_skills
        )
    )

    # Find active courses associated with those skills.
    statement = (
        select(Course)
        .join(Skill, Course.skill_id == Skill.id)
        .options(joinedload(Course.skill))
        .where(
            Course.status == "ACTIVE",
            Skill.status == "ACTIVE",
            Course.skill_id.in_(skill_ids),
        )
        .order_by(
            Course.is_free.desc(),
            Course.title.asc(),
        )
    )

    courses = db.scalars(statement).all()

    # Group courses by skill ID.
    courses_by_skill_id: dict[int, list[dict]] = {}

    for course in courses:

        course_data = {
            "id": course.id,
            "title": course.title,
            "provider": course.provider,
            "skill_id": course.skill_id,
            "skill_name": course.skill.name,
            "level": course.level,
            "duration": course.duration,
            "url": course.url,
            "is_free": course.is_free,
            "description": course.description,
        }

        courses_by_skill_id.setdefault(
            course.skill_id,
            [],
        ).append(course_data)

    # Return an entry for every missing skill.
    # A skill can have an empty courses list if no course exists.
    recommendations = []

    for missing_skill in missing_skills:

        skill_id = missing_skill["skill_id"]

        recommendations.append(
            {
                "skill_id": skill_id,
                "skill_name": missing_skill["skill_name"],
                "courses": courses_by_skill_id.get(
                    skill_id,
                    [],
                ),
            }
        )

    return recommendations