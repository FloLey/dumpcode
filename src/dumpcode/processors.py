"""File content processing and encoding detection."""

from pathlib import Path
from typing import Callable, Dict, Optional, Tuple


def detect_file_encoding(header: bytes) -> str:
    """Attempt to detect file encoding using buffered heuristics.

    Args:
        header: First 4096 bytes of the file content.

    Returns:
        Detected encoding string (e.g., 'utf-8', 'latin-1').
    """
    if not header:
        return 'utf-8'

    if header.startswith(b'\xef\xbb\xbf'):
        return 'utf-8-sig'
    if header.startswith(b'\xff\xfe'):
        return 'utf-16-le'
    if header.startswith(b'\xfe\xff'):
        return 'utf-16-be'

    for enc in ['utf-8', 'latin-1', 'cp1252']:
        try:
            header.decode(enc)
            return enc
        except UnicodeDecodeError:
            continue

    return 'utf-8'


def is_binary_file(filepath: Path) -> bool:
    """Check if a file is likely binary based on extension and content.
    
    Args:
        filepath: Path to the file to check.

    Returns:
        True if the file is detected as binary, False otherwise.
    """
    binary_extensions = {
        '.pyc', '.pyo', '.so', '.dll', '.exe', '.bin', '.jpg', '.png', '.zip',
        '.pdf', '.pyd', '.ico', '.tar', '.gz', '.7z', '.mp3', '.mp4', '.avi',
        '.mov', '.wav', '.ogg', '.flac', '.webm', '.mkv'
    }
    if filepath.suffix.lower() in binary_extensions:
        return True

    try:
        if filepath.stat().st_size == 0:
            return False
        with open(filepath, 'rb') as f:
            if b'\0' in f.read(1024):
                return True
    except Exception:
        return True
    return False


def truncate_text_lines(file_path: Path, limit: int = 5) -> str:
    """Read and return only the first N lines of a file.
    
    Args:
        file_path: Path to the file.
        limit: Maximum number of lines to read.

    Returns:
        A string containing the truncated lines and a marker.
    """
    try:
        lines = []
        has_more = False
        
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            for _ in range(limit):
                line = f.readline()
                if not line:
                    break
                lines.append(line)
            
            # Check if there is more content while file is still open
            if len(lines) == limit and f.readline():
                has_more = True
        
        if not lines:
            return f"[Data snippet from {file_path.name}]"
        
        content = "".join(lines)
        
        if has_more:
            return content + f"\n[... truncated {file_path.suffix} ...]"
        
        return content
    except Exception:
        return f"[Data snippet from {file_path.name}]"

CONTENT_PROCESSORS: Dict[str, Callable[[Path], str]] = {
    ".csv": lambda p: truncate_text_lines(p, 5),
    ".jsonl": lambda p: truncate_text_lines(p, 5),
    ".log": lambda p: truncate_text_lines(p, 10),
}


def get_file_content(file_path: Path, ignore_errors: bool = False) -> Tuple[str, Optional[str]]:
    """Get content from a file, applying appropriate processors.
    
    Args:
        file_path: Path to the target file.
        ignore_errors: If True, uses 'ignore' error handler for decoding.

    Returns:
        Tuple of (content, error_message). error_message is None if successful.
    """
    ext = file_path.suffix.lower()
    if ext in CONTENT_PROCESSORS:
        return CONTENT_PROCESSORS[ext](file_path), None
    
    if is_binary_file(file_path):
        return "[Binary file content omitted]\n", None
    
    try:
        with open(file_path, 'rb') as f:
            raw_data = f.read()
        
        header = raw_data[:4096]
        encoding = detect_file_encoding(header)
        
        error_handler = "ignore" if ignore_errors else "strict"
        return raw_data.decode(encoding, errors=error_handler), None
    except Exception as e:
        error_msg = f"Error reading file: {e}"
        return f"[{error_msg}]", error_msg