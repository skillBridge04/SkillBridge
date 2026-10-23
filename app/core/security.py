from datetime import datetime, timedelta, timezone

import jwt
from pwdlib import PasswordHash


from app.core.config import settings


# ---------------------------------------------------------
# PASSWORD HASHING
# ---------------------------------------------------------

password_hash = PasswordHash.recommended()


def hash_password(password: str) -> str:
    """
    Convert a plain password into a secure Argon2 hash.
    """
    return password_hash.hash(password)


def verify_password(
    plain_password: str,
    hashed_password: str,
) -> bool:
    """
    Check whether the entered password matches
    the password hash stored in the database.
    """
    return password_hash.verify(
        plain_password,
        hashed_password,
    )


# ---------------------------------------------------------
# JWT
# ---------------------------------------------------------

ALGORITHM = "HS256"


def create_access_token(user_id: int) -> str:
    """
    Create a JWT access token for the user.
    """

    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )

    payload = {
        "sub": str(user_id),
        "exp": expire,
    }

    token = jwt.encode(
        payload,
        settings.SECRET_KEY,
        algorithm=ALGORITHM,
    )

    return token