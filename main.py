"""
FastAPI backend for the AI Internship Finder web app.

Endpoints:
  POST /api/search  -> runs the search/extract/rank pipeline, returns JSON
  POST /api/apply    -> takes form fields + an uploaded resume file, sends
                         the application email directly (no file paths)

Also serves the static frontend (index.html / styles.css / app.js).
"""
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from models import UserPreferences, Internship
from search_tool import search_all_sources
from extractor import extract_internships
from filters import filter_quality_results
from ranking import rank_internships
from email_tool import send_application_email
from recruiter_finder import find_recruiter_email

BASE_DIR = Path(__file__).resolve().parent
FRONTEND_DIR = BASE_DIR / "frontend"

app = FastAPI(title="AI Internship Finder")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class SearchRequest(BaseModel):
    role: str
    location: Optional[str] = ""
    work_mode: Optional[str] = ""
    skills: Optional[str] = ""        # comma-separated string from the form
    experience_level: Optional[str] = "fresher"


def internship_to_dict(i: Internship) -> dict:
    return {
        "company": i.company,
        "role": i.role,
        "location": i.location or "Location not listed",
        "work_mode": i.work_mode or "Not specified in listing",
        "posted": i.posted,
        "posted_hours_ago": i.posted_hours_ago,
        "is_new": i.posted_hours_ago is None or i.posted_hours_ago <= 24,
        "is_actively_hiring": i.is_actively_hiring,
        "duration": i.duration or "Not listed",
        "stipend": i.stipend or "Not disclosed",
        "skills_required": i.skills_required,
        "application_link": i.application_link,
        "source": i.source,
        "company_verified": i.company_verified,
        "recruiter_email": i.recruiter_email or "",
        "match_score": i.match_score,
        "reasons": i.reasons,
    }


@app.post("/api/search")
def api_search(req: SearchRequest):
    if not req.role.strip():
        raise HTTPException(status_code=400, detail="Role is required")

    skills_list = [s.strip() for s in req.skills.split(",") if s.strip()]
    prefs = UserPreferences(
        role=req.role.strip(),
        location=(req.location or "").strip() or None,
        work_mode=(req.work_mode or "").strip() or None,
        skills=skills_list,
        experience_level=req.experience_level or "fresher",
    )

    try:
        raw_results = search_all_sources(prefs.role, prefs.location, prefs.skills)
        internships = extract_internships(raw_results)
        internships = filter_quality_results(internships)
        ranked = rank_internships(internships, prefs)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    return {
        "count": len(ranked),
        "results": [internship_to_dict(i) for i in ranked[:15]],
    }


class RecruiterEmailRequest(BaseModel):
    company: str
    application_link: Optional[str] = ""


@app.post("/api/find-recruiter-email")
def api_find_recruiter_email(req: RecruiterEmailRequest):
    if not req.company.strip():
        raise HTTPException(status_code=400, detail="Company name is required")
    try:
        return find_recruiter_email(req.company.strip(), req.application_link or "")
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.post("/api/apply")
async def api_apply(
    name: str = Form(...),
    email: str = Form(...),
    phone: str = Form(...),
    linkedin_url: str = Form(...),
    portfolio_url: Optional[str] = Form(None),
    recruiter_email: str = Form(...),
    role: str = Form(...),
    company: str = Form(...),
    resume: UploadFile = File(...),
):
    try:
        resume_bytes = await resume.read()
        if not resume_bytes:
            raise ValueError("Uploaded resume file is empty")

        send_application_email(
            applicant_name=name,
            applicant_email=email,
            applicant_phone=phone,
            linkedin_url=linkedin_url,
            role=role,
            company=company,
            recruiter_email=recruiter_email,
            resume_bytes=resume_bytes,
            resume_filename=resume.filename or "resume.pdf",
            portfolio_url=portfolio_url,
        )
        return {"success": True, "message": f"Application sent to {company} for the {role} role."}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


# Serve the frontend (must be added last so /api/* routes above take priority)
app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")
