import os
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.api.v1.jobs import router as jobs_router
from app.api.v1.registrations import router as registrations_router
from app.api.v1.auth import router as auth_router
from app.api.v1.workers import router as workers_router
from app.api.v1.payments import router as payments_router
from app.api.v1.applications import router as applications_router
from app.api.v1.documents import router as documents_router
from app.api.v1.admin import router as admin_router

app = FastAPI(
    title="TopLine API",
    description="TopLine - Verified Gulf Construction Jobs Backend API",
    version="1.0.0"
)

# CORS configuration - restrict to same-origin / localhost in development
origins = [
    "http://127.0.0.1:8000",
    "http://localhost:8000",
    "http://127.0.0.1:3000",
    "http://localhost:3000"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API v1 Router Registration
app.include_router(jobs_router, prefix="/api/v1")
app.include_router(registrations_router, prefix="/api/v1")
app.include_router(auth_router, prefix="/api/v1")
app.include_router(workers_router, prefix="/api/v1")
app.include_router(payments_router, prefix="/api/v1")
app.include_router(applications_router, prefix="/api/v1")
app.include_router(documents_router, prefix="/api/v1")
app.include_router(admin_router, prefix="/api/v1")

@app.get("/health", tags=["Health"])
def health_check():
    return {
        "status": "healthy",
        "app": "TopLine",
        "environment": settings.APP_ENV,
        "fee_minor": settings.PLATFORM_ACCESS_FEE_MINOR,
        "currency": settings.PLATFORM_ACCESS_CURRENCY
    }

# Serve frontend static assets if directories exist
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
frontend_dir = os.path.join(base_dir, "frontend")
if os.path.exists(os.path.join(frontend_dir, "js")):
    app.mount("/js", StaticFiles(directory=os.path.join(frontend_dir, "js")), name="js")
if os.path.exists(os.path.join(frontend_dir, "assets")):
    app.mount("/assets", StaticFiles(directory=os.path.join(frontend_dir, "assets")), name="assets")

@app.get("/admin", include_in_schema=False)
def serve_admin():
    admin_file = os.path.join(frontend_dir, "admin.html")
    if os.path.exists(admin_file):
        return FileResponse(admin_file, media_type="text/html")
    return {"message": "Admin dashboard file not found."}

@app.get("/dashboard", include_in_schema=False)
def serve_dashboard():
    dash_file = os.path.join(frontend_dir, "dashboard.html")
    if os.path.exists(dash_file):
        return FileResponse(dash_file, media_type="text/html")
    return {"message": "Dashboard file not found."}

@app.get("/", include_in_schema=False)
def serve_index():
    index_file = os.path.join(frontend_dir, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file, media_type="text/html")
    root_index = os.path.join(base_dir, "index.html")
    if os.path.exists(root_index):
        return FileResponse(root_index, media_type="text/html")
    return {"message": "TopLine API is running. Visit /docs for Swagger documentation."}

