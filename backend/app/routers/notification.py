from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr
from app.settings import settings
from app.services.email_service import EmailService
from app.services.whatsapp_service import WhatsAppService
from app.services.sms_service import SMSService

router = APIRouter()

# ----- Request Models -----
class EmailIn(BaseModel):
    to: EmailStr
    subject: str
    body: str  
    plain: str | None = None

class WhatsAppMessage(BaseModel):
    to: str | None = None   
    body: str

class SMSMessage(BaseModel):
    to: str | None = None
    body: str


# ----- Email Endpoint -----
@router.post("/send-email")
async def send_email(payload: EmailIn):
    svc = EmailService()
    try:
        # Build formatted HTML email using the service helper
        html_content = EmailService.build_html_email(
            title=payload.subject,
            body=payload.body
        )
        await svc.send(
            to=payload.to,
            subject=payload.subject,
            html_content=html_content,
            plain_content=payload.plain
        )
        return {"ok": True, "to": payload.to}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ----- WhatsApp Endpoint -----
@router.post("/send-whatsapp")
def send_whatsapp(msg: WhatsAppMessage):
    whatsapp_service = WhatsAppService()
    sid = whatsapp_service.send_message(
        #to=msg.to
        to=settings.TWILIO_WHATSAPP_TO,
        body=msg.body
    )
    return {"status": "sent", "sid": sid}


# ----- SMS Endpoint -----
@router.post("/send-sms")
def send_sms(msg: SMSMessage):
    sms_service = SMSService()
    sid = sms_service.send_sms(
        #to=msg.to
        to=settings.TWILIO_SMS_TO,
        body=msg.body
    )
    return {"status": "sent", "sid": sid}
