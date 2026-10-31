from pathlib import Path
from uuid import uuid4

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    UploadFile,
    status,
)
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from docx import Document
from pypdf import PdfReader

from app.core.database import get_db
from app.core.dependencies import get_current_user

from app.models.resume import Resume
from app.models.user import User
from app.models.skill import Skill
from app.models.resume_skill import ResumeSkill

from app.schemas.resume_skill import ResumeSkillResponse
from app.services.skill_extractor import extract_skills_from_resume


# =========================================
# ROUTER CONFIGURATION
# =========================================

router = APIRouter(
    prefix="/api/resume",
    tags=["Resume"],
)


# =========================================
# UPLOAD DIRECTORY
# =========================================

# Project root: the directory containing app/, uploads/, etc.
PROJECT_ROOT = Path(__file__).resolve().parents[2]

UPLOAD_DIR = PROJECT_ROOT / "uploads" / "resumes"

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


# =========================================
# HELPER: RESOLVE STORED FILE PATH SAFELY
# =========================================

def resolve_resume_file_path(storage_path: str | None) -> Path | None:
    """
    Resolve a saved resume path and ensure that it points
    inside the configured resume upload directory.

    Returns None when the path is missing or points outside
    the allowed upload directory.
    """

    if not storage_path:
        return None

    stored_path = Path(storage_path)

    if not stored_path.is_absolute():
        stored_path = PROJECT_ROOT / stored_path

    try:
        resolved_path = stored_path.resolve()
        resolved_upload_dir = UPLOAD_DIR.resolve()

        # Only allow file deletion inside uploads/resumes.
        resolved_path.relative_to(resolved_upload_dir)

        return resolved_path

    except (ValueError, OSError, RuntimeError):
        return None


# =========================================
# HELPER: EXTRACT TEXT FROM PDF
# =========================================

def extract_pdf_text(file_path: Path) -> str:
    """Extract readable text from a PDF file."""

    reader = PdfReader(str(file_path))

    pages_text = []

    for page in reader.pages:
        page_text = page.extract_text()

        if page_text:
            pages_text.append(page_text)

    return "\n".join(pages_text).strip()


# =========================================
# HELPER: EXTRACT TEXT FROM DOCX
# =========================================

def extract_docx_text(file_path: Path) -> str:
    """Extract readable text from a DOCX file."""

    document = Document(str(file_path))

    paragraphs = []

    for paragraph in document.paragraphs:
        if paragraph.text.strip():
            paragraphs.append(paragraph.text)

    return "\n".join(paragraphs).strip()


# =========================================
# UPLOAD RESUME
# =========================================

@router.post(
    "/upload",
    status_code=status.HTTP_201_CREATED,
)
async def upload_resume(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Upload a PDF or DOCX resume, extract its text,
    and save the resume record in the database.
    """

    # Only Job Seekers can upload resumes.
    if current_user.role != "JOB_SEEKER":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only job seekers can upload resumes.",
        )

    # Check the uploaded filename.
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File name is missing.",
        )

    # Keep only the filename, not any supplied directory path.
    safe_file_name = Path(file.filename).name

    extension = Path(safe_file_name).suffix.lower()

    # Allow only PDF and DOCX files.
    if extension not in {".pdf", ".docx"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF and DOCX files are allowed.",
        )

    # Read uploaded file contents.
    file_content = await file.read()

    if not file_content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty.",
        )

    # Generate a unique stored filename to avoid overwriting
    # another user's file with the same original filename.
    stored_file_name = f"{uuid4().hex}{extension}"

    file_path = UPLOAD_DIR / stored_file_name

    # Save the file.
    try:
        with file_path.open("xb") as buffer:
            buffer.write(file_content)

    except OSError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not save the uploaded resume.",
        ) from exc

    # Extract the resume text.
    try:
        if extension == ".pdf":
            extracted_text = extract_pdf_text(file_path)

        else:
            extracted_text = extract_docx_text(file_path)

    except Exception as exc:
        # Remove the saved file if text extraction fails.
        try:
            file_path.unlink(missing_ok=True)
        except OSError:
            pass

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not extract text from the resume. "
                   "Please check that your PDF or DOCX file is valid.",
        ) from exc

    # Reject files that contain no readable text.
    if not extracted_text:
        try:
            file_path.unlink(missing_ok=True)
        except OSError:
            pass

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not extract readable text from the resume.",
        )

    # Save resume information in the database.
    resume = Resume(
        user_id=current_user.id,
        file_name=safe_file_name,
        storage_path=str(file_path),
        file_type=extension.removeprefix("."),
        extracted_text=extracted_text,
    )

    try:
        db.add(resume)
        db.commit()
        db.refresh(resume)

    except Exception as exc:
        db.rollback()

        # Clean up the stored file if database saving fails.
        try:
            file_path.unlink(missing_ok=True)
        except OSError:
            pass

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not save resume information.",
        ) from exc

    return {
        "message": "Resume uploaded and text extracted successfully.",
        "resume_id": resume.id,
        "file_name": resume.file_name,
        "file_type": resume.file_type,
        "extracted_text": resume.extracted_text,
    }


# =========================================
# EXTRACT RESUME SKILLS
# =========================================

@router.post(
    "/{resume_id}/extract-skills",
    response_model=list[ResumeSkillResponse],
)
def extract_resume_skills(
    resume_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Extract and save skills from a resume belonging
    to the authenticated user.
    """

    # Find the resume owned by the current user.
    resume = db.scalar(
        select(Resume).where(
            Resume.id == resume_id,
            Resume.user_id == current_user.id,
        )
    )

    if resume is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resume not found.",
        )

    # Extract and save the resume skills.
    resume_skills = extract_skills_from_resume(
        db=db,
        resume=resume,
    )

    return [
        {
            "id": resume_skill.id,
            "resume_id": resume_skill.resume_id,
            "skill_id": resume_skill.skill_id,
            "skill_name": resume_skill.skill.name,
            "source": resume_skill.source,
            "confidence": resume_skill.confidence,
        }
        for resume_skill in resume_skills
    ]


# =========================================
# DELETE UPLOADED RESUME
# =========================================

@router.delete(
    "/{resume_id}",
    status_code=status.HTTP_200_OK,
)
def delete_resume(
    resume_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Delete a resume owned by the authenticated user,
    its extracted skill records, and its stored file.

    The endpoint cannot delete another user's resume.
    """

    # Find the resume AND verify ownership.
    resume = db.scalar(
        select(Resume).where(
            Resume.id == resume_id,
            Resume.user_id == current_user.id,
        )
    )

    if resume is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resume not found.",
        )

    # Resolve the saved file path before deleting the database record.
    stored_path = resume.storage_path

    resume_file_path = resolve_resume_file_path(stored_path)

    # If a saved path points outside uploads/resumes, do not delete it.
    unsafe_stored_path = bool(stored_path) and resume_file_path is None

    # Delete the uploaded resume and its extracted skill records.
    try:
        db.execute(
            delete(ResumeSkill).where(
                ResumeSkill.resume_id == resume_id
            )
        )

        db.delete(resume)
        db.commit()

    except Exception as exc:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                "Could not delete the resume from the database. "
                "Check for other database records referencing this resume."
            ),
        ) from exc

    # The database deletion has succeeded.
    # Now remove the stored file, if it exists.
    file_deleted = not unsafe_stored_path

    if resume_file_path is not None and resume_file_path.is_file():
        try:
            resume_file_path.unlink()

        except OSError:
            # Do not claim the file was deleted if cleanup failed.
            file_deleted = False

    return {
        "message": (
            "Resume deleted successfully."
            if file_deleted
            else (
                "The resume record was deleted, but the stored file "
                "could not be removed automatically."
            )
        ),
        "resume_id": resume_id,
        "file_deleted": file_deleted,
    }