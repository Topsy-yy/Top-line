import io
from uuid import uuid4
from app.models import UserRole, JobStatus, PaymentStatus

def test_public_can_retrieve_published_jobs(client, published_job, draft_job):
    resp = client.get("/api/v1/jobs")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 1
    job_ids = [j["id"] for j in data]
    assert str(published_job.id) in job_ids
    # Draft job must be excluded
    assert str(draft_job.id) not in job_ids

def test_public_get_single_job_excludes_draft(client, published_job, draft_job):
    pub_resp = client.get(f"/api/v1/jobs/{published_job.id}")
    assert pub_resp.status_code == 200
    assert pub_resp.json()["title"] == "Master Plumber"

    draft_resp = client.get(f"/api/v1/jobs/{draft_job.id}")
    assert draft_resp.status_code == 404

def test_public_cannot_escalate_role_on_registration(client):
    payload = {
        "full_name": "Infiltrator",
        "phone": "+254799000111",
        "email": "hack@admin.com",
        "trade": "Mason",
        "preferred_country": "Qatar",
        "password": "SecurePassword123!",
        "role": "administrator"  # Attempted escalation
    }
    resp = client.post("/api/v1/registrations", json=payload)
    assert resp.status_code == 201
    user_id = resp.json()["user_id"]

    # Verify via phone verify
    mock_otp = resp.json().get("mock_otp")
    assert mock_otp is not None

    v_resp = client.post("/api/v1/auth/phone/verify", json={"phone": "+254799000111", "otp_code": mock_otp})
    assert v_resp.status_code == 200
    token_data = v_resp.json()
    # Ensure role remained worker
    assert token_data["role"] == "worker"

def test_worker_cannot_create_or_modify_jobs(client, worker_token, published_job):
    headers = {"Authorization": f"Bearer {worker_token}"}
    create_payload = {
        "title": "Hacked Job",
        "category": "Structural",
        "country": "UAE",
        "city": "Dubai",
        "salary_min": 5000,
        "salary_max": 6000,
        "salary_currency": "AED",
        "salary_period": "mo",
        "description": "Exploit attempt",
        "requirements": "None"
    }
    # Attempt create job
    resp = client.post("/api/v1/admin/jobs", json=create_payload, headers=headers)
    assert resp.status_code == 403

    # Attempt pause job
    resp2 = client.post(f"/api/v1/admin/jobs/{published_job.id}/pause", headers=headers)
    assert resp2.status_code == 403

    # Attempt record verification
    verify_payload = {
        "verification_type": "fake_review",
        "result": "verified"
    }
    resp3 = client.post(f"/api/v1/admin/jobs/{published_job.id}/verification", json=verify_payload, headers=headers)
    assert resp3.status_code == 403

def test_admin_can_create_publish_pause_and_verify_job(client, admin_token):
    headers = {"Authorization": f"Bearer {admin_token}"}
    create_payload = {
        "title": "Tower Crane Operator",
        "category": "Equipment & Site",
        "country": "Saudi Arabia",
        "city": "Jeddah",
        "salary_min": 3500,
        "salary_max": 4200,
        "salary_currency": "SAR",
        "salary_period": "mo",
        "description": "Operating 50T tower crane on high-rise building.",
        "requirements": "Certified crane operator licence with 5+ years experience.",
        "employer_name": "Red Sea Construction",
        "status": "draft"
    }
    resp = client.post("/api/v1/admin/jobs", json=create_payload, headers=headers)
    assert resp.status_code == 201
    job_data = resp.json()
    job_id = job_data["id"]
    assert job_data["status"] == "draft"

    # Verify job in draft is not public
    pub_list = client.get("/api/v1/jobs").json()
    assert str(job_id) not in [j["id"] for j in pub_list]

    # Publish job
    pub_resp = client.post(f"/api/v1/admin/jobs/{job_id}/publish", headers=headers)
    assert pub_resp.status_code == 200
    assert pub_resp.json()["status"] == "published"

    # Record verification
    v_resp = client.post(
        f"/api/v1/admin/jobs/{job_id}/verification",
        json={
            "verification_type": "contractor_licence_check",
            "result": "verified",
            "evidence_reference": "LIC-998822"
        },
        headers=headers
    )
    assert v_resp.status_code == 201

    # Check public job now shows is_verified = True
    public_job = client.get(f"/api/v1/jobs/{job_id}").json()
    assert public_job["is_verified"] is True
    assert len(public_job["verifications"]) == 1

def test_unactivated_worker_cannot_apply(client, worker_token, published_job):
    headers = {"Authorization": f"Bearer {worker_token}"}
    app_payload = {"cover_letter": "I am interested in this job."}
    resp = client.post(f"/api/v1/jobs/{published_job.id}/applications", json=app_payload, headers=headers)
    assert resp.status_code == 403
    assert "activation fee" in resp.json()["detail"].lower()

def test_activated_worker_can_apply_and_duplicate_is_prevented(client, activated_worker_token, published_job):
    headers = {"Authorization": f"Bearer {activated_worker_token}"}
    app_payload = {"cover_letter": "Certified plumber with 5 years GCC experience."}

    # First application succeeds
    resp = client.post(f"/api/v1/jobs/{published_job.id}/applications", json=app_payload, headers=headers)
    assert resp.status_code == 201
    app_data = resp.json()
    assert app_data["status"] == "submitted"
    assert app_data["job_id"] == str(published_job.id)

    # Duplicate application rejected
    dup_resp = client.post(f"/api/v1/jobs/{published_job.id}/applications", json=app_payload, headers=headers)
    assert dup_resp.status_code == 409
    assert "already submitted" in dup_resp.json()["detail"]

def test_document_upload_and_download_authorization(client, activated_worker_token, worker_token, published_job):
    # Activated worker applies
    act_headers = {"Authorization": f"Bearer {activated_worker_token}"}
    app_resp = client.post(
        f"/api/v1/jobs/{published_job.id}/applications",
        json={"cover_letter": "Here is my application."},
        headers=act_headers
    )
    app_id = app_resp.json()["id"]

    # Upload valid PDF document
    fake_pdf_content = b"%PDF-1.4 sample pdf content for testing document storage"
    files = {
        "file": ("test_cv.pdf", io.BytesIO(fake_pdf_content), "application/pdf")
    }
    data = {"document_type": "cv"}
    upload_resp = client.post(
        f"/api/v1/applications/{app_id}/documents",
        data=data,
        files=files,
        headers=act_headers
    )
    assert upload_resp.status_code == 201
    doc_id = upload_resp.json()["id"]

    # Worker owner can download document
    download_resp = client.get(f"/api/v1/documents/{doc_id}/download", headers=act_headers)
    assert download_resp.status_code == 200
    assert download_resp.content == fake_pdf_content

    # Another worker CANNOT download this document (IDOR protection)
    other_headers = {"Authorization": f"Bearer {worker_token}"}
    unauth_resp = client.get(f"/api/v1/documents/{doc_id}/download", headers=other_headers)
    assert unauth_resp.status_code == 403

def test_oversized_and_invalid_document_rejected(client, activated_worker_token, published_job):
    act_headers = {"Authorization": f"Bearer {activated_worker_token}"}
    app_resp = client.post(
        f"/api/v1/jobs/{published_job.id}/applications",
        json={"cover_letter": "Application for upload check."},
        headers=act_headers
    )
    app_id = app_resp.json()["id"]

    # Spoofed mime type (claims PDF but content is arbitrary text)
    invalid_files = {
        "file": ("fake.pdf", io.BytesIO(b"NOT A REAL PDF HEADER"), "application/pdf")
    }
    bad_sig_resp = client.post(
        f"/api/v1/applications/{app_id}/documents",
        data={"document_type": "cv"},
        files=invalid_files,
        headers=act_headers
    )
    assert bad_sig_resp.status_code == 400
    assert "signature does not match" in bad_sig_resp.json()["detail"]

def test_payment_initiation_and_mock_confirmation(client, worker_token):
    headers = {"Authorization": f"Bearer {worker_token}"}

    # Check initial access is inactive
    access_resp = client.get("/api/v1/workers/me/access", headers=headers)
    assert access_resp.status_code == 200
    assert access_resp.json()["is_activated"] is False

    # Initiate payment
    init_resp = client.post("/api/v1/payments", json={}, headers=headers)
    assert init_resp.status_code == 201
    pay_data = init_resp.json()
    assert pay_data["amount_minor"] == 100000
    assert pay_data["currency"] == "KES"
    assert pay_data["status"] == "awaiting_confirmation"
    payment_id = pay_data["id"]

    # Confirm via mock endpoint
    confirm_resp = client.post(
        "/api/v1/payments/mock/confirm",
        json={"payment_id": payment_id, "mpesa_receipt_number": "QWE123TEST"},
        headers=headers
    )
    assert confirm_resp.status_code == 200
    assert confirm_resp.json()["status"] == "confirmed"

    # Check access is now active
    access_after = client.get("/api/v1/workers/me/access", headers=headers)
    assert access_after.json()["is_activated"] is True

def test_mpesa_callback_with_wrong_amount_fails_and_grants_no_entitlement(client, db, worker_user):
    from app.models import Payment, Entitlement
    # Create a pending payment
    payment = Payment(
        user_id=worker_user.id,
        purpose="platform_access",
        amount_minor=100000,
        currency="KES",
        provider="mpesa",
        checkout_request_id="ws_CO_TEST_WRONG_AMOUNT",
        status=PaymentStatus.AWAITING_CONFIRMATION
    )
    db.add(payment)
    db.commit()

    # Callback with wrong amount (e.g. 500 KES instead of 1,000 KES)
    callback_payload = {
        "Body": {
            "stkCallback": {
                "MerchantRequestID": "MOCK_MERCH",
                "CheckoutRequestID": "ws_CO_TEST_WRONG_AMOUNT",
                "ResultCode": 0,
                "ResultDesc": "The service request is processed successfully.",
                "CallbackMetadata": {
                    "Item": [
                        {"Name": "Amount", "Value": 500},
                        {"Name": "MpesaReceiptNumber", "Value": "BAD_AMOUNT_REC"},
                        {"Name": "PhoneNumber", "Value": 254711223344}
                    ]
                }
            }
        }
    }
    resp = client.post("/api/v1/payments/mpesa/callback", json=callback_payload)
    assert resp.status_code == 200

    db.refresh(payment)
    assert payment.status == PaymentStatus.FAILED

    ent = db.query(Entitlement).filter(Entitlement.source_payment_id == payment.id).first()
    assert ent is None

def test_mpesa_callback_idempotency_prevents_duplicate_entitlements(client, db, worker_user):
    from app.models import Payment, Entitlement
    payment = Payment(
        user_id=worker_user.id,
        purpose="platform_access",
        amount_minor=100000,
        currency="KES",
        provider="mpesa",
        checkout_request_id="ws_CO_TEST_DEDUP",
        status=PaymentStatus.AWAITING_CONFIRMATION
    )
    db.add(payment)
    db.commit()

    valid_payload = {
        "Body": {
            "stkCallback": {
                "MerchantRequestID": "MOCK_MERCH_DEDUP",
                "CheckoutRequestID": "ws_CO_TEST_DEDUP",
                "ResultCode": 0,
                "ResultDesc": "The service request is processed successfully.",
                "CallbackMetadata": {
                    "Item": [
                        {"Name": "Amount", "Value": 1000},
                        {"Name": "MpesaReceiptNumber", "Value": "REC_DEDUP_123"},
                        {"Name": "PhoneNumber", "Value": 254711223344}
                    ]
                }
            }
        }
    }

    # First callback
    resp1 = client.post("/api/v1/payments/mpesa/callback", json=valid_payload)
    assert resp1.status_code == 200

    db.refresh(payment)
    assert payment.status == PaymentStatus.CONFIRMED

    ent_count1 = db.query(Entitlement).filter(Entitlement.user_id == worker_user.id).count()
    assert ent_count1 == 1

    # Duplicate callback with exact same checkout request
    resp2 = client.post("/api/v1/payments/mpesa/callback", json=valid_payload)
    assert resp2.status_code == 200
    assert "already processed" in resp2.json()["ResultDesc"]

    # Entitlement count must remain exactly 1
    ent_count2 = db.query(Entitlement).filter(Entitlement.user_id == worker_user.id).count()
    assert ent_count2 == 1

