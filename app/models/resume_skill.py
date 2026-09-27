from decimal import Decimal

from sqlalchemy import (
    ForeignKey,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.mixins import AuditMixin


class ResumeSkill(AuditMixin, Base):
    __tablename__ = "resume_skills"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    resume_id: Mapped[int] = mapped_column(
        ForeignKey("resumes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    skill_id: Mapped[int] = mapped_column(
        ForeignKey("skills.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    source: Mapped[str] = mapped_column(
        String(30),
        default="ai",
        nullable=False,
    )

    confidence: Mapped[Decimal | None] = mapped_column(
        Numeric(5, 4),
        nullable=True,
    )

    resume: Mapped["Resume"] = relationship(
        back_populates="resume_skills",
    )

    skill: Mapped["Skill"] = relationship(
        back_populates="resume_skills",
    )

    __table_args__ = (
        UniqueConstraint(
            "resume_id",
            "skill_id",
            name="uq_resume_skill",
        ),
    )