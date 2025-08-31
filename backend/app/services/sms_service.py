from twilio.rest import Client
from app.settings import settings

class SMSService:
    def __init__(self):
        account_sid = settings.TWILIO_ACCOUNT_SID
        auth_token = settings.TWILIO_AUTH_TOKEN
        self.client = Client(account_sid, auth_token)

    def send_sms(self, to: str, body: str):
        message = self.client.messages.create(
            from_=settings.TWILIO_SMS_FROM,
            body=body,
            to=to
        )
        return message.sid
