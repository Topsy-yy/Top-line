from typing import Optional
from uuid import UUID
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.security import decode_token
from app.models import User, UserRole, UserStatus, Entitlement, EntitlementType

security_bearer = HTTPBearer(auto_error=False)

def get_token_from_request(request: Request, creds: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer)) -> Optional[str]:
    # Check Bearer header first
    if creds and creds.credentials:
        return creds.credentials
    # Fallback to session cookie
    cookie_token = request.cookies.get("topline_token")
    if cookie_token:
        return cookie_token
    return None

def get_current_user(
    request: Request,
    token: Optional[str] = Depends(get_token_from_request),
    db: Session = Depends(get_db)
) -> User:
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please log in.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_token(token)
    if not payload or payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id_str = payload.get("sub")
    if not user_id_str:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token subject.")

    try:
        user_uuid = UUID(user_id_str)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token user ID.")

    user = db.query(User).filter(User.id == user_uuid).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User account not found.")

    if user.status == UserStatus.SUSPENDED:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="This account has been suspended.")

    return user

def require_role(*roles: UserRole):
    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to perform this administrative action."
            )
        return current_user
    return role_checker

def require_activated_worker(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> User:
    if current_user.role != UserRole.WORKER:
        # Admins can bypass or act on applications
        return current_user

    entitlement = (
        db.query(Entitlement)
        .filter(
            Entitlement.user_id == current_user.id,
            Entitlement.entitlement_type == EntitlementType.PLATFORM_ACCESS,
            Entitlement.revoked_at.is_(None)
        )
        .first()
    )

    if not entitlement:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Platform activation fee (KSh 1,000) required to access this feature."
        )

    return current_user

