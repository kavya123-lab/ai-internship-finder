"""
Post-extraction quality filter. This is a safety net BEHIND the extraction
prompt — even if the LLM doesn't follow instructions perfectly, these are
hard Python-level rules, so:
  1. No placeholder text ("Not specified" etc.) ever reaches the UI.
  2. Nothing older than 24 hours gets through.
  3. Anything that looks closed/expired gets dropped.
"""
from typing import List
from models import Internship

PLACEHOLDER_VALUES = {"", "not specified", "n/a", "unknown", "none"}

CLOSED_SIGNALS = [
    "no longer accepting", "applications closed", "application closed",
    "position filled", "position has been filled", "hiring completed",
    "expired", "closed for this posting", "job has expired",
    "no longer available", "this position is closed",
]


def _is_placeholder(value: str) -> bool:
    return (value or "").strip().lower() in PLACEHOLDER_VALUES


def _looks_closed(internship: Internship) -> bool:
    haystack = f"{internship.role} {internship.posted} {internship.stipend}".lower()
    return any(signal in haystack for signal in CLOSED_SIGNALS)


def is_quality_result(internship: Internship) -> bool:
    if _is_placeholder(internship.company):
        return False
    if _is_placeholder(internship.role):
        return False
    if _is_placeholder(internship.application_link):
        return False
    if not internship.is_actively_hiring:
        return False
    if _looks_closed(internship):
        return False
    # Strict 24-hour rule: unknown age or anything older than 24h is dropped.
    if internship.posted_hours_ago is not None and internship.posted_hours_ago > 24:
        return False
    return True


def filter_quality_results(internships: List[Internship]) -> List[Internship]:
    return [i for i in internships if is_quality_result(i)]
