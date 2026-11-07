"""Split page text into overlapping chunks for embedding.

Recursive strategy: try to split on the "largest" boundary first (paragraph),
falling back to line, sentence, clause and word boundaries, and finally a hard
character cut. Small pieces are then merged back up to ~chunk_size, carrying a
tail of ~overlap characters into the next chunk so context isn't lost at edges.
"""

from dataclasses import dataclass

from app.core.config import settings
from app.rag.loader import Page

SEPARATORS = ["\n\n", "\n", ". ", "? ", "! ", "; ", ", ", " "]


@dataclass
class Chunk:
    text: str
    page: int | None  # page the chunk came from (None for TXT)
    chunk_no: int     # 0-based position within the document


def chunk_pages(
    pages: list[Page],
    chunk_size: int | None = None,
    overlap: int | None = None,
    min_chars: int | None = None,
) -> list[Chunk]:
    """Chunk each page separately so every chunk maps to exactly one page (for citations)."""
    chunk_size = chunk_size or settings.chunk_size
    overlap = settings.chunk_overlap if overlap is None else overlap
    min_chars = settings.min_chunk_chars if min_chars is None else min_chars

    chunks: list[Chunk] = []
    for page in pages:
        for text in split_text(page.text, chunk_size, overlap):
            if len(text) >= min_chars:  # drop stray headers/footers like "Page 3"
                chunks.append(Chunk(text=text, page=page.number, chunk_no=len(chunks)))
    return chunks


def split_text(text: str, chunk_size: int, overlap: int) -> list[str]:
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")
    if not 0 <= overlap < chunk_size:
        raise ValueError("overlap must be >= 0 and smaller than chunk_size")

    text = text.strip()
    if not text:
        return []
    pieces = _split_recursive(text, SEPARATORS, chunk_size)
    return _merge(pieces, chunk_size, overlap)


def _split_recursive(text: str, separators: list[str], chunk_size: int) -> list[str]:
    """Break text into pieces no longer than chunk_size, using the coarsest separator possible."""
    if len(text) <= chunk_size:
        return [text]

    for i, sep in enumerate(separators):
        if sep not in text:
            continue
        parts = text.split(sep)
        pieces: list[str] = []
        for j, part in enumerate(parts):
            piece = part + sep if j < len(parts) - 1 else part  # keep the separator attached
            if not piece:
                continue
            if len(piece) > chunk_size:
                pieces.extend(_split_recursive(piece, separators[i + 1 :], chunk_size))
            else:
                pieces.append(piece)
        return pieces

    # No separator left (e.g. one giant "word"): hard cut.
    return [text[k : k + chunk_size] for k in range(0, len(text), chunk_size)]


def _merge(pieces: list[str], chunk_size: int, overlap: int) -> list[str]:
    """Greedily join pieces into chunks of <= chunk_size, keeping ~overlap chars of tail."""
    chunks: list[str] = []
    current: list[str] = []
    length = 0

    for piece in pieces:
        if current and length + len(piece) > chunk_size:
            chunk = "".join(current).strip()
            if chunk:
                chunks.append(chunk)
            # Drop pieces from the front until only the overlap tail remains
            # and the next piece fits.
            while current and (length > overlap or length + len(piece) > chunk_size):
                length -= len(current.pop(0))
        current.append(piece)
        length += len(piece)

    tail = "".join(current).strip()
    if tail:
        chunks.append(tail)
    return chunks
