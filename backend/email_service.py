#!/usr/bin/env python3
"""
Email service for sending event digests and notifications
Supports multiple email providers (SendGrid, SMTP, etc.)
"""

import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional
import aiohttp
import asyncio
import html

# Email configuration
SMTP_HOST = os.environ.get("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", 587))
SMTP_USER = os.environ.get("SMTP_USER", "")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")
SMTP_FROM = os.environ.get("SMTP_FROM", "noreply@nocturne.events")

# SendGrid configuration (alternative to SMTP)
SENDGRID_API_KEY = os.environ.get("SENDGRID_API_KEY", "")
SENDGRID_FROM_EMAIL = os.environ.get("SENDGRID_FROM_EMAIL", "noreply@nocturne.events")

# Email template
def generate_email_template(city_name: str, events: list) -> str:
    """
    Generate HTML email template for weekly digest
    """
    events_html = ""
    
    for event in events:
        title = html.escape(event.get('title', 'Unknown Event'))
        date_val = html.escape(str(event.get('date', 'TBA')))
        time_val = html.escape(event.get('time', 'TBA'))
        location = html.escape(event.get('location', 'Location TBA'))
        
        desc = event.get('description', '')
        if len(desc) > 200:
            truncated = html.escape(desc[:200]) + "..."
        else:
            truncated = html.escape(desc)
        
        link = event.get('link')
        link_html = ''
        if link:
            escaped_link = html.escape(link)
            link_html = f'<a href="{escaped_link}" style="color: #ccff00; text-decoration: none; font-weight: bold;">VIEW EVENT →</a>'
        
        events_html += f"""
        <div style="border-left: 3px solid #ccff00; padding-left: 15px; margin-bottom: 20px;">
            <h3 style="margin: 0 0 5px 0; color: #ffffff; font-size: 18px;">{title}</h3>
            <p style="margin: 5px 0; color: #a1a1aa; font-size: 14px;">
                {date_val} @ {time_val}
            </p>
            <p style="margin: 5px 0; color: #a1a1aa; font-size: 14px;">
                {location}
            </p>
            <p style="margin: 10px 0 0 0; color: #d4d4d8; font-size: 14px; line-height: 1.5;">
                {truncated}
            </p>
            {link_html}
        </div>
        """
    
    html_template = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body {{
                font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                background-color: #09090b;
                color: #f4f4f5;
                margin: 0;
                padding: 20px;
            }}
            .container {{
                max-width: 600px;
                margin: 0 auto;
                background-color: #18181b;
                border-radius: 8px;
                overflow: hidden;
            }}
            .header {{
                background-color: #09090b;
                padding: 30px;
                text-align: center;
                border-bottom: 2px solid #ccff00;
            }}
            .header h1 {{
                margin: 0;
                color: #ccff00;
                font-size: 32px;
                font-weight: 900;
                letter-spacing: -1px;
            }}
            .content {{
                padding: 30px;
            }}
            .footer {{
                background-color: #09090b;
                padding: 20px;
                text-align: center;
                font-size: 12px;
                color: #71717a;
            }}
            .footer a {{
                color: #ccff00;
                text-decoration: none;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>NOCTURNE /// {city_name}</h1>
            </div>
            <div class="content">
                <p style="font-size: 14px; color: #a1a1aa; margin-bottom: 30px;">
                    Your weekly dose of underground events. Stay in the loop.
                </p>
                {events_html}
            </div>
            <div class="footer">
                <p>
                    You're receiving this because you subscribed to Nocturne events in {city_name}.<br/>
                    <a href="#">Unsubscribe</a> | <a href="#">Manage Preferences</a>
                </p>
            </div>
        </div>
    </body>
    </html>
    """
    
    return html_template


async def send_email_via_smtp(
    to_email: str,
    subject: str,
    html_content: str
) -> bool:
    """
    Send email using SMTP
    """
    if not SMTP_USER or not SMTP_PASSWORD:
        print("SMTP credentials not configured, skipping email send")
        return False
    
    try:
        msg = MIMEMultipart('alternative')
        msg['From'] = SMTP_FROM
        msg['To'] = to_email
        msg['Subject'] = subject
        
        # Attach HTML content
        msg.attach(MIMEText(html_content, 'html'))
        
        # Send email (in a thread pool to avoid blocking)
        def _send_sync():
            with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
                server.starttls()
                server.login(SMTP_USER, SMTP_PASSWORD)
                server.send_message(msg)
        
        # Run in executor to avoid blocking
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, _send_sync)
        
        return True
        
    except Exception as e:
        print(f"Error sending email via SMTP: {e}")
        return False


async def send_email_via_sendgrid(
    to_email: str,
    subject: str,
    html_content: str
) -> bool:
    """
    Send email using SendGrid API
    """
    if not SENDGRID_API_KEY:
        print("SendGrid API key not configured, skipping email send")
        return False
    
    try:
        url = "https://api.sendgrid.com/v3/mail/send"
        headers = {
            "Authorization": f"Bearer {SENDGRID_API_KEY}",
            "Content-Type": "application/json"
        }
        
        data = {
            "personalizations": [
                {
                    "to": [{"email": to_email}],
                    "subject": subject
                }
            ],
            "from": {"email": SENDGRID_FROM_EMAIL},
            "content": [
                {
                    "type": "text/html",
                    "value": html_content
                }
            ]
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=data) as response:
                if response.status in [200, 202]:
                    return True
                else:
                    error_text = await response.text()
                    print(f"SendGrid error: {response.status} - {error_text}")
                    return False
                    
    except Exception as e:
        print(f"Error sending email via SendGrid: {e}")
        return False


async def send_email(
    to_email: str,
    subject: str,
    html_content: str,
    prefer_sendgrid: bool = False
) -> bool:
    """
    Send email using the best available method
    
    Args:
        to_email: Recipient email address
        subject: Email subject
        html_content: HTML content of the email
        prefer_sendgrid: If True, try SendGrid first, otherwise try SMTP first
    
    Returns:
        True if email sent successfully, False otherwise
    """
    # Determine which method to try first
    if prefer_sendgrid and SENDGRID_API_KEY:
        success = await send_email_via_sendgrid(to_email, subject, html_content)
        if success:
            return True
        # Fallback to SMTP
        return await send_email_via_smtp(to_email, subject, html_content)
    elif SMTP_USER and SMTP_PASSWORD:
        success = await send_email_via_smtp(to_email, subject, html_content)
        if success:
            return True
        # Fallback to SendGrid
        return await send_email_via_sendgrid(to_email, subject, html_content)
    elif SENDGRID_API_KEY:
        return await send_email_via_sendgrid(to_email, subject, html_content)
    else:
        print("No email service configured (SMTP or SendGrid)")
        return False


async def send_subscription_confirmation(email: str, city_name: str, city: str) -> bool:
    """
    Send confirmation email when user subscribes
    
    Args:
        email: User's email address
        city_name: Name of the city
        city: City ID for unsubscribe link
    
    Returns:
        True if email sent successfully
    """
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body {{
                font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                background-color: #09090b;
                color: #f4f4f5;
                margin: 0;
                padding: 20px;
            }}
            .container {{
                max-width: 600px;
                margin: 0 auto;
                background-color: #18181b;
                border-radius: 8px;
                overflow: hidden;
            }}
            .header {{
                background-color: #09090b;
                padding: 30px;
                text-align: center;
                border-bottom: 2px solid #ccff00;
            }}
            .content {{
                padding: 30px;
            }}
            .button {{
                display: inline-block;
                background-color: #ccff00;
                color: #09090b;
                text-decoration: none;
                padding: 12px 24px;
                border-radius: 4px;
                font-weight: bold;
                margin-top: 20px;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1 style="margin: 0; color: #ccff00; font-size: 32px; font-weight: 900;">NOCTURNE</h1>
            </div>
            <div class="content">
                <h2 style="color: #ffffff;">You're in the network.</h2>
                <p style="color: #a1a1aa; line-height: 1.6;">
                    You've successfully subscribed to receive weekly event updates for <strong>{city_name}</strong>.
                </p>
                <p style="color: #a1a1aa; line-height: 1.6;">
                    We'll send you a curated digest of the best underground events every week. No spam, just signal.
                </p>
                <p style="color: #a1a1aa; line-height: 1.6; font-size: 14px;">
                    Want to unsubscribe? You can do so from any email we send you.
                </p>
            </div>
        </div>
    </body>
    </html>
    """
    
    return await send_email(
        to_email=email,
        subject=f"Welcome to Nocturne /// {city_name}",
        html_content=html_content
    )


async def send_unsubscribe_confirmation(email: str, city_name: str) -> bool:
    """
    Send confirmation email when user unsubscribes
    
    Args:
        email: User's email address
        city_name: Name of the city
    
    Returns:
        True if email sent successfully
    """
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body {{
                font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                background-color: #09090b;
                color: #f4f4f5;
                margin: 0;
                padding: 20px;
            }}
            .container {{
                max-width: 600px;
                margin: 0 auto;
                background-color: #18181b;
                border-radius: 8px;
                overflow: hidden;
            }}
        </style>
    </head>
    <body>
        <div class="container" style="padding: 30px;">
            <h2 style="color: #ffffff;">You've been disconnected.</h2>
            <p style="color: #a1a1aa; line-height: 1.6;">
                You've successfully unsubscribed from event updates for <strong>{city_name}</strong>.
            </p>
            <p style="color: #a1a1aa; line-height: 1.6;">
                If you change your mind, you can always resubscribe on our website.
            </p>
        </div>
    </body>
    </html>
    """
    
    return await send_email(
        to_email=email,
        subject=f"Unsubscribed from {city_name}",
        html_content=html_content
    )


if __name__ == "__main__":
    # Test email sending
    import sys
    test_email = sys.argv[1] if len(sys.argv) > 1 else "test@example.com"
    
    async def test():
        success = await send_subscription_confirmation(test_email, "LOS ANGELES", "ca--los-angeles")
        print(f"Email sent: {success}")
    
    asyncio.run(test())
