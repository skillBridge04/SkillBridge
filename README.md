# SkillBridge Backend

AI-Powered Career Recommendation and Skill Gap Analysis Platform.

Built incrementally, following this order:

1. **FastAPI foundation** ← you are here
2. PostgreSQL + SQLAlchemy
3. Authentication (JWT)
4. Resume PDF/DOCX upload
5. Resume text extraction
6. AI skill extraction
7. Companies + jobs database
8. Job/company matching
9. Skill-gap analysis
10. Course recommendation
11. Frontend/dashboard
12. Live job data + deployment

## Part 1 — What's included

```
app/
├── main.py           # FastAPI app entrypoint
├── core/
│   └── config.py      # Typed settings loaded from .env
├── models/            # (empty — Part 2 adds SQLAlchemy models here)
├── schemas/           # (empty — Pydantic request/response schemas)
├── routers/           # (empty — Part 3+ adds route modules here)
├── services/          # (empty — business logic lives here, not in routers)
└── utils/             # (empty — shared helper functions)
uploads/                # where resume files will be stored (Part 4)
```

## Setup

```bash
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

pip install -r requirements.txt

cp .env.example .env            # then edit .env if needed
```

## Run it

```bash
uvicorn app.main:app --reload
```

Then open:
- http://127.0.0.1:8000/docs — interactive Swagger UI (auto-generated from your endpoints)
- http://127.0.0.1:8000/health — health check

## Why the project is structured this way

- **`core/config.py`** — one place for all settings, instead of `os.getenv()` scattered everywhere.
- **`routers/`** — each feature (auth, resumes, jobs...) gets its own router file, kept thin (just request/response wiring).
- **`services/`** — actual business logic (resume parsing, skill matching...) lives here, separate from routing, so it can be unit-tested without spinning up the API.
- **`models/` vs `schemas/`** — SQLAlchemy `models` describe database tables; Pydantic `schemas` describe API request/response shapes. Keeping them separate means you can change your API's public shape without touching the database, and vice versa.

This mirrors the architecture recommendation in the project roadmap: keep the resume analyzer, user profile, and recommendation engine as separate, explainable stages rather than one AI black box.
