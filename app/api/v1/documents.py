from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import ApplicationDocument, User
from app.core.permissions import get_current_user
from app.services.storage import document_storage
from app.services.audit import log_audit_event

router = APIRouter(prefix="/documents", tags=["Documents"])

@router.get("/{document_id}/download")
def download_document(
    document_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    doc = db.query(ApplicationDocument).filter(ApplicationDocument.id == document_id).first()
    if not doc or doc.deleted_at is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")

    application = doc.application
    # Strictly authorize access: worker who applied or administrator/reviewer
    if application.worker_id != current_user.id and current_user.role.value not in ["administrator", "reviewer"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")

    file_path = document_storage.get_document_path(doc.storage_key)

    log_audit_event(
        db=db,
        action="document.downloaded",
        target_type="application_document",
        target_id=str(doc.id),
        actor_user_id=current_user.id
    )

    return FileResponse(
        path=file_path,
        media_type=doc.content_type,
        filename=doc.original_filename
    )

