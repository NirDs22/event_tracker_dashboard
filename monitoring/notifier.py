"""Email notification utilities."""
import os
import smtplib
from email.mime.text import MIMEText


def send_email(to_email: str, subject: str, body: str) -> bool:
    host = os.getenv('SMTP_HOST')
    user = os.getenv('SMTP_USER')
    password = os.getenv('SMTP_PASSWORD')
    port = int(os.getenv('SMTP_PORT', '587'))
    if not all([host, user, password, to_email]):
        print('Missing SMTP configuration or recipient')
        return False
    msg = MIMEText(body, 'html')
    msg['Subject'] = subject
    msg['From'] = user
    msg['To'] = to_email
    try:
        with smtplib.SMTP(host, port) as server:
            server.starttls()
            server.login(user, password)
            server.sendmail(user, [to_email], msg.as_string())
        return True
    except Exception as exc:
        print('Email sending failed', exc)
        return False
