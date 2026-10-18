import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, Text, Integer, BigInteger, Boolean, DateTime, ForeignKey,
    Enum, Index, UniqueConstraint, JSON
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import enum

from app.db.session import Base

# Enums
class UserRole(str, enum.Enum):
    WORKER = "worker"
    ADMINISTRATOR = "administrator"
    REVIEWER = "reviewer"

class UserStatus(str, enum.Enum):
    PENDING_VERIFICATION = "pending_verification"
    ACTIVE = "active"
    SUSPENDED = "suspended"

class JobStatus(str, enum.Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    PAUSED = "paused"
    CLOSED = "closed"
    EXPIRED = "expired"

class VerificationResult(str, enum.Enum):
    VERIFIED = "verified"
    REJECTED = "rejected"
    FLAGGED = "flagged"

class PaymentStatus(str, enum.Enum):
    INITIATED = "initiated"
    AWAITING_CONFIRMATION = "awaiting_confirmation"
    CONFIRMED = "confirmed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    REVERSED = "reversed"

class EntitlementType(str, enum.Enum):
    PLATFORM_ACCESS = "platform_access"

class ApplicationStatus(str, enum.Enum):
    SUBMITTED = "submitted"
    UNDER_REVIEW = "under_review"
    SHORTLISTED = "shortlisted"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"

class DocumentScanStatus(str, enum.Enum):
    PENDING = "pending"
    CLEAN = "clean"
    INFECTED = "infected"
    FAILED = "failed"

class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    phone = Column(String(32), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=True, index=True)
    password_hash = Column(String(255), nullable=True)
    role = Column(Enum(UserRole), default=UserRole.WORKER, nullable=False)
    status = Column(Enum(UserStatus), default=UserStatus.PENDING_VERIFICATION, nullable=False)
    phone_verified_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    profile = relationship("WorkerProfile", back_populates="user", uselist=False, cascade="all, delete-orphan")
    applications = relationship("JobApplication", back_populates="worker", cascade="all, delete-orphan")
    payments = relationship("Payment", back_populates="user", cascade="all, delete-orphan")
    entitlements = relationship("Entitlement", back_populates="user", cascade="all, delete-orphan")

class WorkerProfile(Base):
    __tablename__ = "worker_profiles"

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    full_name = Column(String(255), nullable=False)
    trade = Column(String(100), nullable=False)
    preferred_country = Column(String(100), nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="profile")

class Job(Base):
    __tablename__ = "jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    title = Column(String(255), nullable=False)
    category = Column(String(100), nullable=False, index=True)
    country = Column(String(100), nullable=False, index=True)
    city = Column(String(100), nullable=False)
    salary_min = Column(BigInteger, nullable=False)  # in minor units or local currency units
    salary_max = Column(BigInteger, nullable=False)
    salary_currency = Column(String(10), nullable=False)  # SAR, AED, QAR, etc.
    salary_period = Column(String(20), default="mo", nullable=False)  # mo, yr, hr
    description = Column(Text, nullable=False)
    requirements = Column(Text, nullable=False)
    employer_name = Column(String(255), nullable=True)
    status = Column(Enum(JobStatus), default=JobStatus.DRAFT, nullable=False, index=True)
    published_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    verifications = relationship("JobVerification", back_populates="job", cascade="all, delete-orphan")
    applications = relationship("JobApplication", back_populates="job", cascade="all, delete-orphan")

class JobVerification(Base):
    __tablename__ = "job_verifications"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id = Column(UUID(as_uuid=True), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    reviewer_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    verification_type = Column(String(100), nullable=False)  # e.g. "licence_and_contractor_registry"
    result = Column(Enum(VerificationResult), nullable=False)
    evidence_reference = Column(String(500), nullable=True)  # Registration ID, contract ref
    review_notes = Column(Text, nullable=True)
    reviewed_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    job = relationship("Job", back_populates="verifications")
    reviewer = relationship("User")

class Payment(Base):
    __tablename__ = "payments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    purpose = Column(String(100), default="platform_access", nullable=False)
    amount_minor = Column(BigInteger, nullable=False)  # 100000 for KSh 1000
    currency = Column(String(10), default="KES", nullable=False)
    provider = Column(String(50), nullable=False)  # mpesa, mock
    provider_reference = Column(String(100), unique=True, nullable=True, index=True)
    checkout_request_id = Column(String(100), unique=True, nullable=True, index=True)
    merchant_request_id = Column(String(100), nullable=True, index=True)
    phone_number = Column(String(32), nullable=True)
    status = Column(Enum(PaymentStatus), default=PaymentStatus.INITIATED, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    confirmed_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="payments")
    entitlements = relationship("Entitlement", back_populates="source_payment")

class Entitlement(Base):
    __tablename__ = "entitlements"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    entitlement_type = Column(Enum(EntitlementType), default=EntitlementType.PLATFORM_ACCESS, nullable=False)
    source_payment_id = Column(UUID(as_uuid=True), ForeignKey("payments.id"), nullable=True, unique=True)
    granted_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=True)  # null indicates non-expiring under initial policy
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    revocation_reason = Column(String(255), nullable=True)

    user = relationship("User", back_populates="entitlements")
    source_payment = relationship("Payment", back_populates="entitlements")

class JobApplication(Base):
    __tablename__ = "job_applications"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    worker_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    job_id = Column(UUID(as_uuid=True), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    cover_letter = Column(Text, nullable=True)
    status = Column(Enum(ApplicationStatus), default=ApplicationStatus.SUBMITTED, nullable=False, index=True)
    submitted_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    worker = relationship("User", back_populates="applications")
    job = relationship("Job", back_populates="applications")
    documents = relationship("ApplicationDocument", back_populates="application", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("worker_id", "job_id", name="uq_worker_job_application"),
    )

class ApplicationDocument(Base):
    __tablename__ = "application_documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    application_id = Column(UUID(as_uuid=True), ForeignKey("job_applications.id", ondelete="CASCADE"), nullable=False, index=True)
    document_type = Column(String(50), nullable=False)  # cv, certificate, passport, id_document, other
    original_filename = Column(String(255), nullable=False)
    storage_key = Column(String(255), unique=True, nullable=False)
    content_type = Column(String(100), nullable=False)
    size_bytes = Column(BigInteger, nullable=False)
    sha256_hash = Column(String(64), nullable=False)
    scan_status = Column(Enum(DocumentScanStatus), default=DocumentScanStatus.PENDING, nullable=False)
    uploaded_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    application = relationship("JobApplication", back_populates="documents")

class PaymentWebhookEvent(Base):
    __tablename__ = "payment_webhook_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    provider = Column(String(50), nullable=False)
    event_reference = Column(String(150), unique=True, nullable=False, index=True)  # Deduplication key
    payment_id = Column(UUID(as_uuid=True), ForeignKey("payments.id"), nullable=True)
    raw_payload = Column(JSON, nullable=True)
    processing_status = Column(String(50), default="processed", nullable=False)
    received_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    processed_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

class AuditEvent(Base):
    __tablename__ = "audit_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    actor_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True)
    action = Column(String(100), nullable=False, index=True)
    target_type = Column(String(100), nullable=False)
    target_id = Column(String(100), nullable=True)
    request_id = Column(String(100), nullable=True)
    metadata_json = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

class OtpChallenge(Base):
    __tablename__ = "otp_challenges"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    phone = Column(String(32), nullable=False, index=True)
    code_hash = Column(String(255), nullable=False)
    attempts = Column(Integer, default=0, nullable=False)
    max_attempts = Column(Integer, default=3, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    consumed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

