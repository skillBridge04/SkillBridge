from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.mixins import AuditMixin


class Skill(AuditMixin, Base):
    __tablename__ = "skills"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True,
    )

    name: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
        index=True,
    )

    category: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    resume_skills: Mapped[list["ResumeSkill"]] = relationship(
        back_populates="skill",
        cascade="all, delete-orphan",
    )

    job_skills: Mapped[list["JobSkill"]] = relationship(
        back_populates="skill",
        cascade="all, delete-orphan",
    )

    courses: Mapped[list["Course"]] = relationship(
        back_populates="skill",
        cascade="all, delete-orphan",
    )