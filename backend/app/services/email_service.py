import aiosmtplib
from email.message import EmailMessage
from app.settings import settings
import re
from typing import Optional


class EmailService:
    def __init__(self):
        self.smtp_host = settings.SMTP_HOST
        self.smtp_port = settings.SMTP_PORT
        self.smtp_user = settings.SMTP_USERNAME
        self.smtp_pass = settings.SMTP_PASSWORD
        self.email_from = settings.EMAIL_FROM

    async def send(
        self,
        to: str,
        subject: str,
        html_content: str,
        plain_content: Optional[str] = None
    ) -> bool:
        """
        Send an email with HTML and optional plain text content.
        """
        msg = EmailMessage()
        msg["From"] = self.email_from
        msg["To"] = to
        msg["Subject"] = subject

        # Auto-generate plain text if not provided
        if not plain_content:
            plain_content = self._html_to_plain(html_content)

        msg.set_content(plain_content)
        msg.add_alternative(html_content, subtype="html")

        await aiosmtplib.send(
            msg,
            hostname=self.smtp_host,
            port=self.smtp_port,
            username=self.smtp_user,
            password=self.smtp_pass,
            start_tls=True,
        )
        return True

    @staticmethod
    def _html_to_plain(html: str) -> str:
        """Convert HTML to plain text by stripping tags."""
        return re.sub("<[^<]+?>", "", html)

    @staticmethod
    def build_html_email(title: str, body: str, footer: Optional[str] = None) -> str:
        """Return a nicely formatted HTML email with inline styles."""
        footer = footer or "© 2025 BH Assurance. All rights reserved."
        html_template = f"""
        <html>
          <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: auto; padding: 20px; border: 1px solid #e2e2e2; border-radius: 8px;">
              <h2 style="color: #2F4F4F;">{title}</h2>
              <p>{body}</p>
              <hr style="border: none; border-top: 1px solid #e2e2e2;">
              <p style="font-size: 12px; color: #888;">{footer}</p>
            </div>
          </body>
        </html>
        """
        return html_template

    @staticmethod
    def adapt_pitch_for_email(pitch: dict) -> str:
        """
        Adapt a pitch dict into an email-ready HTML string.
        """
        client_name = pitch.get("client", "Client")
        text = pitch.get("pitch", "Pas de pitch disponible.")
        footer = "Cordialement,<br>Votre assistant commercial à BH"
        return f"Bonjour {client_name},<br><br>{text}<br><br>{footer}"
