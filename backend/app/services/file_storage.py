import hashlib
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from app.core.config import settings
from app.core.exceptions import BadRequestError, PayloadTooLargeError
from app.db.models import FileType

READ_CHUNK = 1024 * 1024  # 1 MB


class AsyncReadable(Protocol):
    async def read(self, size: int = -1) -> bytes: ...


@dataclass
class TempFile:
    path: Path
    size_bytes: int
    sha256: str

    def discard(self) -> None:
        self.path.unlink(missing_ok=True)


async def save_to_temp(source: AsyncReadable, file_type: FileType) -> TempFile:
    """Stream an upload to a temp file, enforcing the size limit and hashing as we go."""
    max_bytes = settings.max_upload_mb * 1024 * 1024
    tmp_path = settings.upload_dir / f".tmp-{uuid.uuid4()}"
    sha = hashlib.sha256()
    size = 0
    first = True

    try:
        with tmp_path.open("wb") as out:
            while chunk := await source.read(READ_CHUNK):
                if first:
                    first = False
                    _check_content(chunk, file_type)
                size += len(chunk)
                if size > max_bytes:
                    raise PayloadTooLargeError(f"File exceeds {settings.max_upload_mb} MB limit")
                sha.update(chunk)
                out.write(chunk)
    except BaseException:
        tmp_path.unlink(missing_ok=True)
        raise

    if size == 0:
        tmp_path.unlink(missing_ok=True)
        raise BadRequestError("File is empty")

    return TempFile(tmp_path, size, sha.hexdigest())


def promote(temp: TempFile, stored_filename: str) -> Path:
    """Move a temp file to its final name in the upload directory."""
    final_path = settings.upload_dir / stored_filename
    temp.path.replace(final_path)
    return final_path


def _check_content(first_chunk: bytes, file_type: FileType) -> None:
    if file_type is FileType.pdf and not first_chunk.startswith(b"%PDF-"):
        raise BadRequestError("File is not a valid PDF")
    if file_type is FileType.txt and b"\x00" in first_chunk:
        raise BadRequestError("File is not a text file")
