# SkillBridge

AI-powered career recommendation and skill gap analysis platform for job seekers.

Upload a resume, get matched jobs and companies with a readiness score, see which skills you are missing, and follow recommended courses to close the gap.

## Features

**Job Seeker**
- Register and log in (email/password or Google OAuth)
- Upload a resume in PDF or DOCX format
- AI-based skill extraction, normalized against a skill taxonomy
- Ranked company and job recommendations with a readiness score
- Explainable skill-gap analysis (top matched and missing skills)
- Course recommendations mapped to each missing skill
- Recruiter visibility consent toggle and a log of who viewed the profile

**Recruiter / Employer**
- Register with a work email and get verified by an Admin
- Post and manage job requirements
- Search consenting candidate profiles by skill-match score
- Shortlist candidates; contact details are shared only after the candidate accepts

**Admin / Authority**
- Approve or reject recruiter accounts
- Manage companies, jobs, skills taxonomy, courses and skill-to-course mapping
- Monitor users, flagged resumes and platform statistics

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | FastAPI (Python) |
| Database | PostgreSQL, SQLAlchemy, Alembic |
| Frontend | HTML, CSS, Node.JS, React |
| Resume parsing | pdfplumber, python-docx |
| AI / NLP | DeepSeek API (spaCy and Sentence Transformers planned) |

## Architecture

Client-server with a centralized data store, and a layered backend: Router → Service → Model/Schema.
## Project Structure

```
SkillBridge/
├── app/
│   ├── main.py            # FastAPI entry point
│   ├── routers/           # HTTP endpoints (auth, resumes, jobs, admin, recruiter)
│   ├── services/          # Business logic (parsing, skill extraction, matching, skill gap, courses)
│   ├── models/            # SQLAlchemy models (users, resumes, resume_skills, skills, companies, jobs, job_skills, courses)
│   └── schemas/           # Pydantic request/response schemas
├── alembic/               # Database migrations
├── frontend/              # React app (Job Seeker, Recruiter and Admin interfaces)
├── docs/                  # SRS, architecture and design document, diagrams
├── requirements.txt       # Python dependencies
├── .env.example           # Example environment variables (no real secrets)
├── .gitignore
└── README.md
```
## Getting Started

```bash
# 1. Clone the repository
git clone https://github.com/skillBridge04/SkillBridge.git
cd SkillBridge

# 2. Create a virtual environment and install dependencies
python -m venv venv
venv\Scripts\activate        # Windows
pip install -r requirements.txt

# 3. Add your settings
# Copy .env.example to .env and fill in the values (database URL, DeepSeek API key)

# 4. Run database migrations
alembic upgrade head

# 5. Start the server
uvicorn app.main:app --reload
```

## Documentation

- SRS, architecture and design: see the `docs/` folder
- Figma prototype: *(add link here)*

## Team

CSE 314 — Software Engineering Lab, University of Asia Pacific

| Name | Role |
|---|---|
| Rafi Ahammed Rajon | Business Analyst / Project Manager |
| Foujia Jahan Prome | Team Lead |
| Sabbir Ahmed Shisir | Reporting Lead |
| Mahinur E Jannat | QA Lead |

Submitted to: Md. Ashraful Alam, Lecturer of CSE
