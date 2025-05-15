import mimetypes
from pathlib import Path
from typing import Set

BINARY_EXTS: Set[str] = {
    '.pdf', '.jpg', '.jpeg', '.png', '.gif', '.doc', '.docx', '.xls', '.xlsx',
    '.zip', '.tar', '.gz', '.exe', '.bin', '.ppt', '.pptx', '.mp3', '.mp4'
}

CONTENT_TYPE_MAP = {
    '.txt': 'text/plain',
    '.html': 'text/html',
    '.htm': 'text/html',
    '.json': 'application/json',
    '.xml': 'application/xml',
    '.pdf': 'application/pdf',
    '.doc': 'application/msword',
    '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    '.xls': 'application/vnd.ms-excel',
    '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    '.csv': 'text/csv',
    '.md': 'text/markdown',
    '.jpg': 'image/jpeg',
    '.jpeg': 'image/jpeg',
    '.png': 'image/png',
    '.gif': 'image/gif',
    '.svg': 'image/svg+xml'
}

def is_binary_by_extension(file_path: Path) -> bool:
    return file_path.suffix.lower() in BINARY_EXTS

def is_binary_by_content(file_path: Path, check_bytes: int = 1024) -> bool:
    try:
        with open(file_path, 'rb') as f:
            chunk = f.read(check_bytes)
        # Heuristic: null bytes or high-bit characters
        return b'\0' in chunk or not all(32 <= b <= 127 or b in b'\r\n\t' for b in chunk)
    except Exception:
        return True  # Assume binary on error

def is_binary_by_mimetype(file_path: Path) -> bool:
    mime_type, _ = mimetypes.guess_type(file_path.as_posix())
    return mime_type is not None and not mime_type.startswith('text')

def is_binary_file(file_path: Path) -> bool:
    # Fast path first
    if is_binary_by_extension(file_path):
        return True
    # Fallback to content-based heuristic
    return is_binary_by_content(file_path)

def get_content_type(file_path: Path) -> str:
    ext = file_path.suffix.lower()
    if ext in CONTENT_TYPE_MAP:
        return CONTENT_TYPE_MAP[ext]
    mime_type, _ = mimetypes.guess_type(file_path.as_posix())
    return mime_type or 'application/octet-stream' 