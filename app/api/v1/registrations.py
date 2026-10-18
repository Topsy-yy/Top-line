from typing import Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import User, WorkerProfile, UserRole, UserStatus
from app.schemas import RegistrationRequest, RegistrationResponse
from app.core.phone import normalize_phone
from app.core.security import hash_password
from app.services.otp import OtpService
from app.services.audit import log_audit_event
from app.core.config import settings

router = APIRouter(prefix="/registrations", tags=["Registration"])

@router.post("", response_model=RegistrationResponse, status_code=status.HTTP_201_CREATED)
def register_worker(req: RegistrationRequest, db: Session = Depends(get_db)):
    normalized_phone = normalize_phone(req.phone)

    # Check if phone is already registered
    existing_user = db.query(User).filter(User.phone == normalized_phone).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this phone number is already registered. Please log in or verify your account."
        )

    # Check email uniqueness if provided
    if req.email:
        existing_email = db.query(User).filter(User.email == req.email.lower()).first()
        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A user with this email is already registered."
            )

    # Hash password if provided
    password_hash = hash_password(req.password) if req.password else None

    # CRITICAL: Always enforce Worker role - prevent role escalation
    user = User(
        phone=normalized_phone,
        email=req.email.lower() if req.email else None,
        password_hash=password_hash,
        role=UserRole.WORKER,
        status=UserStatus.PENDING_VERIFICATION
    )
    db.add(user)
    db.flush()

    profile = WorkerProfile(
        user_id=user.id,
        full_name=req.full_name.strip(),
        trade=req.trade.strip(),
        preferred_country=req.preferred_country.strip()
    )
    db.add(profile)
    db.commit()

    # Generate OTP Challenge
    otp_code = OtpService.create_challenge(db, normalized_phone)

    log_audit_event(
        db=db,
        action="worker.registered",
        target_type="user",
        target_id=str(user.id),
        actor_user_id=user.id,
        metadata_json={"phone": normalized_phone, "trade": req.trade}
    )

    # In mock/dev environment, return mock_otp so frontend can demonstrate seamless OTP completion
    mock_otp = otp_code if settings.OTP_PROVIDER == "mock" else None

    return RegistrationResponse(
        user_id=user.id,
        phone=normalized_phone,
        message="Registration successful. Please verify your phone number with the OTP code sent.",
        phone_verified=False,
        mock_otp=mock_otp
    )

