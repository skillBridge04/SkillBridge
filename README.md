# SkillBridge

AI-Powered Career Recommendation, Job Matching & Skill Gap Analysis Platform

SkillBridge is a full-stack career guidance platform that analyzes a user's resume, identifies their skills and qualifications, recommends relevant companies and job opportunities, compares their skills with job requirements, identifies skill gaps, and recommends relevant courses to help users improve their skills.

---

## 📌 Project Overview

Finding a suitable job can be difficult because users may not know which companies or jobs match their current skills and qualifications.

SkillBridge helps users:

- Analyze their resume
- Identify their skills and qualifications
- Find suitable companies and job opportunities
- Compare their skills with job requirements
- Identify missing skills
- Find relevant courses to learn those skills

### Main Workflow

```text
                    User
                     │
                     ▼
             Upload Resume
              PDF / DOCX
                     │
                     ▼
             Resume Processing
                     │
                     ▼
             AI Resume Analysis
                     │
          ┌──────────┼──────────┐
          ▼          ▼          ▼
       Skills     Education   Experience
          │          │          │
          └──────────┼──────────┘
                     ▼
                User Profile
                     │
                     ▼
             Job & Company Matching
                     │
          ┌──────────┼──────────┐
          ▼          ▼          ▼
       Companies     Jobs      Salary
                     │
                     ▼
              Job Requirements
                     │
                     ▼
             Skill Gap Analysis
                     │
           ┌─────────┴─────────┐
           ▼                   ▼
     Matching Skills       Missing Skills
                               │
                               ▼
                     Course Recommendation
                               │
                               ▼
                       Learning Roadmap
## 🚀 Main Features

- Resume upload (PDF/DOCX)
- AI-powered skill extraction
- Company recommendations
- Job recommendations
- Job match percentage
- Salary and qualification information
- Skill gap analysis
- Course recommendations
- Personalized learning roadmap
## 🛠️ Technology Stack

- **Frontend:** React / Next.js
- **Backend:** Python, FastAPI
- **Database:** PostgreSQL, Supabase
- **ORM & Migration:** SQLAlchemy, Alembic
- **AI/NLP:** DeepSeek API, spaCy
- **Resume Processing:** pdfplumber, python-docx
- **Storage:** Supabase Storage
## 👥 Contributors

- Contributor 1
- Contributor 2
- Contributor 3
- Contributor 4
