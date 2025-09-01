import sys
import os
import aiosmtplib
from email.message import EmailMessage
from app.settings import settings
import re
from typing import Optional
from langchain_core.prompts import ChatPromptTemplate, SystemMessagePromptTemplate, HumanMessagePromptTemplate
from datetime import datetime

# Add the root directory (Agentify) to the Python path
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
sys.path.insert(0, root_dir)
print(root_dir)

# Try the import (already included above, but kept for clarity)
try:
    from shared.database import GestionnaireBaseDonnees, StatutInteraction, TypeReponse, InteractionEmail, tester_connexion_postgresql
    print("Import from shared.database successful!")
except ImportError as e:
    print(f"Import failed: {e}")
    raise  # Re-raise to see the full traceback

class EmailService:
    def __init__(self):
        self.smtp_host = settings.SMTP_HOST
        self.smtp_port = settings.SMTP_PORT
        self.smtp_user = settings.SMTP_USERNAME
        self.smtp_pass = settings.SMTP_PASSWORD
        self.email_from = settings.EMAIL_FROM
        # Initialize database manager with configuration (assuming settings contains db config)
        self.db_config = {
            'host': settings.DB_HOST,
            'database': settings.DB_NAME,
            'user': settings.DB_USER,
            'password': settings.DB_PASSWORD,
            'port': settings.DB_PORT
        }
        self.db_manager = GestionnaireBaseDonnees(self.db_config)

    async def send(
        self,
        to: str,
        subject: str,
        html_content: str,
        plain_content: Optional[str] = None,
        conversation_id: str = None
    ) -> bool:
        """
        Send an email with HTML and optional plain text content, and save the interaction.
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

        # Save interaction to database
        interaction = InteractionEmail(
            email_id=msg["Message-ID"] if "Message-ID" in msg else str(hash(str(msg))),
            expediteur_email=self.email_from,
            sujet=subject,
            corps=plain_content,
            timestamp=datetime.now(),
            type_reponse=TypeReponse.EN_COURS,
            reponse_ia=html_content,
            conversation_id=conversation_id or str(hash(to + subject + str(datetime.now()))),
            statut=StatutInteraction.EN_COURS
        )
        self.db_manager.sauvegarder_interaction(interaction)

        return True

    @staticmethod
    def _html_to_plain(html: str) -> str:
        """Convert HTML to plain text by stripping tags."""
        return re.sub("<[^<]+?>", "", html)

    @staticmethod
    def build_html_email(title: str, body: str, footer: Optional[str] = None) -> str:
        """Return a nicely formatted HTML email with inline styles."""
        html_template = f"""
        <html>
          <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: auto; padding: 20px; border: 1px solid #e2e2e2; border-radius: 8px;">
              <p>Bonjour,<br>{body}</p>
              <br>
              <p>Choisissez votre réponse :</p>

                <a href="mailto:chatbot.bh01@gmail.com?subject=Refus&body=Je refuse"
                style="padding:10px 20px; margin:5px; background:#f44336; color:white; text-decoration:none; border-radius:5px; display:inline-block;">
                Je refuse
                </a>

                <a href="mailto:chatbot.bh01@gmail.com?subject=Interesse&body=Je suis intéressée"
                style="padding:10px 20px; margin:5px; background:#4CAF50; color:white; text-decoration:none; border-radius:5px; display:inline-block;">
                Je suis intéressée
                </a>

                <a href="mailto:chatbot.bh01@gmail.com?subject=Demande de devis&body=Je veux un devis"
                style="padding:10px 20px; margin:5px; background:#2196F3; color:white; text-decoration:none; border-radius:5px; display:inline-block;">
                Je veux un devis
                </a>

              <p>Cordialement,<br>Votre assistant commercial</p>
              <hr style="border: none; border-top: 1px solid #e2e2e2;">
              <br>© 2025 BH Assurance. All rights reserved.
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
