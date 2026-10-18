import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session

from app.models import OtpChallenge
from app.core.config import settings

class OtpService:
    @staticmethod
    def generate_code() -> str:
        # In mock or testing, generate 6 digits
        return f"{secrets.randbelow(900000) + 100000}"

    @staticmethod
    def hash_code(code: str) -> str:
        return hashlib.sha256(code.encode("utf-8")).hexdigest()

    @classmethod
    def create_challenge(cls, db: Session, phone: str) -> str:
        code = cls.generate_code()
        code_hash = cls.hash_code(code)
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.OTP_EXPIRY_MINUTES)

        challenge = OtpChallenge(
            phone=phone,
            code_hash=code_hash,
            expires_at=expires_at,
            attempts=0,
            max_attempts=3
        )
        db.add(challenge)
        db.commit()
        db.refresh(challenge)

        # In a live SMS environment, dispatch SMS via provider.
        # In mock environment, log it safely or make it retrievable for test.
        return code

    @classmethod
    def verify_code(cls, db: Session, phone: str, code: str) -> bool:
        now = datetime.now(timezone.utc)
        challenge = (
            db.query(OtpChallenge)
            .filter(
                OtpChallenge.phone == phone,
                OtpChallenge.consumed_at.is_(None),
                OtpChallenge.expires_at > now
            )
            .order_by(OtpChallenge.created_at.desc())
            .first()
        )

        if not challenge:
            return False

        if challenge.attempts >= challenge.max_attempts:
            return False

        challenge.attempts += 1
        code_hash = cls.hash_code(code.strip())

        if challenge.code_hash == code_hash:
            challenge.consumed_at = now
            db.commit()
            return True

        db.commit()
        return False

