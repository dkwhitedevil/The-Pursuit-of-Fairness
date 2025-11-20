# backend/utils/file_handler.py
import os
import shutil
from fastapi import UploadFile, HTTPException
from pathlib import Path
import uuid

TMP_DIR = Path("tmp")
TMP_DIR.mkdir(exist_ok=True)

def save_temp_file(upload_file: UploadFile, max_mb: int = 10) -> str:
    """
    Save UploadFile to a temp directory and return absolute path.
    Also enforce max file size.
    """
    filename = upload_file.filename or f"{uuid.uuid4()}.csv"
    safe_name = f"{int(uuid.uuid4().int>>64)}_{filename.replace(' ', '_')}"
    dest = TMP_DIR / safe_name
    # Read in chunks and enforce size
    total = 0
    with open(dest, "wb") as f:
        while True:
            chunk = upload_file.file.read(1024 * 1024)
            if not chunk:
                break
            total += len(chunk)
            if total > max_mb * 1024 * 1024:
                f.close()
                dest.unlink(missing_ok=True)
                raise HTTPException(status_code=413, detail="File too large")
            f.write(chunk)
    return str(dest.resolve())

def remove_file_safe(path: str):
    try:
        os.remove(path)
    except Exception:
        pass
