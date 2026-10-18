from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.db.session import get_db
from app.models import Job, JobStatus, JobVerification, VerificationResult
from app.schemas import JobOut

router = APIRouter(prefix="/jobs", tags=["Public Jobs"])

def build_job_out(job: Job) -> JobOut:
    # Check if there is an active verified verification
    is_verified = any(v.result == VerificationResult.VERIFIED for v in job.verifications)
    return JobOut(
        id=job.id,
        title=job.title,
        category=job.category,
        country=job.country,
        city=job.city,
        salary_min=job.salary_min,
        salary_max=job.salary_max,
        salary_currency=job.salary_currency,
        salary_period=job.salary_period,
        description=job.description,
        requirements=job.requirements,
        employer_name=job.employer_name,
        status=job.status,
        is_verified=is_verified,
        verifications=job.verifications,
        published_at=job.published_at
    )

@router.get("", response_model=List[JobOut])
def list_jobs(
    category: Optional[str] = Query(None, description="Filter by job category"),
    country: Optional[str] = Query(None, description="Filter by country"),
    search: Optional[str] = Query(None, description="Search by title or trade"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db)
):
    query = db.query(Job).filter(Job.status == JobStatus.PUBLISHED)

    if category and category.lower() != "all":
        query = query.filter(func.lower(Job.category) == category.lower())

    if country and country.lower() != "all":
        query = query.filter(func.lower(Job.country) == country.lower())

    if search:
        search_fmt = f"%{search.lower()}%"
        query = query.filter(
            func.lower(Job.title).like(search_fmt) |
            func.lower(Job.description).like(search_fmt)
        )

    jobs = query.order_by(Job.published_at.desc().nullslast(), Job.created_at.desc()).offset(skip).limit(limit).all()
    return [build_job_out(j) for j in jobs]

@router.get("/categories", response_model=List[str])
def list_categories(db: Session = Depends(get_db)):
    categories = (
        db.query(Job.category)
        .filter(Job.status == JobStatus.PUBLISHED)
        .distinct()
        .all()
    )
    result = [c[0] for c in categories if c[0]]
    if not result:
        return ["Structural", "MEP", "Finishing", "Equipment & Site"]
    return sorted(result)

@router.get("/countries", response_model=List[str])
def list_countries(db: Session = Depends(get_db)):
    countries = (
        db.query(Job.country)
        .filter(Job.status == JobStatus.PUBLISHED)
        .distinct()
        .all()
    )
    result = [c[0] for c in countries if c[0]]
    if not result:
        return ["Saudi Arabia", "UAE", "Qatar", "Kuwait", "Oman", "Bahrain"]
    return sorted(result)

@router.get("/{job_id}", response_model=JobOut)
def get_job(job_id: UUID, db: Session = Depends(get_db)):
    job = (
        db.query(Job)
        .filter(Job.id == job_id, Job.status == JobStatus.PUBLISHED)
        .first()
    )
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found or not currently published.")
    return build_job_out(job)

