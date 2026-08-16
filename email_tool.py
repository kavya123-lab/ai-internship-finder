"""
Builds and sends internship application emails, with the uploaded resume
attached, via SMTP. Used by the /api/apply endpoint — takes raw fields
straight from the web form instead of a file path.
"""
import smtplib
from email.message import EmailMessage
from typing import Optional
from config import settings

EMAIL_TEMPLATE = """Dear Hiring Team,

I hope you are doing well.

I am interested in applying for the {role} Internship position. I am currently pursuing a degree in Computer Science and have experience in technologies relevant to the role.

I have attached my resume for your review and would appreciate the opportunity to discuss my application further.

Thank you for your time and consideration.

Best Regards,
{name}
"""


def send_application_email(
    applicant_name: str,
    applicant_email: str,
    applicant_phone: str,
    linkedin_url: str,
    role: str,
    company: str,
    recruiter_email: str,
    resume_bytes: bytes,
    resume_filename: str,
    portfolio_url: Optional[str] = None,
) -> None:
    if not settings.smtp_user or not settings.smtp_password:
        raise RuntimeError("Email is not configured (SMTP_USER / SMTP_PASSWORD missing in .env)")
    if not recruiter_email:
        raise ValueError("A recruiter/company email is required to send the application")

    msg = EmailMessage()
    msg["Subject"] = f"Application for {role} Internship"
    msg["From"] = settings.smtp_user
    msg["To"] = recruiter_email
    msg["Reply-To"] = applicant_email

    body = EMAIL_TEMPLATE.format(role=role, name=applicant_name)
    body += f"\nPhone: {applicant_phone}\nLinkedIn: {linkedin_url}"
    if portfolio_url:
        body += f"\nPortfolio: {portfolio_url}"
    msg.set_content(body)

    msg.add_attachment(
        resume_bytes,
        maintype="application",
        subtype="octet-stream",
        filename=resume_filename,
    )

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
        server.starttls()
        server.login(settings.smtp_user, settings.smtp_password)
        server.send_message(msg)
