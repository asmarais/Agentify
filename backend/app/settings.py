from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USERNAME: str
    SMTP_PASSWORD: str
    EMAIL_FROM: str = "rais.asma99@gmail.com"
    TWILIO_ACCOUNT_SID: str
    TWILIO_AUTH_TOKEN: str
    TWILIO_WHATSAPP_FROM: str
    TWILIO_WHATSAPP_TO: str
    TWILIO_SMS_FROM: str
    TWILIO_SMS_TO: str
    """
    MONGO_URI: str
    DB_NAME: str
    COLLECTION_NAME: str
    OLLAMA_MODEL: str
    QUERY_PROMPT: str
    """
    model_config = SettingsConfigDict(
        env_file="../backend/.env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
