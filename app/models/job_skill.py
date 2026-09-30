from sqlalchemy import Boolean, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.mixins import AuditMixin


class JobSkill(AuditMixin, Base):
    __tablename__ = "job_skills"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    job_id: Mapped[int] = mapped_column(
        ForeignKey("jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    skill_id: Mapped[int] = mapped_column(
        ForeignKey("skills.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    is_required: Mapped[bool] = mapped_column(
        default=True,
        nullable=False,
    )

    job: Mapped["Job"] = relationship(
        back_populates="job_skills",
    )

    skill: Mapped["Skill"] = relationship(
        back_populates="job_skills",
    )

    __table_args__ = (
        UniqueConstraint(
            "job_id",
            "skill_id",
            name="uq_job_skill",
        ),
    )