
"""Email notification utilities using Gmail SMTP with Brevo fallback."""
import os
import logging
from datetime import datetime
from monitoring.secrets import get_secret

logger = logging.getLogger(__name__)

def send_email(to_email: str, subject: str, body: str, body_type: str = 'html') -> bool:
    """
    Send an email using Gmail SMTP with Brevo fallback.
    Args:
        to_email: Recipient email address
        subject: Email subject line
        body: Email body content
        body_type: 'html' or 'plain' for email format
    Returns:
        True if email sent successfully, False only for real errors
    """
    from monitoring.email_sender import send_email as send_email_new
    
    # --- Prevent sending if last email was sent less than 1 hour ago ---
    import time
    import pathlib
    last_sent_file = pathlib.Path(".last_digest_sent")
    now_ts = int(time.time())
    last_sent_ts = None
    if last_sent_file.exists():
        try:
            last_sent_ts = int(last_sent_file.read_text().strip())
        except Exception:
            last_sent_ts = None
    if last_sent_ts and (now_ts - last_sent_ts) < 3600:
        logger.warning("Digest email was sent less than an hour ago. Aborting send.")
        print("[DEBUG] Digest email was sent less than an hour ago. Aborting send.")
        return False
    
    # Set subject to Tracker Dashboard - Daily Digest (date)
    today_str = datetime.now().strftime('%B %d, %Y')
    subject_final = f"Tracker Dashboard - Daily Digest ({today_str})"
    
    # Prepare content based on type
    html_content = body if body_type == 'html' else None
    text_content = body if body_type != 'html' else None
    
    # Use the new Gmail SMTP + Brevo fallback system
    success = send_email_new(
        to_emails=[to_email], 
        subject=subject_final,
        html_content=html_content or body,
        text_content=text_content,
        from_name="Dashboard"
    )
    
    if success:
        # Write the last sent timestamp
        try:
            last_sent_file.write_text(str(now_ts))
        except Exception as e:
            logger.warning(f"Could not write last sent timestamp: {e}")
        
        logger.info(f"Email sent successfully to {to_email}")
        print(f"[DEBUG] Email sent successfully to {to_email}")
        return True
    else:
        logger.error(f"Failed to send email to {to_email}")
        print(f"[DEBUG] Failed to send email to {to_email}")
        return False


def send_otp_email(to_email: str, code: str) -> bool:
    """
    Send an OTP code email using Gmail SMTP with Brevo fallback.
    Args:
        to_email: Recipient email address
        code: 6-digit OTP code
    Returns:
        True if email sent successfully, False otherwise
    """
    from monitoring.email_sender import send_otp_email as send_otp_via_email
    
    print(f"DEBUG: send_otp_email called with to_email='{to_email}', code='{code}'")
    
    # Clean and validate email
    to_email = str(to_email).strip().lower()
    if '@' not in to_email or '.' not in to_email:
        logger.error(f'Invalid email format for OTP: "{to_email}"')
        return False
    
    logger.info(f'Attempting to send OTP to: "{to_email}" with code: "{code}"')
    
    # Use the new Gmail SMTP + Brevo fallback system
    success = send_otp_via_email(to_email, code)
    
    if success:
        logger.info(f"OTP email sent successfully to {to_email}")
    else:
        logger.error(f"Failed to send OTP email to {to_email}")
    
    return success


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

    # Group posts by topic
    from collections import defaultdict
    topic_posts = defaultdict(list)
    for post in posts:
        topic = post.get('topic', 'General')
        topic_posts[topic].append(post)

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>What's New? | Your Fun Daily Digest</title>
        <style>
            body {{ font-family: 'Segoe UI', Arial, sans-serif; line-height: 1.7; color: #222; max-width: 700px; margin: 0 auto; padding: 24px; background: #f7f8fa; }}
            .header {{ background: linear-gradient(90deg, #ffb347 0%, #ffcc33 100%); color: #222; padding: 28px 20px 18px 20px; border-radius: 18px; text-align: center; margin-bottom: 28px; box-shadow: 0 4px 18px #ffe6a0; }}
            .header h1 {{ font-size: 2.2rem; margin: 0 0 0.5rem 0; letter-spacing: -0.01em; }}
            .header p {{ font-size: 1.1rem; margin: 0; }}
            .topic-title {{ font-size: 1.4rem; margin: 2.2rem 0 0.7rem 0; color: #ff9800; font-weight: 700; letter-spacing: -0.01em; }}
            .ai-summary {{ background: #fffbe6; border-left: 5px solid #ffb347; border-radius: 7px; padding: 1rem 1.2rem; margin-bottom: 1.1rem; font-size: 1.05rem; }}
            .new-links {{ background: #f0f7ff; border-left: 5px solid #2196f3; border-radius: 7px; padding: 0.8rem 1.1rem; margin-bottom: 1.1rem; }}
            .post-link {{ display: block; margin: 0.4rem 0 0.4rem 0.5rem; font-size: 1.01rem; color: #1976d2; text-decoration: none; }}
            .post-link:hover {{ text-decoration: underline; }}
            .nothing-new {{ color: #888; font-size: 1.08rem; margin-bottom: 1.2rem; }}
            .footer {{ text-align: center; margin-top: 38px; padding-top: 18px; border-top: 1px solid #eee; color: #666; font-size: 1.08rem; }}
            .dashboard-invite {{ background: #e3fcec; color: #1b5e20; border-radius: 8px; padding: 1.1rem 1.2rem; margin: 2.2rem 0 1.2rem 0; font-size: 1.13rem; font-weight: 600; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>🌞 What's New? Your Fun Daily Digest</h1>
            <p>{datetime.now().strftime('%A, %B %d, %Y')}</p>
        </div>
    """

    for topic, t_posts in topic_posts.items():
        html += f'<div class="topic-title">🔸 {topic}</div>'
        # AI summary for this topic
        ai_summary = None
        for post in t_posts:
            if post.get('ai_summary'):
                ai_summary = post['ai_summary']
                break
        if not ai_summary:
            # Try to generate a summary from content if available
            contents = [p.get('content','') for p in t_posts if p.get('content')]
            if contents:
                try:
                    from monitoring.summarizer import summarize
                    ai_summary = summarize(contents)
                except Exception:
                    ai_summary = None
        # Format AI summary with bullet points for each ' - '
        import re
        def format_bullets(text):
            if not text:
                return ''
            dash_re = re.compile(r'\s*([\-\u2013\u2014\u2015])\s+')  # hyphen, en-dash, em-dash, horizontal bar
            lines = []
            for line in text.splitlines():
                # Split at any dash type surrounded by spaces
                if dash_re.search(line):
                    parts = dash_re.split(line)
                    # parts alternates: [before, dash, after, dash, after...]
                    if parts[0].strip():
                        lines.append(f'<p>{parts[0].strip()}</p>')
                    for i in range(1, len(parts)-1, 2):
                        bullet = parts[i+1].strip()
                        if bullet:
                            lines.append(f'<li style="margin-bottom:0.3em;">{bullet}</li>')
                elif re.match(r'^[\-\u2013\u2014\u2015]\s+', line.strip()):
                    # Line starts with a dash
                    bullet = re.sub(r'^[\-\u2013\u2014\u2015]\s+', '', line.strip())
                    lines.append(f'<li style="margin-bottom:0.3em;">{bullet}</li>')
                elif line.strip():
                    lines.append(f'<p>{line.strip()}</p>')
            # Wrap bullets in <ul> if any
            bullets = [l for l in lines if l.startswith('<li')]
            if bullets:
                non_bullets = [l for l in lines if not l.startswith('<li')]
                return ''.join(non_bullets) + '<ul style="margin:0.5em 0 0.5em 1.2em;">' + ''.join(bullets) + '</ul>'
            return ''.join(lines)
        if ai_summary:
            html += f'<div class="ai-summary"><b>🤖 AI Summary:</b> {format_bullets(ai_summary)}</div>'
        # New links
        links = [p for p in t_posts if p.get('url')]
        if links:
            html += '<div class="new-links"><b>🆕 New Links:</b>'
            for p in links:
                url = p.get('url','#')
                # Prefer title, then content, then url as fallback
                title = p.get('title') or p.get('content') or url
                title = str(title).strip()
                if not title:
                    title = url
                # Truncate for display
                display = title[:80] + ('...' if len(title) > 80 else '')
                html += f'<a class="post-link" href="{url}" target="_blank">🔗 {display}</a>'
            html += '</div>'
        if not ai_summary and not links:
            html += '<div class="nothing-new">Nothing new for now...</div>'

    html += f'''
        <div class="dashboard-invite">
            🚀 Want more details? <a href="https://nird-tracker.streamlit.app" target="_blank" style="color:#00796b;text-decoration:underline;font-weight:700;">Check the dashboard for an in-depth look!</a>
        </div>
        <div class="footer">
            <p>This digest was automatically generated by your Social & News Monitoring Dashboard.</p>
            <p>To stop receiving these emails, update your topic settings or remove your email from the profiles field.</p>
        </div>
    </body>
    </html>
    '''
    return html
