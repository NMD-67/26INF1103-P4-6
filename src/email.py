from dotenv import load_dotenv
from pathlib import Path
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(dotenv_path=BASE_DIR.parent / ".env")

EMAIL_ADRESS = "sitogether26@gmail.com"

async def send_email(to_email, subject, html_content):
  msg = MIMEMultipart()
  msg['From'] = EMAIL_ADRESS
  msg['To'] = to_email
  msg['Subject'] = subject
  msg.attach(MIMEText(html_content, 'html'))

  try:
    with smtplib.SMTP('smtp.gmail.com', 587) as server:
      server.starttls()
      server.login(EMAIL_ADRESS, os.environ.get("EMAIL_PASSWORD"))
      server.send_message(msg)
      return 200  # Email sent successfully
  except Exception as e:
    print(f"Error sending email: {e}")
    return 500  # Error occurred while sending email
    

