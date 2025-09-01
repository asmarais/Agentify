from twilio.rest import Client
from app.settings import settings

class WhatsAppService:
    def __init__(self):
        account_sid = settings.TWILIO_ACCOUNT_SID
        auth_token = settings.TWILIO_AUTH_TOKEN
        self.client = Client(account_sid, auth_token)

    def send_message(self, to: str, body: str):
        # Ajout du message personnalisé
        customized_body = f"Bonjour,\n\n{body}\n\nPour plus d'information contacter nous via email: contact-bh@gmail.com"
        message = self.client.messages.create(
            from_=settings.TWILIO_WHATSAPP_FROM,
            body=customized_body,
            to=settings.TWILIO_WHATSAPP_TO
        )
        return message.sid