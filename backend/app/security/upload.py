from typing import Literal


class UploadValidationError(Exception):
    """Raised when upload validation fails."""
    pass


ALLOWED_EXTENSIONS = {".pdf", ".docx", ".doc"}
ALLOWED_MIMES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/msword",
}
MIME_TO_EXTENSIONS = {
    "application/pdf": {".pdf"},
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": {".docx"},
    "application/msword": {".doc", ".docx"},
}
MAGIC_BYTES = {
    b"%PDF": ".pdf",
    b"PK\x03\x04": ".docx",
    b"PK\x03\x04": ".doc",  # Both DOCX and DOC are ZIP archives
    b"\xd0\xcf\x11\xe0": ".doc",  # OLE2 format (older Word)
}


def _sniff_file_type(content_bytes: bytes) -> str | None:
    """Detect file type by magic bytes."""
    if content_bytes.startswith(b"%PDF"):
        return ".pdf"
    if content_bytes.startswith(b"PK\x03\x04"):
        return ".zip"  # Could be DOCX or other ZIP
    if content_bytes.startswith(b"\xd0\xcf\x11\xe0"):
        return ".doc"  # OLE2 (older Word)
    return None


def _get_extension_from_filename(filename: str) -> str:
    """Extract and validate extension from filename."""
    if "." not in filename:
        raise UploadValidationError(f"Filename '{filename}' has no extension")

    ext = "." + filename.rsplit(".", 1)[-1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise UploadValidationError(
            f"Extension '{ext}' not allowed. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
        )
    return ext


def validate_upload(
    filename: str,
    content_bytes: bytes,
    content_type: str,
    max_size_mb: int = 10,
) -> None:
    """
    Validate an uploaded file.

    Args:
        filename: Original filename from upload
        content_bytes: Raw file content
        content_type: MIME type from request
        max_size_mb: Max allowed file size in MB (default 10)

    Raises:
        UploadValidationError: If validation fails
    """
    if not filename:
        raise UploadValidationError("Filename is empty")

    if not content_bytes:
        raise UploadValidationError("File content is empty")

    max_size_bytes = max_size_mb * 1024 * 1024
    if len(content_bytes) > max_size_bytes:
        raise UploadValidationError(
            f"File size {len(content_bytes) / 1024 / 1024:.1f} MB exceeds "
            f"limit of {max_size_mb} MB"
        )

    ext = _get_extension_from_filename(filename)

    if content_type not in ALLOWED_MIMES:
        raise UploadValidationError(
            f"MIME type '{content_type}' not allowed. Allowed: "
            f"{', '.join(sorted(ALLOWED_MIMES))}"
        )

    allowed_exts_for_mime = MIME_TO_EXTENSIONS.get(content_type, set())
    if ext not in allowed_exts_for_mime:
        raise UploadValidationError(
            f"Extension '{ext}' does not match MIME type '{content_type}'. "
            f"Expected one of: {', '.join(sorted(allowed_exts_for_mime))}"
        )

    sniffed_type = _sniff_file_type(content_bytes)
    if ext == ".pdf":
        if not content_bytes.startswith(b"%PDF"):
            raise UploadValidationError(
                "File claims to be PDF but does not have PDF magic bytes"
            )
    elif ext in {".docx", ".doc"}:
        if sniffed_type not in {".zip", ".doc"}:
            raise UploadValidationError(
                f"File claims to be {ext} but magic bytes indicate {sniffed_type}"
            )
