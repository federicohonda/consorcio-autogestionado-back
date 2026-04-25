import os
import uuid
from fastapi import UploadFile, HTTPException
from src.core.config import settings
from src.core.logger import logger

ALLOWED_MIME_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
    "image/gif",
    "application/pdf",
}

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".pdf"}


async def save_receipt(file: UploadFile) -> str:
    """Validates, stores and returns the public path for a receipt file."""
    content_type = file.content_type or ""
    if content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=400,
            detail="Tipo de archivo no permitido. Solo se aceptan imágenes (JPG, PNG, WEBP) o PDF.",
        )

    _, ext = os.path.splitext(file.filename or "")
    ext = ext.lower()
    if ext not in ALLOWED_EXTENSIONS:
        ext = _ext_from_mime(content_type)

    contents = await file.read()

    if len(contents) > settings.max_receipt_size_bytes:
        raise HTTPException(
            status_code=400,
            detail=f"El archivo supera el tamaño máximo de {settings.max_receipt_size_bytes // (1024 * 1024)} MB.",
        )

    receipts_dir = os.path.join(settings.uploads_dir, "receipts")
    os.makedirs(receipts_dir, exist_ok=True)

    filename = f"{uuid.uuid4().hex}{ext}"
    file_path = os.path.join(receipts_dir, filename)

    with open(file_path, "wb") as f:
        f.write(contents)

    public_url = f"/uploads/receipts/{filename}"
    logger.info(f"Receipt saved: {public_url} ({len(contents)} bytes)")
    return public_url


def delete_receipt(receipt_url: str) -> None:
    """Removes a receipt file from disk (best-effort)."""
    if not receipt_url:
        return
    relative = receipt_url.lstrip("/")
    file_path = os.path.join(settings.uploads_dir, *relative.split("/")[1:])
    try:
        if os.path.isfile(file_path):
            os.remove(file_path)
    except OSError as e:
        logger.warning(f"Could not delete receipt {file_path}: {e}")


def _ext_from_mime(mime: str) -> str:
    mapping = {
        "image/jpeg": ".jpg",
        "image/png": ".png",
        "image/webp": ".webp",
        "image/gif": ".gif",
        "application/pdf": ".pdf",
    }
    return mapping.get(mime, ".bin")
