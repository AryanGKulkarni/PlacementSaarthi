"""Load a stored document (PDF/TXT) into cleaned text, one entry per page."""

import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path

from pypdf import PdfReader
from pypdf.errors import PdfReadError

from app.db.models import FileType


class LoaderError(Exception):
    """The file couldn't be read or contains no usable text."""


@dataclass
class Page:
    number: int | None  # 1-based page number for PDFs; None for TXT
    text: str


def load_pages(path: Path, file_type: FileType) -> list[Page]:
    if file_type is FileType.pdf:
        pages = _load_pdf(path)
    elif file_type is FileType.txt:
        pages = _load_txt(path)
    else:
        raise LoaderError(f"Unsupported file type: {file_type}")

    if not pages:
        raise LoaderError(
            "No extractable text found (is it a scanned/image-only PDF?)"
            if file_type is FileType.pdf
            else "File contains no text"
        )
    return pages


def _load_pdf(path: Path) -> list[Page]:
    try:
        reader = PdfReader(path)
        if reader.is_encrypted and not reader.decrypt(""):
            raise LoaderError("PDF is password-protected")

        pages = []
        for number, page in enumerate(reader.pages, start=1):
            text = clean_text(page.extract_text() or "")
            if text:
                pages.append(Page(number=number, text=text))
        return pages
    except PdfReadError as exc:
        raise LoaderError(f"Could not read PDF: {exc}") from exc


def _load_txt(path: Path) -> list[Page]:
    raw = path.read_bytes()
    for encoding in ("utf-8-sig", "cp1252"):
        try:
            text = raw.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    else:
        text = raw.decode("latin-1")  # never fails; last resort

    text = clean_text(text)
    return [Page(number=None, text=text)] if text else []


_HYPHEN_LINEBREAK = re.compile(r"(\w)-\n(\w)")  # "place-\nment" -> "placement"
_SPACES = re.compile(r"[ \t\f\v ]+")
_MANY_NEWLINES = re.compile(r"\n{3,}")


def clean_text(text: str) -> str:
    text = unicodedata.normalize("NFKC", text)  # ligatures (ﬁ -> fi), full-width chars, etc.
    text = text.replace("\x00", "").replace("\r\n", "\n").replace("\r", "\n")
    text = _HYPHEN_LINEBREAK.sub(r"\1\2", text)
    text = _SPACES.sub(" ", text)
    text = "\n".join(line.strip() for line in text.split("\n"))
    text = _MANY_NEWLINES.sub("\n\n", text)  # keep paragraph breaks, drop big gaps
    return text.strip()
