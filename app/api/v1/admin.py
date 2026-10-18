from typing import List, Optional
from uuid import UUID
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import (
    User, UserRole, Job, JobStatus, JobVerification,
    JobApplication, Payment, AuditEvent, VerificationResult,
    ApplicationStatus
)
from app.schemas import (
    JobCreate, JobUpdate, JobOut, JobVerificationCreate, JobVerificationOut,
    ApplicationOut, ApplicationStatusUpdate, PaymentOut, AuditEventOut, StatusResponse
)
from app.core.permissions import require_role
from app.services.audit import log_audit_event
from app.api.v1.jobs import build_job_out
from app.api.v1.applications import build_application_out

router = APIRouter(prefix="/admin", tags=["Administrator & Reviewer Management"])

admin_or_reviewer = require_role(UserRole.ADMINISTRATOR, UserRole.REVIEWER)
admin_only = require_role(UserRole.ADMINISTRATOR)

@router.get("/jobs", response_model=List[JobOut])
def list_admin_jobs(
    status_filter: Optional[JobStatus] = Query(None, alias="status"),
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(admin_or_reviewer),
    db: Session = Depends(get_db)
):
    query = db.query(Job)
    if status_filter:
        query = query.filter(Job.status == status_filter)
    jobs = query.order_by(Job.created_at.desc()).offset(skip).limit(limit).all()
    return [build_job_out(j) for j in jobs]

@router.post("/jobs", response_model=JobOut, status_code=status.HTTP_201_CREATED)
def create_job(
    req: JobCreate,
    current_user: User = Depends(admin_only),
    db: Session = Depends(get_db)
):
    job = Job(
        created_by=current_user.id,
        title=req.title.strip(),
        category=req.category.strip(),
        country=req.country.strip(),
        city=req.city.strip(),
        salary_min=req.salary_min,
        salary_max=req.salary_max,
        salary_currency=req.salary_currency.upper(),
        salary_period=req.salary_period,
        description=req.description.strip(),
        requirements=req.requirements.strip(),
        employer_name=req.employer_name.strip() if req.employer_name else None,
        status=req.status,
        published_at=datetime.now(timezone.utc) if req.status == JobStatus.PUBLISHED else None
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    log_audit_event(
        db=db,
        action="admin.job_created",
        target_type="job",
        target_id=str(job.id),
        actor_user_id=current_user.id,
        metadata_json={"title": job.title, "status": job.status.value}
    )

    return build_job_out(job)

@router.patch("/jobs/{job_id}", response_model=JobOut)
def update_job(
    job_id: UUID,
    req: JobUpdate,
    current_user: User = Depends(admin_only),
    db: Session = Depends(get_db)
):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found.")

    for field, val in req.model_dump(exclude_unset=True).items():
        if val is not None:
            setattr(job, field, val)

    db.commit()
    db.refresh(job)

    log_audit_event(
        db=db,
        action="admin.job_updated",
        target_type="job",
        target_id=str(job.id),
        actor_user_id=current_user.id
    )

    return build_job_out(job)

@router.post("/jobs/{job_id}/publish", response_model=JobOut)
def publish_job(
    job_id: UUID,
    current_user: User = Depends(admin_only),
    db: Session = Depends(get_db)
):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found.")

    job.status = JobStatus.PUBLISHED
    job.published_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(job)

    log_audit_event(
        db=db,
        action="admin.job_published",
        target_type="job",
        target_id=str(job.id),
        actor_user_id=current_user.id
    )

    return build_job_out(job)

@router.post("/jobs/{job_id}/pause", response_model=JobOut)
def pause_job(
    job_id: UUID,
    current_user: User = Depends(admin_only),
    db: Session = Depends(get_db)
):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found.")

    job.status = JobStatus.PAUSED
    db.commit()
    db.refresh(job)

    log_audit_event(
        db=db,
        action="admin.job_paused",
        target_type="job",
        target_id=str(job.id),
        actor_user_id=current_user.id
    )

    return build_job_out(job)

@router.post("/jobs/{job_id}/close", response_model=JobOut)
def close_job(
    job_id: UUID,
    current_user: User = Depends(admin_only),
    db: Session = Depends(get_db)
):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found.")

    job.status = JobStatus.CLOSED
    db.commit()
    db.refresh(job)

    log_audit_event(
        db=db,
        action="admin.job_closed",
        target_type="job",
        target_id=str(job.id),
        actor_user_id=current_user.id
    )

    return build_job_out(job)

@router.post("/jobs/{job_id}/verification", response_model=JobVerificationOut, status_code=status.HTTP_201_CREATED)
def record_job_verification(
    job_id: UUID,
    req: JobVerificationCreate,
    current_user: User = Depends(admin_or_reviewer),
    db: Session = Depends(get_db)
):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found.")

    verification = JobVerification(
        job_id=job.id,
        reviewer_id=current_user.id,
        verification_type=req.verification_type,
        result=req.result,
        evidence_reference=req.evidence_reference,
        review_notes=req.review_notes,
        reviewed_at=datetime.now(timezone.utc)
    )
    db.add(verification)
    db.commit()
    db.refresh(verification)

    log_audit_event(
        db=db,
        action="admin.job_verified",
        target_type="job_verification",
        target_id=str(verification.id),
        actor_user_id=current_user.id,
        metadata_json={
            "job_id": str(job.id),
            "result": req.result.value,
            "verification_type": req.verification_type
        }
    )

    return JobVerificationOut.model_validate(verification)

@router.get("/applications", response_model=List[ApplicationOut])
def list_admin_applications(
    status_filter: Optional[ApplicationStatus] = Query(None, alias="status"),
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(admin_or_reviewer),
    db: Session = Depends(get_db)
):
    query = db.query(JobApplication)
    if status_filter:
        query = query.filter(JobApplication.status == status_filter)
    apps = query.order_by(JobApplication.submitted_at.desc()).offset(skip).limit(limit).all()
    return [build_application_out(a) for a in apps]

@router.patch("/applications/{application_id}", response_model=ApplicationOut)
def update_application_status(
    application_id: UUID,
    req: ApplicationStatusUpdate,
    current_user: User = Depends(admin_or_reviewer),
    db: Session = Depends(get_db)
):
    app_record = db.query(JobApplication).filter(JobApplication.id == application_id).first()
    if not app_record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found.")

    old_status = app_record.status
    app_record.status = req.status
    app_record.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(app_record)

    log_audit_event(
        db=db,
        action="admin.application_status_updated",
        target_type="job_application",
        target_id=str(app_record.id),
        actor_user_id=current_user.id,
        metadata_json={
            "old_status": old_status.value,
            "new_status": req.status.value,
            "review_notes": req.review_notes
        }
    )

    return build_application_out(app_record)

@router.get("/payments", response_model=List[PaymentOut])
def list_admin_payments(
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(admin_only),
    db: Session = Depends(get_db)
):
    payments = db.query(Payment).order_by(Payment.created_at.desc()).offset(skip).limit(limit).all()
    return [PaymentOut.model_validate(p) for p in payments]

@router.get("/audit-events", response_model=List[AuditEventOut])
def list_audit_events(
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(admin_only),
    db: Session = Depends(get_db)
):
    events = db.query(AuditEvent).order_by(AuditEvent.created_at.desc()).offset(skip).limit(limit).all()
    return [AuditEventOut.model_validate(e) for e in events]

