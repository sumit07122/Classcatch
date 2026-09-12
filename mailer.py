"""
ClassCatch Institutional Email Delivery Service
Provides transactional emails for GLA University institutional account verification,
password resets, and official academic broadcast notices.
Supports standard SMTP (Gmail, SendGrid, Amazon SES, Brevo) and Resend HTTP API,
with a zero-configuration development fallback that logs to stdout/logger without failing.
"""
import os
import smtplib
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

logger = logging.getLogger('classcatch.mailer')


def is_mail_configured() -> bool:
    """Check if either SMTP or Resend API credentials are provided."""
    has_smtp = bool(os.environ.get('MAIL_SERVER') and os.environ.get('MAIL_USERNAME') and os.environ.get('MAIL_PASSWORD'))
    has_resend = bool(os.environ.get('RESEND_API_KEY'))
    return has_smtp or has_resend


def send_raw_email(to_email: str, subject: str, html_body: str, text_body: str = None) -> tuple[bool, str]:
    """
    Dispatches an email via Resend API or SMTP transport.
    Returns (success: bool, status_message: str).
    """
    sender = os.environ.get('MAIL_DEFAULT_SENDER', 'ClassCatch GLA <noreply@classcatch.edu>')

    # 1. Resend API Transport (if RESEND_API_KEY is configured)
    resend_key = os.environ.get('RESEND_API_KEY')
    if resend_key and resend_key.strip():
        try:
            import requests
            headers = {
                'Authorization': f'Bearer {resend_key.strip()}',
                'Content-Type': 'application/json'
            }
            payload = {
                'from': sender,
                'to': [to_email],
                'subject': subject,
                'html': html_body,
                'text': text_body or "Please view this email in an HTML-compatible client."
            }
            resp = requests.post('https://api.resend.com/emails', json=payload, headers=headers, timeout=10)
            if resp.status_code in (200, 201):
                logger.info(f"[Mailer] Sent email to {to_email} via Resend API")
                return True, f"Sent via Resend to {to_email}"
            else:
                logger.warning(f"[Mailer] Resend API error {resp.status_code}: {resp.text}")
        except Exception as e:
            logger.error(f"[Mailer] Resend API dispatch failed: {e}")

    # 2. SMTP Transport (if MAIL_SERVER is configured)
    mail_server = os.environ.get('MAIL_SERVER')
    mail_username = os.environ.get('MAIL_USERNAME')
    mail_password = os.environ.get('MAIL_PASSWORD')

    if mail_server and mail_username and mail_password:
        mail_port = int(os.environ.get('MAIL_PORT', 587))
        use_tls = os.environ.get('MAIL_USE_TLS', '1').lower() in ('1', 'true', 'yes')
        use_ssl = os.environ.get('MAIL_USE_SSL', '0').lower() in ('1', 'true', 'yes')

        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = sender
            msg['To'] = to_email

            if text_body:
                msg.attach(MIMEText(text_body, 'plain'))
            msg.attach(MIMEText(html_body, 'html'))

            if use_ssl:
                with smtplib.SMTP_SSL(mail_server, mail_port, timeout=12) as server:
                    server.login(mail_username, mail_password)
                    server.send_message(msg)
            else:
                with smtplib.SMTP(mail_server, mail_port, timeout=12) as server:
                    if use_tls:
                        server.starttls()
                    server.login(mail_username, mail_password)
                    server.send_message(msg)

            logger.info(f"[Mailer] Sent email to {to_email} via SMTP ({mail_server})")
            return True, f"Sent via SMTP to {to_email}"
        except Exception as e:
            logger.error(f"[Mailer] SMTP dispatch to {to_email} failed: {e}")
            return False, f"SMTP delivery error: {e}"

    # 3. Development / Testing Mock Transport (No server credentials configured)
    try:
        print(f"\n=======================================================")
        print(f"[EMAIL DISPATCH - DEV/TEST MODE]")
        print(f"To: {to_email}")
        print(f"Subject: {subject}")
        print(f"Body Preview:\n{(text_body or html_body)[:250]}...")
        print(f"=======================================================\n")
    except Exception:
        pass
    return True, f"Simulated delivery (Logged to console: {to_email})"


def send_verification_email(user, token: str, base_url: str) -> tuple[bool, str]:
    """
    Sends the official GLA University email verification notice with a 1-click activation link.
    """
    verification_link = f"{base_url.rstrip('/')}/verify-email/{token}"
    subject = "🎓 Verify your GLA University Email — ClassCatch"

    html_content = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f8fafc; margin: 0; padding: 0; }}
  .container {{ max-width: 580px; margin: 30px auto; background: #ffffff; border-radius: 12px; overflow: hidden; border: 1px solid #e2e8f0; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05); }}
  .header {{ background: linear-gradient(135deg, #1e40af 0%, #3b82f6 100%); color: #ffffff; padding: 28px 24px; text-align: center; }}
  .header h1 {{ margin: 0; font-size: 22px; font-weight: 700; }}
  .header p {{ margin: 6px 0 0; font-size: 13px; opacity: 0.9; }}
  .content {{ padding: 28px 24px; color: #334155; line-height: 1.6; font-size: 15px; }}
  .highlight {{ background: #eff6ff; border-left: 4px solid #3b82f6; padding: 12px 16px; margin: 18px 0; border-radius: 0 6px 6px 0; font-size: 14px; }}
  .btn-container {{ text-align: center; margin: 28px 0; }}
  .btn {{ display: inline-block; background: #2563eb; color: #ffffff !important; text-decoration: none; padding: 12px 28px; border-radius: 8px; font-weight: 600; font-size: 15px; box-shadow: 0 2px 4px rgba(37, 99, 235, 0.2); }}
  .footer {{ background: #f1f5f9; padding: 18px 24px; text-align: center; color: #64748b; font-size: 12px; border-top: 1px solid #e2e8f0; }}
  .url-box {{ word-break: break-all; font-family: monospace; font-size: 12px; color: #475569; background: #f8fafc; padding: 8px 12px; border-radius: 4px; border: 1px solid #cbd5e1; margin-top: 14px; }}
</style>
</head>
<body>
  <div class="container">
    <div class="header">
      <h1>🎓 GLA University · ClassCatch</h1>
      <p>Department of Computer Science & Engineering · Section 2FE</p>
    </div>
    <div class="content">
      <p>Hello <strong>{user.name}</strong>,</p>
      <p>Thank you for joining ClassCatch! To access your Section 2FE timetable, safe bunk predictions, and verified lecture notes, please confirm your official GLA institutional email address.</p>
      
      <div class="highlight">
        <strong>Institutional Account:</strong> {user.email}<br>
        <strong>Academic Program:</strong> B.Tech CSE (Lateral Entry, Sem 3)
      </div>

      <div class="btn-container">
        <a href="{verification_link}" class="btn" target="_blank">Verify GLA Email Address</a>
      </div>

      <p style="font-size: 13px; color: #64748b;">If the button above does not work, copy and paste this link into your browser:</p>
      <div class="url-box">{verification_link}</div>
      
      <p style="font-size: 12px; color: #94a3b8; margin-top: 24px;">If you did not register for ClassCatch, please ignore this email.</p>
    </div>
    <div class="footer">
      ClassCatch GLA Academic Operations · Mathura Campus, NH-19, Chaumuhan, Mathura, UP 281406
    </div>
  </div>
</body>
</html>"""

    text_content = f"""GLA University · ClassCatch
Verify Your Institutional Email

Hello {user.name},

Please verify your official GLA institutional email address ({user.email}) by visiting the link below:

{verification_link}

This activation link confirms your enrollment in Section 2FE (B.Tech CSE, Lateral Entry).

If you did not register for ClassCatch, please ignore this message.
GLA University, Mathura Campus.
"""
    return send_raw_email(user.email, subject, html_content, text_content)


def send_password_reset_email(user, token: str, base_url: str) -> tuple[bool, str]:
    """
    Sends a secure password reset link to the student's institutional email.
    """
    reset_link = f"{base_url.rstrip('/')}/reset-password/{token}"
    subject = "🔒 Password Reset Request — ClassCatch GLA"

    html_content = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f8fafc; margin: 0; padding: 0; }}
  .container {{ max-width: 580px; margin: 30px auto; background: #ffffff; border-radius: 12px; overflow: hidden; border: 1px solid #e2e8f0; }}
  .header {{ background: #1e293b; color: #ffffff; padding: 24px; text-align: center; }}
  .content {{ padding: 28px 24px; color: #334155; line-height: 1.6; }}
  .btn-container {{ text-align: center; margin: 24px 0; }}
  .btn {{ display: inline-block; background: #dc2626; color: #ffffff !important; text-decoration: none; padding: 12px 28px; border-radius: 8px; font-weight: 600; font-size: 15px; }}
  .footer {{ background: #f1f5f9; padding: 18px 24px; text-align: center; color: #64748b; font-size: 12px; }}
  .url-box {{ word-break: break-all; font-family: monospace; font-size: 12px; color: #475569; background: #f8fafc; padding: 8px 12px; border-radius: 4px; border: 1px solid #cbd5e1; margin-top: 12px; }}
</style>
</head>
<body>
  <div class="container">
    <div class="header">
      <h2 style="margin:0;">🔒 Password Reset Request</h2>
      <p style="margin:4px 0 0; font-size:13px; opacity:0.85;">ClassCatch GLA Institutional Platform</p>
    </div>
    <div class="content">
      <p>Hello <strong>{user.name}</strong>,</p>
      <p>We received a request to reset the password for your ClassCatch account (<strong>{user.email}</strong>).</p>
      <p>Click the button below to choose a new password. This link is valid for <strong>1 hour</strong>.</p>
      
      <div class="btn-container">
        <a href="{reset_link}" class="btn" target="_blank">Reset My Password</a>
      </div>

      <p style="font-size: 13px; color: #64748b;">Or copy this link into your browser:</p>
      <div class="url-box">{reset_link}</div>

      <p style="font-size: 12px; color: #94a3b8; margin-top: 24px;">If you did not request a password reset, you can safely ignore this email. Your password will remain unchanged.</p>
    </div>
    <div class="footer">
      GLA University Computer Science & Engineering · ClassCatch Security Team
    </div>
  </div>
</body>
</html>"""

    text_content = f"""ClassCatch GLA — Password Reset Request

Hello {user.name},

A password reset was requested for your account ({user.email}).
To reset your password, visit:

{reset_link}

This link is valid for 1 hour. If you did not request this, please ignore this email.
"""
    return send_raw_email(user.email, subject, html_content, text_content)
