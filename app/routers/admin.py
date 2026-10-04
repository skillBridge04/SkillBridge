from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import require_admin
from app.models.user import User
from app.schemas.auth import UserResponse

from app.core.security import hash_password
from app.schemas.admin import AdminCreate


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
    Get all employers waiting for Admin approval.
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
    Approve a pending Employer.
    """

    employer = db.get(User, user_id)

    # User doesn't exist
    if employer is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Make sure this user is an Employer
    if employer.role != "EMPLOYER":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This user is not an Employer",
        )

    # Make sure employer is pending
    if employer.account_status != "PENDING":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This Employer is not pending approval",
        )

    # Approve employer
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
    Reject a pending Employer.
    """

    employer = db.get(User, user_id)

    # User doesn't exist
    if employer is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Make sure this user is an Employer
    if employer.role != "EMPLOYER":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This user is not an Employer",
        )

    # Make sure employer is pending
    if employer.account_status != "PENDING":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This Employer is not pending approval",
        )

    # Reject employer
    employer.account_status = "REJECTED"

    db.commit()
    db.refresh(employer)

    return employer

# =========================================================# =========================================================
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
    Create a new Admin account.

    Only an existing Admin can create another Admin.
    """

    # Check if email already exists
    existing_user = db.scalar(
        select(User).where(
            User.email == admin_data.email
        )
    )

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    # Hash password
    hashed_password = hash_password(
        admin_data.password
    )

    # Create Admin
    new_admin = User(
        name=admin_data.name,
        email=admin_data.email,
        password_hash=hashed_password,
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
    Get all Admin accounts.
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
    Deactivate an Admin account.
    """

    admin = db.get(User, user_id)

    if admin is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    if admin.role != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This user is not an Admin",
        )

    # Prevent Admin from deactivating themselves
    if admin.id == current_admin.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot deactivate your own Admin account",
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
    Activate an Admin account.
    """

    admin = db.get(User, user_id)

    if admin is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    if admin.role != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This user is not an Admin",
        )

    admin.account_status = "ACTIVE"

    db.commit()
    db.refresh(admin)

    return admin

