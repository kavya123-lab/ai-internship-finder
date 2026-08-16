"""
Configuration for the AI Internship Finder web app.
Loads settings from environment variables (.env file).
"""
import os
from dataclasses import dataclass, field
from dotenv import load_dotenv

load_dotenv()


@dataclass
class Settings:
    # LLM used to extract structured internship data from raw search results.
    # Groq is used because it's free to start with and needs no payment method.
    groq_api_key: str = os.getenv("GROQ_API_KEY", "")
    groq_model: str = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

    # Search provider. Direct scraping of LinkedIn/Naukri/Indeed violates
    # their Terms of Service and is blocked by anti-bot systems, so we use
    # a search-engine API restricted with `site:` filters instead.
    serpapi_key: str = os.getenv("SERPAPI_KEY", "")

    # SMTP settings for sending application emails
    smtp_host: str = os.getenv("SMTP_HOST", "smtp.gmail.com")
    smtp_port: int = int(os.getenv("SMTP_PORT", "587"))
    smtp_user: str = os.getenv("SMTP_USER", "")
    smtp_password: str = os.getenv("SMTP_PASSWORD", "")

    # Required search priority order
    search_order: list = field(default_factory=lambda: [
        "linkedin.com/jobs",
        "internshala.com",
        "indeed.com",
        "naukri.com",
    ])

    max_results_per_source: int = 8


settings = Settings()
