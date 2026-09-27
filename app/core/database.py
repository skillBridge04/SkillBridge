"""
app/core/database.py

Database configuration for SkillBridge.
"""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import settings


# ---------------------------------------------------------
# DATABASE ENGINE
# ---------------------------------------------------------

engine = create_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_pre_ping=True,
)


# ---------------------------------------------------------
# DATABASE SESSION
# ---------------------------------------------------------

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
)


# ---------------------------------------------------------
# BASE CLASS
# ---------------------------------------------------------

class Base(DeclarativeBase):
    """
    Parent class for all SQLAlchemy models.
    """
    pass


# ---------------------------------------------------------
# DATABASE DEPENDENCY
# ---------------------------------------------------------

def get_db() -> Generator[Session, None, None]:
    """
    Provide a database session to FastAPI routes.
    """

    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()