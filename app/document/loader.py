"""Document Loader for validating and reading files."""

from pathlib import Path
from typing import Tuple
from app.utils.logging import logger

SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".txt", ".csv", ".xlsx"}
MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024  # 50 MB


class DocumentLoader:
    """Handles file validation, size verification, and safe reading."""

    @staticmethod
    def validate_file(file_path: Path) -> Tuple[bool, str]:
        """Validates file existence, format, and readable size."""
        if not file_path.exists():
            return False, f"File does not exist: {file_path.name}"

        ext = file_path.suffix.lower()
        if ext not in SUPPORTED_EXTENSIONS:
            return False, f"Unsupported file extension '{ext}'. Supported: {', '.join(SUPPORTED_EXTENSIONS)}"

        size = file_path.stat().st_size
        if size == 0:
            return False, f"File '{file_path.name}' is empty (0 bytes)."

        if size > MAX_FILE_SIZE_BYTES:
            return False, f"File exceeds maximum allowed size of 50MB (current: {size / (1024 * 1024):.2f}MB)"

        return True, "Valid"
