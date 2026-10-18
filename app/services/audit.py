from typing import Optional, Dict, Any
from uuid import UUID
from sqlalchemy.orm import Session
from app.models import AuditEvent

def log_audit_event(
    db: Session,
    action: str,
    target_type: str,
    target_id: Optional[str] = None,
    actor_user_id: Optional[UUID] = None,
    metadata_json: Optional[Dict[str, Any]] = None,
    request_id: Optional[str] = None
) -> AuditEvent:
    event = AuditEvent(
        actor_user_id=actor_user_id,
        action=action,
        target_type=target_type,
        target_id=str(target_id) if target_id else None,
        request_id=request_id,
        metadata_json=metadata_json or {}
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event

