
"""Email notification utilities using Brevo (Sendinblue) API."""
import os
import logging
from datetime import datetime
import sib_api_v3_sdk
from sib_api_v3_sdk.rest import ApiException

logger = logging.getLogger(__name__)

def send_email(to_email: str, subject: str, body: str, body_type: str = 'html') -> bool:
    """
    Send an email using the Brevo transactional email API.
    Args:
        to_email: Recipient email address
        subject: Email subject line
        body: Email body content
        body_type: 'html' or 'plain' for email format
    Returns:
        True if email sent successfully, False otherwise
    """
    api_key = os.getenv('BREVO_API')
    from_email = os.getenv('BREVO_FROM') or 'noreply@yourdomain.com'
    from_name = os.getenv('BREVO_FROM_NAME') or 'Dashboard'
    if not api_key or not to_email:
        logger.error('Missing BREVO_API key or recipient email')
        print('[DEBUG] Missing BREVO_API key or recipient email')
        return False
    try:
        configuration = sib_api_v3_sdk.Configuration()
        configuration.api_key['api-key'] = api_key
        api_instance = sib_api_v3_sdk.TransactionalEmailsApi(sib_api_v3_sdk.ApiClient(configuration))
        send_smtp_email = sib_api_v3_sdk.SendSmtpEmail(
            to=[{"email": to_email}],
            sender={"name": from_name, "email": from_email},
            subject=subject,
            html_content=body if body_type == 'html' else None,
            text_content=body if body_type != 'html' else None
        )
        print(f"[DEBUG] Sending Brevo email: {send_smtp_email}")
        response = api_instance.send_transac_email(send_smtp_email)
        print(f"[DEBUG] Brevo response: {response}")
        if hasattr(response, 'messageId') or (isinstance(response, dict) and response.get('messageId')):
            logger.info(f"Email sent successfully to {to_email} via Brevo")
            print(f"[DEBUG] Email sent successfully to {to_email} via Brevo")
            return True
        else:
            logger.error(f"Brevo API error: {response}")
            print(f"[DEBUG] Brevo API error: {response}")
            return False
    except ApiException as e:
        logger.error(f"Brevo API exception: {e}")
        print(f"[DEBUG] Brevo API exception: {e}")
        return False
    except Exception as exc:
        logger.error(f"Brevo email sending failed: {exc}")
        import traceback
        print(f"[DEBUG] Exception: {exc}\n{traceback.format_exc()}")
        return False


def create_digest_html(topic_name: str, posts: list, summary: str) -> str:
    """
    Create an HTML email digest for a topic.
    
    Args:
        topic_name: Name of the monitored topic
        posts: List of post dictionaries with content, url, source, etc.
        summary: AI-generated summary of the posts
    
    Returns:
        HTML string for email body
    """
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>Daily Digest: {topic_name}</title>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background: linear-gradient(135deg, #667eea, #764ba2); color: white; padding: 20px; border-radius: 10px; text-align: center; margin-bottom: 20px; }}
            .summary {{ background: #f8f9fa; padding: 15px; border-left: 4px solid #667eea; border-radius: 5px; margin-bottom: 20px; }}
            .post {{ background: white; border: 1px solid #ddd; border-radius: 8px; margin: 10px 0; padding: 15px; }}
            .post-header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; }}
            .source-badge {{ padding: 4px 8px; border-radius: 12px; font-size: 12px; font-weight: bold; color: white; }}
            .reddit {{ background-color: #ff4500; }}
            .news {{ background-color: #0066cc; }}
            .instagram {{ background-color: #e4405f; }}
            .facebook {{ background-color: #1877f2; }}
            .photos {{ background-color: #28a745; }}
            .footer {{ text-align: center; margin-top: 30px; padding-top: 20px; border-top: 1px solid #ddd; color: #666; font-size: 12px; }}
            a {{ color: #667eea; text-decoration: none; }}
            a:hover {{ text-decoration: underline; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>📰 Daily Digest</h1>
            <h2>{topic_name}</h2>
            <p>{datetime.now().strftime('%B %d, %Y')}</p>
        </div>
        
        <div class="summary">
            <h3>🤖 AI Summary</h3>
            <p>{summary}</p>
        </div>
        
        <h3>📊 Recent Posts ({len(posts)})</h3>
    """
    
    for post in posts[:10]:  # Limit to 10 most recent posts
        content = post.get('content', '')[:200] + ('...' if len(post.get('content', '')) > 200 else '')
        source = post.get('source', 'unknown')
        url = post.get('url', '#')
        posted_at = post.get('posted_at', datetime.now())
        
        # Format the date
        if hasattr(posted_at, 'strftime'):
            date_str = posted_at.strftime('%m/%d %H:%M')
        else:
            date_str = str(posted_at)[:16]
        
        html += f"""
        <div class="post">
            <div class="post-header">
                <span class="source-badge {source}">{source.title()}</span>
                <small>{date_str}</small>
            </div>
            <p>{content}</p>
            <a href="{url}" target="_blank">🔗 Read more</a>
        </div>
        """
    
    html += f"""
        <div class="footer">
            <p>This digest was automatically generated by your Social & News Monitoring Dashboard.</p>
            <p>To stop receiving these emails, update your topic settings or remove your email from the profiles field.</p>
        </div>
    </body>
    </html>
    """
    
    return html
