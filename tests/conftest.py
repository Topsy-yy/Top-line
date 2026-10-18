import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.db.session import Base, get_db
from app.core.config import settings
from app.models import (
    User, WorkerProfile, Job, JobVerification,
    Payment, Entitlement, JobApplication, ApplicationDocument,
    UserRole, UserStatus, JobStatus, VerificationResult,
    PaymentStatus, EntitlementType, ApplicationStatus, DocumentScanStatus
)
from app.core.security import hash_password, create_access_token
from app.core.phone import normalize_phone

test_engine = create_engine(settings.TEST_DATABASE_URL, pool_pre_ping=True)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    Base.metadata.drop_all(bind=test_engine)
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)

@pytest.fixture()
def db():
    connection = test_engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)

    yield session

    session.close()
    transaction.rollback()
    connection.close()

@pytest.fixture()
def client(db):
    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()

@pytest.fixture()
def admin_user(db):
    user = User(
        phone=normalize_phone("+254700999001"),
        email="admin_test@topline.com",
        password_hash=hash_password("AdminPass123!"),
        role=UserRole.ADMINISTRATOR,
        status=UserStatus.ACTIVE
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

@pytest.fixture()
def admin_token(admin_user):
    return create_access_token(data={"sub": str(admin_user.id), "role": admin_user.role.value})

@pytest.fixture()
def worker_user(db):
    user = User(
        phone=normalize_phone("+254711223344"),
        email="worker_test@topline.com",
        password_hash=hash_password("WorkerPass123!"),
        role=UserRole.WORKER,
        status=UserStatus.ACTIVE
    )
    db.add(user)
    db.flush()
    profile = WorkerProfile(
        user_id=user.id,
        full_name="John Kamau",
        trade="Electrician",
        preferred_country="UAE"
    )
    db.add(profile)
    db.commit()
    db.refresh(user)
    return user

@pytest.fixture()
def worker_token(worker_user):
    return create_access_token(data={"sub": str(worker_user.id), "role": worker_user.role.value})

@pytest.fixture()
def activated_worker_user(db):
    user = User(
        phone=normalize_phone("+254722334455"),
        email="active_worker@topline.com",
        password_hash=hash_password("ActivePass123!"),
        role=UserRole.WORKER,
        status=UserStatus.ACTIVE
    )
    db.add(user)
    db.flush()
    profile = WorkerProfile(
        user_id=user.id,
        full_name="Peter Ochieng",
        trade="Mason",
        preferred_country="Saudi Arabia"
    )
    db.add(profile)
    ent = Entitlement(
        user_id=user.id,
        entitlement_type=EntitlementType.PLATFORM_ACCESS
    )
    db.add(ent)
    db.commit()
    db.refresh(user)
    return user

@pytest.fixture()
def activated_worker_token(activated_worker_user):
    return create_access_token(data={"sub": str(activated_worker_user.id), "role": activated_worker_user.role.value})

@pytest.fixture()
def published_job(db, admin_user):
    job = Job(
        created_by=admin_user.id,
        title="Master Plumber",
        category="MEP",
        country="Qatar",
        city="Doha",
        salary_min=2200,
        salary_max=2600,
        salary_currency="QAR",
        salary_period="mo",
        description="High-rise piping installation and MEP testing.",
        requirements="4+ years plumbing experience with commercial trade certificate.",
        status=JobStatus.PUBLISHED
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job

@pytest.fixture()
def draft_job(db, admin_user):
    job = Job(
        created_by=admin_user.id,
        title="Draft Job",
        category="Finishing",
        country="UAE",
        city="Dubai",
        salary_min=1500,
        salary_max=1800,
        salary_currency="AED",
        salary_period="mo",
        description="Draft listing description.",
        requirements="Requirements for draft job.",
        status=JobStatus.DRAFT
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job

