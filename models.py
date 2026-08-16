"""
Data models used throughout the agent.
"""
from dataclasses import dataclass, field
from typing import Optional, List


@dataclass
class UserPreferences:
    role: str
    location: Optional[str] = None
    work_mode: Optional[str] = None          # Remote / Hybrid / Onsite
    skills: List[str] = field(default_factory=list)
    experience_level: str = "fresher"


@dataclass
class Internship:
    company: str
    role: str
    location: str
    work_mode: str
    posted: str                              # human readable, e.g. "18 hours ago"
    posted_hours_ago: Optional[float]        # numeric, used for recency scoring
    duration: str
    stipend: str
    skills_required: List[str]
    application_link: str
    source: str                              # LinkedIn / Internshala / Indeed / Naukri
    company_verified: bool = False
    is_actively_hiring: bool = True          # False if listing shows signs of being closed/expired
    recruiter_email: Optional[str] = ""      # only populated if found in listing text
    match_score: float = 0.0
    reasons: List[str] = field(default_factory=list)
