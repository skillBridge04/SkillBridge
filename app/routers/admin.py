from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import require_admin
from app.core.security import hash_password

from app.models.user import User
from app.models.skill import Skill
from app.models.course import Course

from app.schemas.auth import UserResponse
from app.schemas.admin import (
    AdminCreate,
    SkillCreate,
    SkillUpdate,
    SkillAdminResponse,
    CourseCreate,
    CourseUpdate,
    CourseAdminResponse,
)

from datetime import datetime, timezone

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from app.models.company import Company
from app.models.job import Job
from app.models.job_skill import JobSkill

from app.schemas.company import CompanyCreate
from app.schemas.admin import (
    CompanyAdminResponse,
    CompanyAdminUpdate,
    AdminJobCreate,
    AdminJobUpdate,
    AdminJobResponse,
)

router = APIRouter(
    prefix="/api/admin",
    tags=["Admin"],
)


# =========================================================
# VIEW PENDING EMPLOYERS
# =========================================================

@router.get(
    "/employers/pending",
    response_model=list[UserResponse],
)
def get_pending_employers(
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_admin),
):
    """
    Get all employers waiting for admin approval.
    """

    pending_employers = db.scalars(
        select(User)
        .where(
            User.role == "EMPLOYER",
            User.account_status == "PENDING",
        )
        .order_by(User.id)
    ).all()

    return pending_employers


# =========================================================
# APPROVE EMPLOYER
# =========================================================

@router.patch(
    "/employers/{user_id}/approve",
    response_model=UserResponse,
)
def approve_employer(
    user_id: int,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_admin),
):
    """
    Approve a pending employer.
    """

    employer = db.get(User, user_id)

    if employer is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )

    if employer.role != "EMPLOYER":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This user is not an employer.",
        )

    if employer.account_status != "PENDING":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This employer is not pending approval.",
        )

    employer.account_status = "ACTIVE"

    db.commit()
    db.refresh(employer)

    return employer


# =========================================================
# REJECT EMPLOYER
# =========================================================

@router.patch(
    "/employers/{user_id}/reject",
    response_model=UserResponse,
)
def reject_employer(
    user_id: int,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_admin),
):
    """
    Reject a pending employer.
    """

    employer = db.get(User, user_id)

    if employer is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )

    if employer.role != "EMPLOYER":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This user is not an employer.",
        )

    if employer.account_status != "PENDING":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This employer is not pending approval.",
        )

    employer.account_status = "REJECTED"

    db.commit()
    db.refresh(employer)

    return employer


# =========================================================
# CREATE ANOTHER ADMIN
# =========================================================

@router.post(
    "/admins",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_admin(
    admin_data: AdminCreate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_admin),
):
    """
    Create another admin account.
    Only an existing admin can create an admin.
    """

    existing_user = db.scalar(
        select(User).where(
            func.lower(User.email) ==
            admin_data.email.lower()
        )
    )

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered.",
        )

    new_admin = User(
        name=admin_data.name.strip(),
        email=admin_data.email,
        password_hash=hash_password(admin_data.password),
        role="ADMIN",
        account_status="ACTIVE",
    )

    db.add(new_admin)
    db.commit()
    db.refresh(new_admin)

    return new_admin


# =========================================================
# LIST ADMINS
# =========================================================

@router.get(
    "/admins",
    response_model=list[UserResponse],
)
def get_admins(
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_admin),
):
    """
    Get all admin accounts.
    """

    admins = db.scalars(
        select(User)
        .where(User.role == "ADMIN")
        .order_by(User.id)
    ).all()

    return admins


# =========================================================
# DEACTIVATE ADMIN
# =========================================================

@router.patch(
    "/admins/{user_id}/deactivate",
    response_model=UserResponse,
)
def deactivate_admin(
    user_id: int,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_admin),
):
    """
    Deactivate another admin account.
    """

    admin = db.get(User, user_id)

    if admin is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )

    if admin.role != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This user is not an admin.",
        )

    if admin.id == current_admin.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot deactivate your own admin account.",
        )

    admin.account_status = "INACTIVE"

    db.commit()
    db.refresh(admin)

    return admin
# =========================================================
# ACTIVATE ADMIN
# =========================================================

@router.patch(
    "/admins/{user_id}/activate",
    response_model=UserResponse,
)
def activate_admin(
    user_id: int,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_admin),
):
    """
    Activate an admin account.
    """

    admin = db.get(User, user_id)

    if admin is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )

    if admin.role != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This user is not an admin.",
        )

    admin.account_status = "ACTIVE"

    db.commit()
    db.refresh(admin)

    return admin
