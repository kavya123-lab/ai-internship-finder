"""
Attempts to automatically discover a company's HR/careers contact email so
the user doesn't have to look it up manually.

This only reads PUBLICLY published pages on the company's own website — it
never scrapes hidden, authenticated, or personal data, and it always
returns its source so the person applying can verify before sending.

Accuracy is prioritized over coverage: a wrong email is worse than no
email. So this module:
  - Only trusts a domain if the company's name actually appears on that
    domain's homepage (title or body text) — this rejects mismatched or
    unrelated domains that a loose web search can return.
  - Never fabricates or guesses an email pattern (e.g. careers@domain.com)
    when nothing real is found. If it can't confirm a real, published
    email on a confirmed-correct domain, it returns not_found and asks
    the user to enter one manually.

Approach:
  1. If the internship's application link is already the company's own
     domain (not a job board), use that domain directly — but still verify
     the company's name appears on that page before trusting it.
  2. Otherwise, use SerpAPI to find candidate websites and only accept one
     whose search result title/snippet actually mentions the company name.
  3. Fetch the homepage and confirm the company's name appears there too
     (a second, independent check) before trusting the domain at all.
  4. Only then look at a few common public pages (/careers, /contact,
     /about) for a real email address, preferring HR-related ones
     (hr@, careers@, jobs@, talent@, recruitment@).
"""
import re
from typing import Optional, Dict, List
import requests
from config import settings

EMAIL_REGEX = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")
HR_KEYWORDS = ["hr", "careers", "career", "jobs", "job", "recruit", "talent", "hiring", "people"]
JOB_BOARD_DOMAINS = ["linkedin.com", "internshala.com", "indeed.com", "naukri.com", "glassdoor.com"]
CANDIDATE_PATHS = ["", "careers", "contact", "about"]
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; InternshipFinderBot/1.0)"}

# Legal-entity suffixes stripped before comparing company names, since a
# domain's homepage rarely spells out "Private Limited" etc.
COMPANY_SUFFIXES = [
    "private limited", "pvt ltd", "pvt. ltd.", "pvt.ltd", "limited", "ltd",
    "llp", "inc", "inc.", "corporation", "corp", "co.", "llc",
]


def _normalize_company_name(company: str) -> str:
    name = company.lower().strip()
    for suffix in COMPANY_SUFFIXES:
        name = re.sub(rf"\b{re.escape(suffix)}\b", "", name)
    name = re.sub(r"[^a-z0-9\s]", " ", name)
    return re.sub(r"\s+", " ", name).strip()


def _company_name_matches(text: str, company: str) -> bool:
    """True only if a meaningful chunk of the company's name appears in text.
    Requires the first (most distinctive) token to match, plus at least
    half of all meaningful tokens, so a generic single-word overlap like
    "solutions" or "tech" alone can't falsely confirm an unrelated domain."""
    normalized = _normalize_company_name(company)
    if not normalized:
        return False
    tokens = [t for t in normalized.split() if len(t) > 2]
    if not tokens:
        return False
    text_lower = text.lower()
    if tokens[0] not in text_lower:
        return False
    hits = sum(1 for t in tokens if t in text_lower)
    return hits >= max(1, len(tokens) // 2)


def _extract_domain_root(url: str) -> Optional[str]:
    if not url:
        return None
    match = re.match(r"https?://(?:www\.)?([^/]+)", url)
    return match.group(1) if match else None


def _search_company_domain(company: str) -> Optional[str]:
    """Finds candidate websites via SerpAPI, but only returns one whose
    search result title/snippet actually mentions the company name —
    rejects unrelated domains that a loose search can surface."""
    if not settings.serpapi_key:
        return None
    try:
        resp = requests.get(
            "https://serpapi.com/search.json",
            params={"q": f"{company} official website", "api_key": settings.serpapi_key, "num": 5},
            timeout=15,
        )
        resp.raise_for_status()
        for item in resp.json().get("organic_results", []):
            link = item.get("link", "")
            if any(skip in link for skip in JOB_BOARD_DOMAINS + [
                "glassdoor", "facebook.com", "instagram.com", "twitter.com",
                "x.com", "wikipedia.org", "crunchbase.com",
            ]):
                continue
            title_and_snippet = f"{item.get('title', '')} {item.get('snippet', '')}"
            if _company_name_matches(title_and_snippet, company):
                return link
    except Exception as exc:
        print(f"[warn] domain search failed for {company}: {exc}")
    return None


def _fetch_page_text(url: str) -> str:
    try:
        resp = requests.get(url, headers=HEADERS, timeout=6)
        if resp.status_code == 200:
            return resp.text
    except Exception:
        pass
    return ""


def _pick_best_email(emails: List[str]) -> Optional[str]:
    if not emails:
        return None
    hr_matches = [e for e in emails if any(k in e.lower() for k in HR_KEYWORDS)]
    return hr_matches[0] if hr_matches else emails[0]


def find_recruiter_email(company: str, application_link: str = "") -> Dict:
    """Returns {"email": str|None, "confidence": "verified"|"not_found", "source_url": str|None}"""
    domain_root = None
    domain_source = None

    # If the listing link is already the company's own site (not a job
    # board), still confirm the company's name is actually on that page
    # before trusting it — a link alone doesn't guarantee it's really them.
    link_domain = _extract_domain_root(application_link)
    if link_domain and not any(jb in link_domain for jb in JOB_BOARD_DOMAINS):
        homepage_text = _fetch_page_text(f"https://{link_domain}")
        if homepage_text and _company_name_matches(homepage_text, company):
            domain_root = link_domain
            domain_source = application_link

    if not domain_root:
        domain_url = _search_company_domain(company)
        if domain_url:
            candidate_root = _extract_domain_root(domain_url)
            homepage_text = _fetch_page_text(f"https://{candidate_root}")
            # Second, independent check: the homepage itself must mention
            # the company, not just the search snippet.
            if homepage_text and _company_name_matches(homepage_text, company):
                domain_root = candidate_root
                domain_source = domain_url

    if not domain_root:
        return {"email": None, "confidence": "not_found", "source_url": None}

    for path in CANDIDATE_PATHS:
        page_url = f"https://{domain_root}/{path}".rstrip("/")
        text = _fetch_page_text(page_url)
        if not text:
            continue
        found = list(set(EMAIL_REGEX.findall(text)))
        found = [e for e in found if not e.lower().endswith((".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp"))]
        best = _pick_best_email(found)
        if best:
            return {"email": best, "confidence": "verified", "source_url": page_url}

    # Domain is confirmed as the real company, but no email is published
    # on any of the pages checked — do NOT fabricate or guess one.
    return {"email": None, "confidence": "not_found", "source_url": domain_source}
