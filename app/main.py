"""
app/main.py

The single entrypoint that creates and configures the FastAPI application.

Run it with:
    uvicorn app.main:app --reload

Then visit:
    http://127.0.0.1:8000/docs   -> interactive Swagger UI (auto-generated)
    http://127.0.0.1:8000/health -> simple health check
    http://127.0.0.1:8000/db-check -> database connection check

WHY start here and nowhere else:
Every later part (database, auth, resume upload, matching engine...) plugs
into this file as an "include_router(...)" call. Keeping main.py thin and
letting each feature live in its own router/service file is what keeps a
FastAPI project maintainable as it grows to 10+ endpoints.
"""

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db

# NOTE: no routers are wired in yet — Part 3 (auth), Part 4 (resume upload),
# etc. will each add one `app.include_router(...)` line below, once those
# modules exist. Nothing to import yet in Part 1.

app = FastAPI(
    title=settings.APP_NAME,
    description="AI-Powered Career Recommendation and Skill Gap Analysis Platform",
    version="0.2.0",
    debug=settings.DEBUG,
)

# CORS: allows a separate frontend (Part 11, React) running on a different
# port/domain to call this API from the browser. Wide open for local dev —
# tighten allow_origins to your real frontend URL before deploying.
# CORS is not needed for Postman or curl, only for browser-based clients.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", tags=["root"])
def read_root():
    """Basic landing route so hitting the base URL doesn't 404."""
    return {
        "message": f"{settings.APP_NAME} API is running",
        "docs": "/docs",
    }


@app.get("/health", tags=["root"])
def health_check():
    """
    Health check endpoint.

    Trivial now, but this is the endpoint you'll point uptime monitors /
    deployment platforms (Render, Railway) at once you deploy in Part 12.
    """
    return {"status": "ok", "env": settings.APP_ENV}

@app.get("/db-check", tags=["database"])
def database_check(db: Session = Depends(get_db)):
    """
    Test the connection between FastAPI,
    SQLAlchemy, and Supabase PostgreSQL.
    """

    result = db.execute(text("SELECT 1"))

    return {
        "database": "connected",
        "result": result.scalar(),
    }