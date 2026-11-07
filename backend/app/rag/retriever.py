"""Question + user -> the relevant, access-checked chunks to give the LLM.

Steps: validate -> embed -> access filter -> over-fetch from Chroma ->
relevance threshold -> dedupe / per-document cap -> context budget -> numbered result.
"""

import logging
from dataclasses import dataclass, field
from typing import Any

from app.core.config import settings
from app.core.exceptions import BadRequestError
from app.db.models import Role, User
from app.rag.embedder import Embedder
from app.rag.vector_store import ALL_DEPARTMENTS, SearchHit, VectorStore

log = logging.getLogger(__name__)


@dataclass
class RetrievedChunk:
    ref: int              # 1-based; the LLM cites it as [ref]
    text: str
    doc_id: str
    filename: str
    page: int | None
    chunk_no: int
    distance: float


@dataclass
class Source:
    doc_id: str
    filename: str
    pages: list[int] = field(default_factory=list)
    refs: list[int] = field(default_factory=list)


@dataclass
class RetrievalResult:
    question: str
    chunks: list[RetrievedChunk]
    sources: list[Source]
    candidates: int  # hits returned by Chroma before filtering (useful for debugging/eval)

    @property
    def found(self) -> bool:
        return bool(self.chunks)


def access_filter(user: User | None) -> dict[str, Any] | None:
    """Chroma `where` filter for what this user may read.

    admin                      -> None (everything)
    student / faculty          -> shared documents + their own department
    no user / no profile yet   -> shared documents only (safe default)
    """
    if user is not None and user.role is Role.admin:
        return None

    department_id = _department_of(user)
    if department_id is None:
        return {"department_id": ALL_DEPARTMENTS}
    return {"department_id": {"$in": [ALL_DEPARTMENTS, department_id]}}


def _department_of(user: User | None) -> int | None:
    if user is None:
        return None
    if user.role is Role.student and user.student_profile is not None:
        return user.student_profile.department_id
    if user.role is Role.faculty and user.faculty_profile is not None:
        return user.faculty_profile.department_id
    return None


class Retriever:
    def __init__(self, embedder: Embedder, vector_store: VectorStore):
        self.embedder = embedder
        self.vector_store = vector_store

    def retrieve(self, question: str, user: User | None) -> RetrievalResult:
        question = self._validate(question)
        where = access_filter(user)

        query_vector = self.embedder.embed_query(question)
        hits = self.vector_store.query(query_vector, k=settings.retrieval_fetch_k, where=where)

        relevant = [h for h in hits if h.distance <= settings.retrieval_max_distance]
        selected = self._select(relevant)
        chunks = [self._to_chunk(ref, hit) for ref, hit in enumerate(selected, start=1)]

        log.info(
            "retrieve role=%s filter=%s candidates=%d relevant=%d selected=%d best=%s",
            getattr(user, "role", None),
            where,
            len(hits),
            len(relevant),
            len(chunks),
            f"{hits[0].distance:.3f}" if hits else "-",
        )
        return RetrievalResult(
            question=question,
            chunks=chunks,
            sources=self._sources(chunks),
            candidates=len(hits),
        )

    # ---- steps ------------------------------------------------------------

    @staticmethod
    def _validate(question: str) -> str:
        question = " ".join((question or "").split())  # collapse whitespace/newlines
        if not question:
            raise BadRequestError("Question is empty")
        if len(question) > settings.max_question_chars:
            raise BadRequestError(f"Question is too long (max {settings.max_question_chars} characters)")
        return question

    @staticmethod
    def _select(hits: list[SearchHit]) -> list[SearchHit]:
        """Hits arrive sorted by distance. Keep the best ones, skipping duplicates,
        capping chunks per document, and staying within the context budget."""
        selected: list[SearchHit] = []
        seen_texts: set[str] = set()
        per_doc: dict[str, int] = {}
        total_chars = 0

        for hit in hits:
            if len(selected) >= settings.retrieval_top_k:
                break

            fingerprint = " ".join(hit.text.lower().split())
            if fingerprint in seen_texts:  # same text in two files (e.g. re-uploaded content)
                continue

            doc_id = str(hit.metadata.get("doc_id", ""))
            if per_doc.get(doc_id, 0) >= settings.retrieval_max_per_doc:
                continue

            if total_chars + len(hit.text) > settings.retrieval_max_context_chars:
                continue  # a later, shorter chunk may still fit

            selected.append(hit)
            seen_texts.add(fingerprint)
            per_doc[doc_id] = per_doc.get(doc_id, 0) + 1
            total_chars += len(hit.text)

        return selected

    @staticmethod
    def _to_chunk(ref: int, hit: SearchHit) -> RetrievedChunk:
        m = hit.metadata
        return RetrievedChunk(
            ref=ref,
            text=hit.text,
            doc_id=str(m.get("doc_id", "")),
            filename=str(m.get("filename", "unknown")),
            page=m.get("page"),
            chunk_no=int(m.get("chunk_no", -1)),
            distance=hit.distance,
        )

    @staticmethod
    def _sources(chunks: list[RetrievedChunk]) -> list[Source]:
        """One entry per document, in order of first appearance (i.e. best match first)."""
        by_doc: dict[str, Source] = {}
        for c in chunks:
            src = by_doc.setdefault(c.doc_id, Source(doc_id=c.doc_id, filename=c.filename))
            src.refs.append(c.ref)
            if c.page is not None and c.page not in src.pages:
                src.pages.append(c.page)
        return list(by_doc.values())
