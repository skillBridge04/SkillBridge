from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from docx import Document
from pypdf import PdfReader

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.resume import Resume
from app.models.user import User

from sqlalchemy import select

from app.models.skill import Skill
from app.models.resume_skill import ResumeSkill
from app.schemas.resume_skill import ResumeSkillResponse
from app.services.skill_extractor import extract_skills_from_resume


router = APIRouter(
    prefix="/api/resume",
    tags=["Resume"],
)


UPLOAD_DIR = Path("uploads/resumes")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def extract_pdf_text(file_path: Path) -> str:
    """Extract text from a PDF file."""

    reader = PdfReader(str(file_path))

    text = ""

    for page in reader.pages:
        page_text = page.extract_text()

        if page_text:
            text += page_text + "\n"

    return text.strip()


def extract_docx_text(file_path: Path) -> str:
    """Extract text from a DOCX file."""

    document = Document(str(file_path))

    text = ""

    for paragraph in document.paragraphs:
        if paragraph.text.strip():
            text += paragraph.text + "\n"

    return text.strip()


@router.post(
    "/upload",
    status_code=status.HTTP_201_CREATED,
)
async def upload_resume(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Only Job Seekers can upload resumes
    if current_user.role != "JOB_SEEKER":
        raise HTTPException(
            status_code=403,
            detail="Only job seekers can upload resumes",
        )

    # Check file extension
    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="File name is missing",
        )

    extension = Path(file.filename).suffix.lower()

    if extension not in [".pdf", ".docx"]:
        raise HTTPException(
            status_code=400,
            detail="Only PDF and DOCX files are allowed",
        )

    # Read uploaded file
    file_content = await file.read()

    if not file_content:
        raise HTTPException(
            status_code=400,
            detail="Uploaded file is empty",
        )

    # Create safe file name
    safe_file_name = Path(file.filename).name

    file_path = UPLOAD_DIR / safe_file_name

    # Save file
    with open(file_path, "wb") as buffer:
        buffer.write(file_content)

    # Extract text
    try:
        if extension == ".pdf":
            extracted_text = extract_pdf_text(file_path)

        else:
            extracted_text = extract_docx_text(file_path)

    except Exception as e:
        # Delete file if extraction fails
        if file_path.exists():
            file_path.unlink()

        raise HTTPException(
            status_code=400,
            detail=f"Could not extract text from resume: {str(e)}",
        )

    # Check if text was extracted
    if not extracted_text:
        raise HTTPException(
            status_code=400,
            detail="Could not extract readable text from the resume",
        )

    # Save resume information in database
    resume = Resume(
        user_id=current_user.id,
        file_name=safe_file_name,
        storage_path=str(file_path),
        file_type=extension.replace(".", ""),
        extracted_text=extracted_text,
    )

    db.add(resume)
    db.commit()
    db.refresh(resume)

    return {
        "message": "Resume uploaded and text extracted successfully",
        "resume_id": resume.id,
        "file_name": resume.file_name,
        "file_type": resume.file_type,
        "extracted_text": resume.extracted_text,
    }

@router.post(
    "/{resume_id}/extract-skills",
    response_model=list[ResumeSkillResponse],
)
def extract_resume_skills(
    resume_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Find the resume
    resume = db.scalar(
        select(Resume).where(
            Resume.id == resume_id,
            Resume.user_id == current_user.id,
        )
    )

    if not resume:
        raise HTTPException(
            status_code=404,
            detail="Resume not found",
        )

    # Extract and save skills
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