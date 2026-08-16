"""
Scores and ranks Internship objects against the user's stated preferences:
  skill match 40%, recency 20%, company reputation 15%,
  remote flexibility 15%, stipend/compensation 10%
Final sort also nudges anything posted in the last 24h to the very top,
as requested.
"""
from typing import List
from models import Internship, UserPreferences

REPUTABLE_KEYWORDS = [
    "google", "microsoft", "amazon", "flipkart", "zomato", "swiggy",
    "tcs", "infosys", "wipro", "accenture", "adobe", "atlassian",
    "goldman", "jpmorgan", "deloitte", "pwc", "ey", "kpmg", "razorpay",
    "paytm", "zoho", "freshworks",
]


def skill_match_score(internship: Internship, prefs: UserPreferences) -> float:
    if not prefs.skills:
        return 0.5
    req = {s.lower().strip() for s in internship.skills_required}
    wanted = {s.lower().strip() for s in prefs.skills}
    if not req:
        return 0.3
    overlap = len(req & wanted)
    return min(overlap / max(len(wanted), 1), 1.0)


def recency_score(internship: Internship) -> float:
    hours = internship.posted_hours_ago
    if hours is None:
        return 0.3
    if hours <= 24:
        return 1.0
    if hours <= 24 * 7:
        return 0.6
    return 0.2


def reputation_score(internship: Internship) -> float:
    name = internship.company.lower()
    base = 0.6 if internship.company_verified else 0.2
    if any(k in name for k in REPUTABLE_KEYWORDS):
        base = 1.0
    return base


def remote_flexibility_score(internship: Internship, prefs: UserPreferences) -> float:
    mode = (internship.work_mode or "").lower()
    if prefs.work_mode and prefs.work_mode.lower() in mode:
        return 1.0
    if "remote" in mode or "hybrid" in mode:
        return 0.7
    return 0.3


def stipend_score(internship: Internship) -> float:
    stipend = (internship.stipend or "").lower()
    if not stipend:
        return 0.3
    if "unpaid" in stipend:
        return 0.0
    return 0.8


def score_internship(internship: Internship, prefs: UserPreferences) -> float:
    score = (
        skill_match_score(internship, prefs) * 0.40 +
        recency_score(internship) * 0.20 +
        reputation_score(internship) * 0.15 +
        remote_flexibility_score(internship, prefs) * 0.15 +
        stipend_score(internship) * 0.10
    )
    return round(score * 100, 1)


def build_reasons(internship: Internship, prefs: UserPreferences) -> List[str]:
    reasons = []
    req = {s.lower() for s in internship.skills_required}
    wanted = {s.lower() for s in prefs.skills}
    overlap = req & wanted
    if overlap:
        reasons.append(f"Matches your skills: {', '.join(sorted(overlap))}")
    if internship.posted_hours_ago is not None and internship.posted_hours_ago <= 24:
        reasons.append("Posted within the last 24 hours")
    if internship.company_verified:
        reasons.append("Verified company listing")
    if prefs.work_mode and prefs.work_mode.lower() in (internship.work_mode or "").lower():
        reasons.append(f"Matches your preferred work mode: {internship.work_mode}")
    if not reasons:
        reasons.append("Relevant to your target role")
    return reasons[:3]


def rank_internships(internships: List[Internship], prefs: UserPreferences) -> List[Internship]:
    for i in internships:
        i.match_score = score_internship(i, prefs)
        i.reasons = build_reasons(i, prefs)

    def sort_key(i: Internship):
        is_new = i.posted_hours_ago is not None and i.posted_hours_ago <= 24
        return (is_new, i.match_score)

    return sorted(internships, key=sort_key, reverse=True)
