# AI Internship Finder

An **agentic AI web app** that searches LinkedIn, Internshala, Indeed, and Naukri for internships matching your role, location, and skills — filters out anything closed or older than 24 hours, ranks what's left, and lets you apply from the browser with one click (real file upload, auto-filled recruiter email lookup, no manual steps).

This isn't a chatbot that answers questions about internships — it's an agent that actually **does the searching, filtering, ranking, and applying** on your behalf.

---

## Demo

**🎥 Video walkthrough:** [Watch the demo](https://drive.google.com/file/d/1tAOObPEiEf9uxE51ihYrbGaAjCRnVVJT/view?usp=sharing)

**Screenshots:**

| Search | Results |
|---|---|
| ![Search form](docs/screenshots/search.png) | ![Results grid](docs/screenshots/results.png) |

| Apply Modal | Success |
|---|---|
| ![Apply modal](docs/screenshots/apply.png) | ![Applied successfully](docs/screenshots/success.png) |

---

## Table of Contents
- [Why I built this](#why-i-built-this)
- [How it works — the pipeline](#how-it-works--the-pipeline)
- [Tech stack, and why each piece](#tech-stack-and-why-each-piece)
- [API keys — what each one is for](#api-keys--what-each-one-is-for)
- [Setup](#setup)
- [Project structure](#project-structure)
- [Features](#features)
- [Problems I ran into (and how I solved them)](#problems-i-ran-into-and-how-i-solved-them)
- [Known limitations — being honest about what this can't do](#known-limitations--being-honest-about-what-this-cant-do)
- [Future improvements](#future-improvements)

---

## Why I built this

After building an LLM + RAG-based chatbot, I wanted to go a step further — from **GenAI** (an app that generates a response to a prompt) to **Agentic AI** (an app that takes a goal and independently works through the steps to complete it: search, extract, filter, rank, and act).

The concrete problem: manually checking four different job boards every day for internships matching a specific role/skill set is repetitive and slow. This app automates that entire loop.

---

## How it works — the pipeline

```
1. SEARCH     → Query LinkedIn, Internshala, Indeed, Naukri via SerpAPI,
                restricted to individual posting pages, filtered to the
                past 24 hours at the Google-search level itself.

2. EXTRACT    → An LLM (Groq / Llama 3.3 70B) reads the raw, messy search
                snippets and turns them into clean, structured data:
                company, role, location, stipend, skills, etc.

3. FILTER     → Independent Python-level rules (not just LLM instructions)
                drop anything incomplete, older than 24h, or showing signs
                of being closed/expired ("applications closed", "position
                filled", etc.)

4. RANK       → Score each listing: skill match (40%), recency (20%),
                company reputation (15%), work-mode fit (15%), stipend (10%)

5. APPLY      → One click opens a form (name, resume upload, etc.), the app
                auto-searches the company's own website for a verified HR
                email, and sends the application email with resume attached
```

---

## Tech stack, and why each piece

| Piece | What I used | Why |
|---|---|---|
| **Backend** | FastAPI (Python) | Fast to build, native async support for calling multiple external APIs (search, LLM, email) without blocking, and serves the frontend + API from one process. |
| **LLM / reasoning** | Groq (Llama 3.3 70B) | Used to turn unstructured search-result text into structured JSON. Chosen over Anthropic/OpenAI because it's **free to start with and requires no payment method** — important for a personal project. |
| **Search** | SerpAPI | LinkedIn, Naukri, and Indeed prohibit automated scraping in their Terms of Service and block bots aggressively (logins, CAPTCHAs). SerpAPI queries Google itself with `site:` filters — a search-engine query, not a scrape — which is the standard ToS-safe way to surface public listings from those sites. |
| **Email** | Python's built-in `smtplib` + Gmail SMTP | No extra service/cost needed; sends the application email with the resume attached directly from the backend. |
| **Frontend** | Plain HTML/CSS/JS (no framework) | The UI is a single search form + result cards + one modal — a full framework (React, Vue) would be unnecessary overhead for this scope. Keeps the project dependency-light and easy to read end to end. |

---

## API keys — what each one is for

### 1. `GROQ_API_KEY`
**What it's for:** Reads the raw search results and extracts structured internship data (company name, role, stipend, skills, etc.) using Llama 3.3 70B.
**Where to get it:** [console.groq.com/keys](https://console.groq.com/keys) — free, no credit card required.
**Why Groq specifically:** I originally planned to use Anthropic's Claude for this, but their API requires a payment method on file even for light usage. Groq offered a genuinely free tier, which mattered for a personal/learning project.

### 2. `SERPAPI_KEY`
**What it's for:** Searches LinkedIn, Internshala, Indeed, and Naukri — restricted to each site's individual-posting URL pattern (e.g. `linkedin.com/jobs/view/...`, `indeed.com/viewjob`) and filtered to the past 24 hours using Google's own `tbs=qdr:d` time filter. Also used by the recruiter-email finder to locate a company's official website.
**Where to get it:** [serpapi.com](https://serpapi.com) — free tier gives 250 searches/month.
**Why not scrape directly:** LinkedIn/Indeed/Naukri explicitly forbid scraping in their Terms of Service and technically block it (login walls, bot detection). There's no public developer API for individuals for any of the four platforms. Querying Google's index of their public pages is the closest ToS-compliant approximation of "search these sites directly."

### 3. `SMTP_USER` / `SMTP_PASSWORD`
**What it's for:** Sends the actual application email with the resume attached, when you click Submit in the Apply modal.
**Where to get it:** Your Gmail address + a **Gmail App Password** (not your normal password) — generated at `myaccount.google.com/apppasswords`, requires 2-Step Verification turned on first.
**Why an App Password, not the real password:** Google blocks direct SMTP login with your actual account password for security; an App Password is a scoped, revocable credential just for this purpose.

---

## Setup

```bash
git clone <your-repo-url>
cd ai-internship-finder-webapp
pip install -r requirements.txt
cp .env.example .env
# fill in GROQ_API_KEY, SERPAPI_KEY, SMTP_USER, SMTP_PASSWORD in .env
uvicorn main:app --reload --port 8000
```
Open **http://127.0.0.1:8000** in your browser.

---

## Project structure

```
main.py                → FastAPI app: /api/search, /api/apply,
                          /api/find-recruiter-email, serves the frontend
config.py                 → loads all settings from .env
models.py                    → shared data classes (Internship, UserPreferences)
search_tool.py                  → queries job boards via SerpAPI,
                                   site:-restricted to individual posting URLs
extractor.py                       → Groq (Llama 3.3) extracts structured
                                      listings, discards incomplete/closed ones
filters.py                            → Python-level safety net: strict 24h
                                         rule, closed-listing keyword detection
ranking.py                               → scores + sorts by skill/recency/
                                            reputation/work-mode/stipend
recruiter_finder.py                         → verifies a company's real
                                               website, finds a published
                                               HR email (never guesses one)
email_tool.py                                  → sends the application email
                                                  with the uploaded resume
frontend/
  index.html                                      → page structure
  styles.css                                          → blue/white theme
  app.js                                                 → search, render
                                                            cards, apply modal,
                                                            autosuggest, tags
```

---

## Features

- **Autosuggest** on Role, Location, and Skills (Skills as removable tag chips)
- **Strict 24-hour filtering**, enforced at three independent layers: the Google search filter itself, the LLM extraction prompt, and a hard Python-level rule — so it doesn't rely on any single layer getting it right
- **Closed/expired listing detection** — drops postings with signals like "applications closed" or "position filled"
- **Real file upload** for the resume — no typed file paths
- **Automatic recruiter-email discovery** — searches the company's own website for a published HR/careers email, but only after verifying the company's name actually appears on that domain (see below for why this needed a rewrite)
- **One-click apply** — fills the email, attaches the resume, sends it, confirms success in the UI

---

## Problems I ran into (and how I solved them)

### 1. "Not specified" everywhere
Early on, extracted listings were full of placeholder text — "Not specified" for location, stipend, work mode — because the LLM was filling in gaps rather than admitting it didn't know.
**Fix:** Rewrote the extraction prompt to explicitly discard a listing entirely if the company, role, or application link couldn't be confidently determined, and added a second Python-level filter (`filters.py`) as a safety net that doesn't depend on the LLM following instructions perfectly.

### 2. Results showing internships from weeks or months ago
Asking the LLM to infer "how recent" a listing is from a vague snippet like "5 months ago" was unreliable, and I explicitly wanted **only postings from the last 24 hours.**
**Fix:** Added Google's own `tbs=qdr:d` time filter directly to the SerpAPI search request — filtering happens *before* anything reaches the AI, not by asking the AI to guess. Backed it up with explicit LLM instructions and a hard Python-level rule that drops anything with `posted_hours_ago > 24`.

### 3. The app crashed on startup without a Groq key
The Groq client was being initialized eagerly at import time, so the whole server failed to boot if `.env` wasn't filled in yet.
**Fix:** Made the client lazy — it's only created the first time a search actually runs, so the UI can load and show a clear error message instead of the whole app crashing silently.

### 4. Typing a file path for the resume (CLI era)
The original CLI version asked the user to type a Windows file path manually — error-prone (OneDrive placeholder files, typos, wrong quotes).
**Fix:** Rebuilt as a web app with FastAPI and a real `<input type="file">` — the browser handles the file, no path typing at all.

### 5. Auto-found recruiter emails were wrong
This was the most important bug. The recruiter-email finder searched for "Company Name official website" and trusted whatever domain came back — but for lesser-known companies, that search can return an unrelated or similarly-named site, and the tool would confidently pull an email from the wrong company entirely. On top of that, when no real email was found, it fell back to *guessing* one (`careers@domain.com`) — a fabricated answer presented as a "best guess."
**Fix:** Rewrote the verification logic so a domain is only trusted if the company's actual name appears on that domain's homepage — checked independently at two points (the search result text, and the fetched homepage itself), requiring the most distinctive name token to match plus at least half of all meaningful tokens, so a generic single-word overlap ("Solutions", "Tech") can't falsely confirm an unrelated company. **The fabricated-guess fallback was removed entirely** — if the tool can't confirm a real, published email with confidence, it now honestly says so and asks for manual entry, instead of presenting a guess as fact.

### 6. Wanting to search LinkedIn's actual job listings directly
I initially wanted the app to pull straight from LinkedIn's own jobs page.
**Reality check:** LinkedIn's job search requires a logged-in session, and automating that breaks their Terms of Service outright (real account-ban risk) — this isn't something any project can legitimately build around. Indeed, Naukri, and Internshala also don't offer public developer APIs to individuals.
**What I did instead:** Tightened the SerpAPI queries to target each platform's *individual posting* URL pattern specifically (`linkedin.com/jobs/view/...`, `indeed.com/viewjob`, `naukri.com/job-listings-...`) rather than their general jobs sections — the closest ToS-compliant equivalent of "search their real listings directly."

---

## Known limitations — being honest about what this can't do

- **Search quality depends on Google's index**, not a direct connection to each job board — so coverage isn't 100% complete, and very fresh postings may not be indexed yet.
- **The strict 24-hour filter can return zero results** for a specific role/skill combination at any given moment — this is the filter working as intended, not a bug, but it means fewer results than a looser search would show.
- **Recruiter email discovery only works when a company publishes an email publicly** on their own site. Many companies deliberately only expose an "Apply" button with no email at all — in that case, manual entry is required.
- **The "Company Verified" badge is a heuristic** (major job board + plausible business name), not a real verification service — don't treat it as a guarantee.
- **SerpAPI's free tier is capped at 250 searches/month** — each internship search uses up to 4 calls (one per platform), plus 1 more if the recruiter-email finder needs to look up a company's website.

---

## Future improvements

- Cross-verify recruiter emails with a second independent signal (e.g. the company's LinkedIn page) before auto-filling, for even higher confidence
- Auto-tailor the resume or cover note per role using the extracted job description
- Track which internships you've applied to, with follow-up reminders
- Expand beyond the current four platforms as new ToS-compliant sources become available
