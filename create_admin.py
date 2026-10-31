import os

from sqlalchemy import select

from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models.user import User


def create_admin():
    email = os.getenv("ADMIN_EMAIL")
    password = os.getenv("ADMIN_PASSWORD")
    if not email or not password:
        raise RuntimeError(
            "Set ADMIN_EMAIL and ADMIN_PASSWORD environment variables "
            "before creating an admin."
        )

    name = os.getenv("ADMIN_NAME", "SkillBridge Admin")
    db = SessionLocal()

    try:
        # -------------------------------------------------
        # Admin information
        # -------------------------------------------------

        # -------------------------------------------------
        # Check if Admin already exists
        # -------------------------------------------------

        existing_user = db.scalar(
            select(User).where(
                User.email == email
            )
        )

        if existing_user:
            print("Admin account already exists.")
            print(f"Email: {existing_user.email}")
            print(f"Role: {existing_user.role}")
            print(f"Status: {existing_user.account_status}")
            return

        # -------------------------------------------------
        # Create Admin
        # -------------------------------------------------

        admin = User(
            name=name,
            email=email,
            password_hash=hash_password(password),
            role="ADMIN",
            account_status="ACTIVE",
        )

        db.add(admin)
        db.commit()
        db.refresh(admin)

        print("====================================")
        print("Admin created successfully!")
        print("====================================")
        print(f"Name: {admin.name}")
        print(f"Email: {admin.email}")
        print(f"Role: {admin.role}")
        print(f"Status: {admin.account_status}")
        print("====================================")

    except Exception as e:
        db.rollback()
        print("Error creating Admin:")
        print(e)

    finally:
        db.close()


if __name__ == "__main__":
    create_admin()