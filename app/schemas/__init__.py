from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, EmailStr, Field
from app.models import (
    UserRole, UserStatus, JobStatus, VerificationResult,
    PaymentStatus, EntitlementType, ApplicationStatus, DocumentScanStatus
)

# Common response
class StatusResponse(BaseModel):
    success: bool
    message: str

# Auth & User Schemas
class RegistrationRequest(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=255)
    phone: str = Field(..., min_length=9, max_length=20)
    email: Optional[EmailStr] = None
    trade: str = Field(..., min_length=2, max_length=100)
    preferred_country: str = Field(..., min_length=2, max_length=100)
    password: Optional[str] = Field(None, min_length=8)

class RegistrationResponse(BaseModel):
    user_id: UUID
    phone: str
    message: str
    phone_verified: bool
    mock_otp: Optional[str] = None  # Included in development / mock mode to facilitate immediate verification

class PhoneVerifyRequest(BaseModel):
    phone: str
    otp_code: str = Field(..., min_length=4, max_length=10)

class PasswordSetupRequest(BaseModel):
    password: str = Field(..., min_length=8)

class LoginRequest(BaseModel):
    phone: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: UUID
    role: UserRole
    phone: str
    full_name: Optional[str] = None

class WorkerProfileResponse(BaseModel):
    user_id: UUID
    phone: str
    email: Optional[str] = None
    role: UserRole
    status: UserStatus
    full_name: str
    trade: str
    preferred_country: str
    is_activated: bool
    phone_verified_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True

class WorkerProfileUpdate(BaseModel):
    full_name: Optional[str] = Field(None, min_length=2, max_length=255)
    trade: Optional[str] = Field(None, min_length=2, max_length=100)
    preferred_country: Optional[str] = Field(None, min_length=2, max_length=100)
    email: Optional[EmailStr] = None

# Job Schemas
class JobVerificationOut(BaseModel):
    id: UUID
    verification_type: str
    result: VerificationResult
    evidence_reference: Optional[str] = None
    reviewed_at: datetime

    class Config:
        from_attributes = True

class JobOut(BaseModel):
    id: UUID
    title: str
    category: str
    country: str
    city: str
    salary_min: int
    salary_max: int
    salary_currency: str
    salary_period: str
    description: str
    requirements: str
    employer_name: Optional[str] = None
    status: JobStatus
    is_verified: bool = False
    verifications: List[JobVerificationOut] = []
    published_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class JobCreate(BaseModel):
    title: str = Field(..., min_length=3, max_length=255)
    category: str = Field(..., min_length=2, max_length=100)
    country: str = Field(..., min_length=2, max_length=100)
    city: str = Field(..., min_length=2, max_length=100)
    salary_min: int = Field(..., ge=0)
    salary_max: int = Field(..., ge=0)
    salary_currency: str = Field(..., min_length=2, max_length=10)
    salary_period: str = Field(default="mo", max_length=20)
    description: str = Field(..., min_length=10)
    requirements: str = Field(..., min_length=10)
    employer_name: Optional[str] = None
    status: JobStatus = JobStatus.DRAFT

class JobUpdate(BaseModel):
    title: Optional[str] = None
    category: Optional[str] = None
    country: Optional[str] = None
    city: Optional[str] = None
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    salary_currency: Optional[str] = None
    salary_period: Optional[str] = None
    description: Optional[str] = None
    requirements: Optional[str] = None
    employer_name: Optional[str] = None
    status: Optional[JobStatus] = None

class JobVerificationCreate(BaseModel):
    verification_type: str = Field(..., min_length=3, max_length=100)
    result: VerificationResult
    evidence_reference: Optional[str] = None
    review_notes: Optional[str] = None

# Payment & Entitlement Schemas
class PaymentInitiateRequest(BaseModel):
    phone_number: Optional[str] = None

class PaymentOut(BaseModel):
    id: UUID
    user_id: UUID
    purpose: str
    amount_minor: int
    currency: str
    provider: str
    provider_reference: Optional[str] = None
    checkout_request_id: Optional[str] = None
    status: PaymentStatus
    created_at: datetime
    confirmed_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class EntitlementOut(BaseModel):
    id: UUID
    user_id: UUID
    entitlement_type: EntitlementType
    granted_at: datetime
    expires_at: Optional[datetime] = None
    is_active: bool

    class Config:
        from_attributes = True

class AccessStatusResponse(BaseModel):
    is_activated: bool
    entitlements: List[EntitlementOut]
    latest_payment: Optional[PaymentOut] = None
    fee_amount: int
    currency: str

class MockPaymentConfirmRequest(BaseModel):
    payment_id: UUID
    mpesa_receipt_number: Optional[str] = None

# Application & Document Schemas
class DocumentOut(BaseModel):
    id: UUID
    document_type: str
    original_filename: str
    content_type: str
    size_bytes: int
    scan_status: DocumentScanStatus
    uploaded_at: datetime

    class Config:
        from_attributes = True

class ApplicationSubmitRequest(BaseModel):
    cover_letter: Optional[str] = None

class ApplicationOut(BaseModel):
    id: UUID
    worker_id: UUID
    job_id: UUID
    job_title: Optional[str] = None
    job_country: Optional[str] = None
    cover_letter: Optional[str] = None
    status: ApplicationStatus
    submitted_at: datetime
    updated_at: datetime
    documents: List[DocumentOut] = []

    class Config:
        from_attributes = True

class ApplicationStatusUpdate(BaseModel):
    status: ApplicationStatus
    review_notes: Optional[str] = None

# Audit Log Schema
class AuditEventOut(BaseModel):
    id: UUID
    actor_user_id: Optional[UUID] = None
    action: str
    target_type: str
    target_id: Optional[str] = None
    metadata_json: Optional[Dict[str, Any]] = None
    created_at: datetime

    class Config:
        from_attributes = True

