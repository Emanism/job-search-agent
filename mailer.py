"""
Emails a summary of job matches above a score threshold, using Gmail's
SMTP server with an "app password" (not your normal Gmail password —
see README.md for how to create one).
"""

import smtplib
from email.message import EmailMessage

SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587


def _format_email_body(jobs):
    lines = []
    for job in jobs:
        lines.append(f"[{job['score']}] {job['title']}")
        lines.append(f"Company:  {job['company']}")
        lines.append(f"Location: {job['location']}")
        lines.append(f"Reason:   {job['reason']}")
        if job["gaps"]:
            lines.append(f"Gaps:     {job['gaps']}")
        lines.append(f"Apply:    {job['link']}")
        lines.append("")  # blank line between jobs
    return "\n".join(lines)


def send_match_email(jobs, threshold, gmail_address, gmail_app_password, to_address=None):
    """
    Email the jobs scoring >= threshold, sorted best-first.
    Sends nothing (and prints why) if credentials are missing or no job
    clears the threshold.
    """
    if not gmail_address or not gmail_app_password:
        print("[Email] Skipped: GMAIL_ADDRESS / GMAIL_APP_PASSWORD not set in .env")
        return

    matches = [job for job in jobs if job["score"] >= threshold]
    matches.sort(key=lambda job: job["score"], reverse=True)

    if not matches:
        print(f"[Email] No jobs scored {threshold} or higher — nothing to send.")
        return

    message = EmailMessage()
    plural = "es" if len(matches) != 1 else ""
    message["Subject"] = f"{len(matches)} job match{plural} (score >= {threshold})"
    message["From"] = gmail_address
    message["To"] = to_address or gmail_address
    message.set_content(_format_email_body(matches))

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as smtp:
        smtp.starttls()
        smtp.login(gmail_address, gmail_app_password)
        smtp.send_message(message)

    print(f"[Email] Sent {len(matches)} match(es) to {message['To']}")
