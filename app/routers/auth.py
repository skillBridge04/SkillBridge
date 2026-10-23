from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.security import (
    create_access_token,
    hash_password,
    verify_password,
)
from app.models.user import User
from app.schemas.auth import (
    EmployerRegister,
    TokenResponse,
    UserRegister,
    UserResponse,
)


router = APIRouter(
    prefix="/api/auth",
    tags=["Authentication"],
)


# =========================================================
# JOB SEEKER REGISTER
# =========================================================

@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
def register(
    user_data: UserRegister,
    db: Session = Depends(get_db),
):
    """
    Register a new Job Seeker.

    Job Seekers are automatically:
        role = JOB_SEEKER
        account_status = ACTIVE
    """

    # -----------------------------------------------------
    # Check if email already exists
    # -----------------------------------------------------

    existing_user = db.scalar(
        select(User).where(
            User.email == user_data.email
        )
    )

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    # -----------------------------------------------------
    # Hash password
    # -----------------------------------------------------

    hashed_password = hash_password(
        user_data.password
    )

    # -----------------------------------------------------
    # Create Job Seeker
    # -----------------------------------------------------

    user = User(
        name=user_data.name,
        email=user_data.email,
        password_hash=hashed_password,

        # Job Seeker defaults
        role="JOB_SEEKER",
        account_status="ACTIVE",
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return user


# =========================================================
# EMPLOYER REGISTER
# =========================================================

@router.post(
    "/register/employer",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
def register_employer(
    user_data: EmployerRegister,
    db: Session = Depends(get_db),
):
    """
    Register a new Employer / Recruiter.

    Employers are NOT activated immediately.

    Initial status:
        role = EMPLOYER
        account_status = PENDING

    An Admin must approve the employer before
    the employer can log in.
    """

    # -----------------------------------------------------
    # Check if email already exists
    # -----------------------------------------------------

    existing_user = db.scalar(
        select(User).where(
            User.email == user_data.email
        )
    )

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    # -----------------------------------------------------
    # Hash password
    # -----------------------------------------------------

    hashed_password = hash_password(
        user_data.password
    )

    # -----------------------------------------------------
    # Create Employer
    # -----------------------------------------------------

    user = User(
        name=user_data.name,
        email=user_data.email,
        password_hash=hashed_password,

        # Employer settings
        role="EMPLOYER",
        account_status="PENDING",
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return user


# =========================================================
# LOGIN
# =========================================================

@router.post(
    "/login",
    response_model=TokenResponse,
)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    """
    Login user and return JWT access token.

    OAuth2 uses the field name `username`.

    In SkillBridge:
        username = user's email
    """

    # -----------------------------------------------------
    # Find user by email
    # -----------------------------------------------------

    user = db.scalar(
        select(User).where(
            User.email == form_data.username
        )
    )

    # -----------------------------------------------------
    # User not found
    # -----------------------------------------------------

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={
                "WWW-Authenticate": "Bearer",
            },
        )

    # -----------------------------------------------------
    # Check password
    # -----------------------------------------------------

    password_valid = verify_password(
        form_data.password,
        user.password_hash,
    )

    if not password_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={
                "WWW-Authenticate": "Bearer",
            },
        )

    # -----------------------------------------------------
    # Check account status
    # -----------------------------------------------------

    if user.account_status == "PENDING":

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "Your account is waiting for Admin approval."
            ),
        )

    if user.account_status == "REJECTED":

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "Your account has been rejected by Admin."
            ),
        )

    if user.account_status != "ACTIVE":

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account is not active.",
        )

    # -----------------------------------------------------
    # Create JWT token
    # -----------------------------------------------------

    access_token = create_access_token(
        user.id
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
    }


# =========================================================
# CURRENT USER
# =========================================================

@router.get(
    "/me",
    response_model=UserResponse,
)
def get_me(
    current_user: User = Depends(
        get_current_user
    ),
):
    """
    Return the currently logged-in user.
    """

    return current_user