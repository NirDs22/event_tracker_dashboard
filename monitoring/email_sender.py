"""
Email sending utility with Gmail SMTP primary and Brevo fallback.
"""

import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional, List, Dict, Any
from monitoring.secrets import get_secret

# Set up logging
logger = logging.getLogger(__name__)

def send_email_gmail_smtp(
    to_emails: List[str],
    subject: str,
    html_content: str,
    text_content: Optional[str] = None,
    from_name: Optional[str] = None
) -> bool:
    """
    Send email using Gmail SMTP.
    
    Args:
        to_emails: List of recipient email addresses
        subject: Email subject
        html_content: HTML content of the email
        text_content: Optional plain text content
        from_name: Optional sender name (defaults to "Event Tracker")
    
    Returns:
        True if email sent successfully, False otherwise
    """
    try:
        # Get Gmail SMTP credentials
        smtp_host = get_secret('EMAIL_HOST')
        smtp_port = int(get_secret('EMAIL_PORT', 587))
        smtp_user = get_secret('EMAIL_USER')
        smtp_pass = get_secret('EMAIL_PASS')
        
        if not all([smtp_host, smtp_user, smtp_pass]):
            logger.error("Gmail SMTP credentials not configured")
            return False
        
        # Set default from name
        if not from_name:
            from_name = "Event Tracker"
        
        # Create message
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = f"{from_name} <{smtp_user}>"
        msg['To'] = ", ".join(to_emails)
        
        # Add text content if provided
        if text_content:
            text_part = MIMEText(text_content, 'plain')
            msg.attach(text_part)
        
        # Add HTML content
        html_part = MIMEText(html_content, 'html')
        msg.attach(html_part)
        
        # Connect and send
        logger.info(f"Attempting to send email via Gmail SMTP to {len(to_emails)} recipients")
        
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.send_message(msg)
        
        logger.info(f"Email sent successfully via Gmail SMTP to: {', '.join(to_emails)}")
        return True
        
    except smtplib.SMTPAuthenticationError as e:
        logger.error(f"Gmail SMTP authentication failed: {e}")
        return False
    except smtplib.SMTPRecipientsRefused as e:
        logger.error(f"Gmail SMTP recipients refused: {e}")
        return False
    except smtplib.SMTPDataError as e:
        logger.error(f"Gmail SMTP data error: {e}")
        return False
    except Exception as e:
        logger.error(f"Gmail SMTP sending failed: {e}")
        return False


def send_email_brevo_fallback(
    to_emails: List[str],
    subject: str,
    html_content: str,
    from_name: Optional[str] = None
) -> bool:
    """
    Send email using Brevo API as fallback.
    
    Args:
        to_emails: List of recipient email addresses
        subject: Email subject
        html_content: HTML content of the email
        from_name: Optional sender name
    
    Returns:
        True if email sent successfully, False otherwise
    """
    try:
        import sib_api_v3_sdk
        from sib_api_v3_sdk.rest import ApiException
        
        api_key = get_secret('BREVO_API')
        from_email = get_secret('BREVO_FROM') or get_secret('EMAIL_USER') or 'noreply@yourdomain.com'
        if not from_name:
            from_name = get_secret('BREVO_FROM_NAME') or 'Event Tracker'
        
        if not api_key:
            logger.error('Brevo API key not configured')
            return False
        
        configuration = sib_api_v3_sdk.Configuration()
        configuration.api_key['api-key'] = api_key
        api_instance = sib_api_v3_sdk.TransactionalEmailsApi(sib_api_v3_sdk.ApiClient(configuration))
        
        # Convert email list to Brevo format
        recipients = [{"email": email} for email in to_emails]
        
        send_smtp_email = sib_api_v3_sdk.SendSmtpEmail(
            to=recipients,
            sender={"name": from_name, "email": from_email},
            subject=subject,
            html_content=html_content
        )
        
        response = api_instance.send_transac_email(send_smtp_email)
        logger.info(f"Email sent successfully via Brevo API to: {', '.join(to_emails)}")
        return True
        
    except ApiException as e:
        if hasattr(e, 'status') and 200 <= e.status < 300:
            logger.info(f"Email sent via Brevo API with status: {e.status}")
            return True
        else:
            logger.error(f"Brevo API exception: {e}")
            return False
    except Exception as e:
        logger.error(f"Brevo fallback email sending failed: {e}")
        return False


def send_email(
    to_emails: List[str],
    subject: str,
    html_content: str,
    text_content: Optional[str] = None,
    from_name: Optional[str] = None,
    use_fallback: bool = True
) -> bool:
    """
    Send email with Gmail SMTP primary and optional Brevo fallback.
    
    Args:
        to_emails: List of recipient email addresses
        subject: Email subject
        html_content: HTML content of the email
        text_content: Optional plain text content
        from_name: Optional sender name
        use_fallback: Whether to use Brevo fallback if Gmail fails
    
    Returns:
        True if email sent successfully (via either method), False otherwise
    """
    # Ensure to_emails is a list
    if isinstance(to_emails, str):
        to_emails = [to_emails]
    
    # Try Gmail SMTP first
    logger.info(f"Attempting to send email: '{subject}' to {len(to_emails)} recipients")
    
    if send_email_gmail_smtp(to_emails, subject, html_content, text_content, from_name):
        return True
    
    # If Gmail fails and fallback is enabled, try Brevo
    if use_fallback:
        logger.warning("Gmail SMTP failed, attempting Brevo fallback")
        return send_email_brevo_fallback(to_emails, subject, html_content, from_name)
    
    logger.error("Email sending failed completely")
    return False


def send_otp_email(to_email: str, code: str) -> bool:
    """
    Send an OTP code email for authentication.
    
    Args:
        to_email: Recipient email address
        code: 6-digit OTP code
    
    Returns:
        True if email sent successfully, False otherwise
    """
    subject = "Your Event Tracker Sign-In Code"
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>Sign-In Code</title>
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; 
                   line-height: 1.6; color: #333; max-width: 500px; margin: 0 auto; padding: 20px; }}
            .header {{ text-align: center; margin-bottom: 30px; }}
            .code-box {{ background: #f8f9fa; border: 2px solid #007AFF; border-radius: 12px; 
                        padding: 30px; text-align: center; margin: 30px 0; }}
            .code {{ font-size: 32px; font-weight: bold; letter-spacing: 8px; color: #007AFF; 
                    font-family: monospace; }}
            .footer {{ text-align: center; margin-top: 30px; color: #666; font-size: 14px; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>🔐 Sign-In Code</h1>
            <p>Use this code to sign in to your Event Tracker dashboard:</p>
        </div>
        
        <div class="code-box">
            <div class="code">{code}</div>
            <p style="margin-top: 20px; color: #666;">This code expires in 10 minutes</p>
        </div>
        
        <div class="footer">
            <p>If you didn't request this code, please ignore this email.</p>
            <p>Event Tracker Dashboard</p>
        </div>
    </body>
    </html>
    """
    
    text_content = f"""
    Event Tracker Sign-In Code
    
    Your verification code is: {code}
    
    This code expires in 10 minutes.
    
    If you didn't request this code, please ignore this email.
    
    Event Tracker Dashboard
    """
    
    return send_email([to_email], subject, html_content, text_content, "Event Tracker")
