"""
Uses Groq (Llama 3.3 70B) to convert noisy search-engine snippets into
structured Internship records. This version is instructed to DROP any
listing where the company, role, or application link can't be confidently
determined, rather than filling those fields with "Not specified" — the
UI should never show placeholder text to the user.
"""
import json
from typing import List, Dict
from openai import OpenAI
from config import settings
from models import Internship

_client = None


def _get_client() -> OpenAI:
    """Lazily creates the Groq client so the app can still start (and serve
    the UI) even before GROQ_API_KEY is filled in — the clear error only
    appears when a search is actually attempted."""
    global _client
    if _client is None:
        if not settings.groq_api_key:
            raise RuntimeError("GROQ_API_KEY not set. Add it to your .env file to enable search.")
        _client = OpenAI(api_key=settings.groq_api_key, base_url="https://api.groq.com/openai/v1")
    return _client

EXTRACTION_PROMPT = """You will be given raw web search results (title, link, snippet)
about internship listings. These results have already been filtered by Google to the
past 24 hours, but that filter is based on when Google last crawled the page, not
necessarily the internship's actual posting date — so you must independently verify
recency and status from the text itself.

STRICT RULES — exclude a result entirely (do not include it in the output) if ANY of
these are true:
1. You cannot confidently determine the company name, the role title, AND a working
   application link.
2. The snippet or title contains any signal that the role is CLOSED or no longer open,
   such as: "applications closed", "no longer accepting applications", "position
   filled", "hiring completed", "expired", "this job has expired", "applications are
   closed for this posting". Set is_actively_hiring to false and exclude it.
3. The snippet explicitly states the posting is OLDER than 24 hours — phrases like
   "2 days ago", "1 week ago", "3 weeks ago", "1 month ago", "5 months ago", or an
   explicit date more than 1 day in the past. Do NOT include these. Only include
   listings where the text says things like "posted today", "just now", "X hours ago"
   (X <= 24), "new", or gives no explicit age at all (in that last case, only include
   it if there is nothing suggesting it's old, and set posted_hours_ago to null).
4. It's a listicle, blog post, "top internships" roundup, or anything that isn't a
   specific posting for one role at one company.

For fields that remain:
- posted: a short human-readable string like "Posted today", "3 hours ago", or
  "Recently posted" if truly unknown. NEVER use "Not specified" as a value anywhere.
- posted_hours_ago: a number if you can infer it from the text, else null.
- location, work_mode, duration, stipend: only fill if the snippet actually states it,
  otherwise use "" (empty string).
- recruiter_email: only fill if an actual email address appears in the snippet text
  (rare). Otherwise use "".
- company_verified: true only if the source is a major job board (LinkedIn, Naukri,
  Indeed, Internshala) and the company name looks like a real registered business.
- is_actively_hiring: true unless you found a closed/expired signal per rule 2 above
  (in which case exclude the result entirely rather than including it as false).

Return ONLY a JSON array, no prose, no markdown fences. Each object must have exactly
these keys: company, role, location, work_mode, posted, posted_hours_ago, duration,
stipend, skills_required (array), application_link, source, company_verified (bool),
is_actively_hiring (bool), recruiter_email.

Search results:
{results}
"""


def extract_internships(raw_results: List[Dict]) -> List[Internship]:
    if not raw_results:
        return []

    payload = "\n\n".join(
        f"Title: {r['title']}\nLink: {r['link']}\nSnippet: {r['snippet']}\nSource: {r['source']}"
        for r in raw_results
    )

    response = _get_client().chat.completions.create(
        model=settings.groq_model,
        max_tokens=4000,
        messages=[{"role": "user", "content": EXTRACTION_PROMPT.format(results=payload)}],
    )

    text = response.choices[0].message.content or ""
    text = text.strip().strip("```json").strip("```").strip()

    try:
        raw_list = json.loads(text)
    except json.JSONDecodeError:
        print("[warn] could not parse extraction output, returning no results")
        return []

    internships = []
    for item in raw_list:
        try:
            internships.append(Internship(
                company=(item.get("company") or "").strip(),
                role=(item.get("role") or "").strip(),
                location=(item.get("location") or "").strip(),
                work_mode=(item.get("work_mode") or "").strip(),
                posted=(item.get("posted") or "Recently posted").strip(),
                posted_hours_ago=item.get("posted_hours_ago"),
                duration=(item.get("duration") or "").strip(),
                stipend=(item.get("stipend") or "").strip(),
                skills_required=item.get("skills_required", []) or [],
                application_link=(item.get("application_link") or "").strip(),
                source=item.get("source", ""),
                company_verified=bool(item.get("company_verified", False)),
                is_actively_hiring=bool(item.get("is_actively_hiring", True)),
                recruiter_email=(item.get("recruiter_email") or "").strip(),
            ))
        except Exception as exc:
            print(f"[warn] skipping malformed record: {exc}")
    return internships
