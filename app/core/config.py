from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    APP_ENV: str = "development"
    SECRET_KEY: str = "change-this-in-production-use-a-secure-random-key-at-least-32-chars"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 120
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    DATABASE_URL: str = "postgresql://topline:topline_secret@127.0.0.1:5432/topline_dev"
    TEST_DATABASE_URL: str = "postgresql://topline:topline_secret@127.0.0.1:5432/topline_test"

    PLATFORM_ACCESS_FEE_MINOR: int = 100000  # KSh 1,000 in minor units (cents)
    PLATFORM_ACCESS_CURRENCY: str = "KES"

    DOCUMENT_STORAGE_DIR: str = "/home/topsy/Documents/topline/storage/documents"
    MAX_UPLOAD_SIZE_BYTES: int = 5 * 1024 * 1024  # 5 MB
    ALLOWED_DOCUMENT_MIME_TYPES: List[str] = [
        "application/pdf",
        "image/jpeg",
        "image/png",
        "application/msword",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    ]

    # M-Pesa Daraja
    MPESA_ENVIRONMENT: str = "sandbox"
    MPESA_CONSUMER_KEY: str = "placeholder_consumer_key"
    MPESA_CONSUMER_SECRET: str = "placeholder_consumer_secret"
    MPESA_SHORTCODE: str = "174379"
    MPESA_PASSKEY: str = "placeholder_passkey"
    MPESA_CALLBACK_URL: str = "http://127.0.0.1:8000/api/v1/payments/mpesa/callback"

    # OTP Provider: mock / real
    OTP_PROVIDER: str = "mock"
    OTP_EXPIRY_MINUTES: int = 10

settings = Settings()

