"""
Search tool: queries job boards for internship listings.

IMPORTANT:
Direct scraping of LinkedIn, Naukri, and Indeed violates their Terms of
Service and is aggressively blocked (logins, CAPTCHAs, rate limits). This
tool instead uses a search-engine API (SerpAPI) restricted to each site via
`site:` operators — the standard, ToS-safe way to surface public listings.
"""
import requests
from typing import List, Dict, Optional
from config import settings

SITE_FILTERS = {
    # /jobs/view/ is LinkedIn's URL pattern for one specific posting page,
    # not a search-results hub — much more precise than plain /jobs.
    "linkedin.com/jobs": "site:linkedin.com/jobs/view",
    # /internship/detail/ is Internshala's individual-listing pattern.
    "internshala.com": "site:internshala.com/internship/detail",
    # /viewjob is Indeed's individual-listing pattern (covers indeed.com
    # and its India subdomain, in.indeed.com).
    "indeed.com": "(site:indeed.com/viewjob OR site:in.indeed.com/viewjob)",
    # /job-listings- is Naukri's individual-posting URL pattern.
    "naukri.com": "site:naukri.com/job-listings",
}


def build_query(role: str, location: str = "", skills: Optional[List[str]] = None) -> str:
    parts = [role, "internship"]
    if location:
        parts.append(location)
    if skills:
        parts.append(" ".join(skills[:3]))
    return " ".join(parts)


def search_site(site_key: str, role: str, location: str = "", skills=None) -> List[Dict]:
    if not settings.serpapi_key:
        raise RuntimeError("SERPAPI_KEY not set. Add it to your .env file to enable live search.")
    query = f"{SITE_FILTERS[site_key]} {build_query(role, location, skills)}"
    resp = requests.get(
        "https://serpapi.com/search.json",
        params={
            "q": query,
            "api_key": settings.serpapi_key,
            "num": settings.max_results_per_source,
            # tbs=qdr:d restricts Google itself to results from the past 24
            # hours — far more reliable than asking the LLM to guess "how
            # old" a listing is from a vague snippet like "5 days ago".
            "tbs": "qdr:d",
        },
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()
    return [
        {
            "title": item.get("title", ""),
            "link": item.get("link", ""),
            "snippet": item.get("snippet", ""),
            "source": site_key,
        }
        for item in data.get("organic_results", [])
    ]


def search_all_sources(role: str, location: str = "", skills=None) -> List[Dict]:
    if not settings.serpapi_key:
        raise RuntimeError("SERPAPI_KEY not set. Add it to your .env file to enable search.")

    all_results: List[Dict] = []
    for site_key in settings.search_order:
        try:
            all_results.extend(search_site(site_key, role, location, skills))
        except Exception as exc:
            print(f"[warn] search failed for {site_key}: {exc}")
    return all_results
