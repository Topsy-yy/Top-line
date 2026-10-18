import hashlib
import os
import shutil
from typing import Tuple
from fastapi import UploadFile, HTTPException, status
from app.core.config import settings

# Magic byte signatures
SIGNATURES = {
    "application/pdf": b"%PDF",
    "image/jpeg": b"\xff\xd8\xff",
    "image/png": b"\x89PNG\r\n\x1a\n",
    "application/msword": b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": b"PK\x03\x04"
}

class DocumentStorageService:
    def __init__(self, base_dir: str = settings.DOCUMENT_STORAGE_DIR):
        self.base_dir = base_dir
        os.makedirs(self.base_dir, exist_ok=True)

    async def save_document(self, upload_file: UploadFile) -> Tuple[str, str, int, str]:
        """
        Validates content type, magic bytes, file size, computes SHA256,
        and saves the file under a random storage key.
        Returns (storage_key, content_type, size_bytes, sha256_hash).
        """
        content_type = upload_file.content_type
        if content_type not in settings.ALLOWED_DOCUMENT_MIME_TYPES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported file type '{content_type}'. Allowed types: PDF, JPEG, PNG, DOC, DOCX."
            )

        # Read first 16 bytes to check signature
        header = await upload_file.read(16)
        if not header:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded file is empty.")

        expected_prefix = SIGNATURES.get(content_type)
        if expected_prefix and not header.startswith(expected_prefix):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File content signature does not match declared MIME type."
            )

        storage_key = hashlib.sha256(os.urandom(32)).hexdigest()
        target_path = os.path.join(self.base_dir, storage_key)

        sha256 = hashlib.sha256()
        sha256.update(header)
        size_bytes = len(header)

        with open(target_path, "wb") as f:
            f.write(header)
            while chunk := await upload_file.read(1024 * 64):
                size_bytes += len(chunk)
                if size_bytes > settings.MAX_UPLOAD_SIZE_BYTES:
                    # Remove partial file
                    f.close()
                    if os.path.exists(target_path):
                        os.remove(target_path)
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail=f"File exceeds maximum upload limit of {settings.MAX_UPLOAD_SIZE_BYTES // (1024*1024)} MB."
                    )
                sha256.update(chunk)
                f.write(chunk)

        sha256_hex = sha256.hexdigest()
        return storage_key, content_type, size_bytes, sha256_hex

    def get_document_path(self, storage_key: str) -> str:
        # Prevent directory traversal
        sanitized_key = os.path.basename(storage_key)
        path = os.path.join(self.base_dir, sanitized_key)
        if not os.path.exists(path):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document file not found on storage.")
        return path

    def delete_document(self, storage_key: str) -> bool:
        path = self.get_document_path(storage_key)
        if os.path.exists(path):
            os.remove(path)
            return True
        return False

document_storage = DocumentStorageService()

