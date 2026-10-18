from typing import List, Optional
from uuid import UUID
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import (
    User, Job, JobStatus, JobApplication, ApplicationDocument,
    ApplicationStatus, DocumentScanStatus
)
from app.schemas import (
    ApplicationSubmitRequest, ApplicationOut, DocumentOut,
    ApplicationStatusUpdate, StatusResponse
)
from app.core.permissions import get_current_user, require_activated_worker
from app.services.storage import document_storage
from app.services.audit import log_audit_event

router = APIRouter(tags=["Job Applications"])

def build_application_out(app: JobApplication) -> ApplicationOut:
    doc_outs = [
        DocumentOut(
            id=d.id,
            document_type=d.document_type,
            original_filename=d.original_filename,
            content_type=d.content_type,
            size_bytes=d.size_bytes,
            scan_status=d.scan_status,
            uploaded_at=d.uploaded_at
        ) for d in app.documents if d.deleted_at is None
    ]
    return ApplicationOut(
        id=app.id,
        worker_id=app.worker_id,
        job_id=app.job_id,
        job_title=app.job.title if app.job else None,
        job_country=app.job.country if app.job else None,
        cover_letter=app.cover_letter,
        status=app.status,
        submitted_at=app.submitted_at,
        updated_at=app.updated_at,
        documents=doc_outs
    )

@router.post("/jobs/{job_id}/applications", response_model=ApplicationOut, status_code=status.HTTP_201_CREATED)
def submit_application(
    job_id: UUID,
    req: ApplicationSubmitRequest,
    current_user: User = Depends(require_activated_worker),
    db: Session = Depends(get_db)
):
    # Verify job exists and is published
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job or job.status != JobStatus.PUBLISHED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This job is not open for applications."
        )

    # Check for duplicate application
    existing_app = (
        db.query(JobApplication)
        .filter(JobApplication.worker_id == current_user.id, JobApplication.job_id == job_id)
        .first()
    )
    if existing_app:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You have already submitted an application for this job."
        )

    application = JobApplication(
        worker_id=current_user.id,
        job_id=job_id,
        cover_letter=req.cover_letter.strip() if req.cover_letter else None,
        status=ApplicationStatus.SUBMITTED
    )
    db.add(application)
    db.commit()
    db.refresh(application)

    log_audit_event(
        db=db,
        action="application.submitted",
        target_type="job_application",
        target_id=str(application.id),
        actor_user_id=current_user.id,
        metadata_json={"job_id": str(job_id)}
    )

    return build_application_out(application)

@router.get("/workers/me/applications", response_model=List[ApplicationOut])
def list_my_applications(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    apps = (
        db.query(JobApplication)
        .filter(JobApplication.worker_id == current_user.id)
        .order_by(JobApplication.submitted_at.desc())
        .all()
    )
    return [build_application_out(a) for a in apps]

@router.get("/applications/{application_id}", response_model=ApplicationOut)
def get_application(
    application_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    application = db.query(JobApplication).filter(JobApplication.id == application_id).first()
    if not application:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found.")

    # Authorization: worker owner or admin/reviewer
    if application.worker_id != current_user.id and current_user.role.value not in ["administrator", "reviewer"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")

    return build_application_out(application)

@router.post("/applications/{application_id}/documents", response_model=DocumentOut, status_code=status.HTTP_201_CREATED)
async def upload_application_document(
    application_id: UUID,
    document_type: str = Form(..., description="Document type: cv, certificate, passport, etc."),
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    application = db.query(JobApplication).filter(JobApplication.id == application_id).first()
    if not application:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found.")

    if application.worker_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")

    # Store file safely in private storage
    storage_key, content_type, size_bytes, sha256_hash = await document_storage.save_document(file)

    doc = ApplicationDocument(
        application_id=application.id,
        document_type=document_type.strip().lower(),
        original_filename=file.filename or "uploaded_document",
        storage_key=storage_key,
        content_type=content_type,
        size_bytes=size_bytes,
        sha256_hash=sha256_hash,
        scan_status=DocumentScanStatus.CLEAN  # Mock scan status clean in dev
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    log_audit_event(
        db=db,
        action="document.uploaded",
        target_type="application_document",
        target_id=str(doc.id),
        actor_user_id=current_user.id,
        metadata_json={
            "application_id": str(application.id),
            "filename": doc.original_filename,
            "document_type": doc.document_type
        }
    )

    return DocumentOut.model_validate(doc)

@router.get("/applications/{application_id}/documents", response_model=List[DocumentOut])
def list_application_documents(
    application_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    application = db.query(JobApplication).filter(JobApplication.id == application_id).first()
    if not application:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found.")

    if application.worker_id != current_user.id and current_user.role.value not in ["administrator", "reviewer"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")

    docs = [d for d in application.documents if d.deleted_at is None]
    return [DocumentOut.model_validate(d) for d in docs]

