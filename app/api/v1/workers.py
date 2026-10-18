from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import User, WorkerProfile, Entitlement, EntitlementType
from app.schemas import WorkerProfileResponse, WorkerProfileUpdate, EntitlementOut, AccessStatusResponse, PaymentOut
from app.core.permissions import get_current_user
from app.services.audit import log_audit_event
from app.core.config import settings

router = APIRouter(prefix="/workers/me", tags=["Worker Profile & Access"])

def check_worker_activated(user_id, db: Session) -> bool:
    return (
        db.query(Entitlement)
        .filter(
            Entitlement.user_id == user_id,
            Entitlement.entitlement_type == EntitlementType.PLATFORM_ACCESS,
            Entitlement.revoked_at.is_(None)
        )
        .first()
        is not None
    )

@router.get("", response_model=WorkerProfileResponse)
def get_my_profile(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    profile = current_user.profile
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Worker profile not found.")

    is_activated = check_worker_activated(current_user.id, db)

    return WorkerProfileResponse(
        user_id=current_user.id,
        phone=current_user.phone,
        email=current_user.email,
        role=current_user.role,
        status=current_user.status,
        full_name=profile.full_name,
        trade=profile.trade,
        preferred_country=profile.preferred_country,
        is_activated=is_activated,
        phone_verified_at=current_user.phone_verified_at,
        created_at=profile.created_at
    )

@router.patch("", response_model=WorkerProfileResponse)
def update_my_profile(
    req: WorkerProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    profile = current_user.profile
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Worker profile not found.")

    if req.full_name is not None:
        profile.full_name = req.full_name.strip()
    if req.trade is not None:
        profile.trade = req.trade.strip()
    if req.preferred_country is not None:
        profile.preferred_country = req.preferred_country.strip()
    if req.email is not None:
        current_user.email = req.email.lower()

    db.commit()

    log_audit_event(
        db=db,
        action="worker.profile_updated",
        target_type="worker_profile",
        target_id=str(current_user.id),
        actor_user_id=current_user.id
    )

    is_activated = check_worker_activated(current_user.id, db)

    return WorkerProfileResponse(
        user_id=current_user.id,
        phone=current_user.phone,
        email=current_user.email,
        role=current_user.role,
        status=current_user.status,
        full_name=profile.full_name,
        trade=profile.trade,
        preferred_country=profile.preferred_country,
        is_activated=is_activated,
        phone_verified_at=current_user.phone_verified_at,
        created_at=profile.created_at
    )

@router.get("/entitlements", response_model=List[EntitlementOut])
def list_my_entitlements(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    entitlements = db.query(Entitlement).filter(Entitlement.user_id == current_user.id).all()
    results = []
    for ent in entitlements:
        is_active = ent.revoked_at is None
        results.append(
            EntitlementOut(
                id=ent.id,
                user_id=ent.user_id,
                entitlement_type=ent.entitlement_type,
                granted_at=ent.granted_at,
                expires_at=ent.expires_at,
                is_active=is_active
            )
        )
    return results

@router.get("/access", response_model=AccessStatusResponse)
def get_my_access(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    entitlements = db.query(Entitlement).filter(Entitlement.user_id == current_user.id).all()
    is_activated = any(e.revoked_at is None for e in entitlements)

    latest_payment = (
        current_user.payments[-1] if current_user.payments else None
    )

    ent_outs = [
        EntitlementOut(
            id=e.id,
            user_id=e.user_id,
            entitlement_type=e.entitlement_type,
            granted_at=e.granted_at,
            expires_at=e.expires_at,
            is_active=(e.revoked_at is None)
        ) for e in entitlements
    ]

    return AccessStatusResponse(
        is_activated=is_activated,
        entitlements=ent_outs,
        latest_payment=PaymentOut.model_validate(latest_payment) if latest_payment else None,
        fee_amount=settings.PLATFORM_ACCESS_FEE_MINOR,
        currency=settings.PLATFORM_ACCESS_CURRENCY
    )

