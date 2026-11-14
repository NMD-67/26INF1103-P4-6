"""Send OTP email with a bounded timeout and injectable configuration."""
import asyncio
import logging
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

logger = logging.getLogger(__name__)


class EmailSender:
    def __init__(self, address="sitogether26@gmail.com", timeout=30):
        self._address = address
        self._timeout = timeout

    async def send(self, to_email, subject, html_content):
        # SMTP is blocking; keep it off the Telegram/async event loop.
        return await asyncio.to_thread(self._send, to_email, subject, html_content)

    def _send(self, to_email, subject, html_content):
        password = os.getenv("EMAIL_PASSWORD")
        if not password:
            logger.error("EMAIL_PASSWORD is not configured")
            return 500
        msg = MIMEMultipart()
        msg["From"] = self._address
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.attach(MIMEText(html_content, "html"))
        try:
            with smtplib.SMTP("smtp.gmail.com", 587, timeout=self._timeout) as server:
                server.starttls()
                server.login(self._address, password)
                server.send_message(msg)
            return 200
        except Exception as error:
            # Do not log message content, OTPs or credentials.
            logger.error("Email delivery failed: %s", type(error).__name__)
            return 500
