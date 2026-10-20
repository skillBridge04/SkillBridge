from pydantic import BaseModel


class CourseRecommendationItem(BaseModel):
    id: int
    title: str
    provider: str
    skill_id: int
    skill_name: str
    level: str | None
    duration: str | None
    url: str
    is_free: bool
    description: str | None


class SkillCourseRecommendation(BaseModel):
    skill_id: int
    skill_name: str
    courses: list[CourseRecommendationItem]


class CourseRecommendationsResponse(BaseModel):
    resume_id: int
    job_id: int
    job_title: str
    company: str
    match_percentage: float
    missing_skill_count: int
    total_courses: int
    recommendations: list[SkillCourseRecommendation]