"""Compatibility wrapper; the active OTP service uses EmailSender."""
from pathlib import Path
from dotenv import load_dotenv
from IO_Manager.email_sender import EmailSender


async def send_email(to_email, subject, html_content):
    load_dotenv(Path(__file__).resolve().parents[1] / ".env")
    return await EmailSender().send(to_email, subject, html_content)
