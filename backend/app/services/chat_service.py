import logging
import time

from app.core.exceptions import ServiceUnavailableError
from app.db.models import User
from app.rag.embedder import EmbeddingError
from app.rag.llm import LLMClient, LLMError
from app.rag.prompts import NOT_FOUND_ANSWER, build_messages
from app.rag.retriever import Retriever
from app.rag.user_context import build_asker_context
from app.rag.vector_store import VectorStoreError
from app.schemas.chat import ChatResponse, SourceOut

log = logging.getLogger("uvicorn.error")


class ChatService:
    def __init__(self, retriever: Retriever, llm: LLMClient):
        self.retriever = retriever
        self.llm = llm

    def answer(self, question: str, user: User) -> ChatResponse:
        started = time.perf_counter()

        try:
            retrieval = self.retriever.retrieve(question, user)
        except (EmbeddingError, VectorStoreError) as exc:
            log.error("Retrieval failed: %s", exc)
            raise ServiceUnavailableError("Search is temporarily unavailable. Please try again shortly.") from exc

        sources = [
            SourceOut(doc_id=s.doc_id, filename=s.filename, pages=s.pages, refs=s.refs)
            for s in retrieval.sources
        ]

        # Nothing relevant (or nothing this user may see): don't ask the LLM to guess.
        if not retrieval.found:
            return ChatResponse(
                answer=NOT_FOUND_ANSWER,
                found=False,
                sources=[],
                duration_ms=_elapsed_ms(started),
            )

        messages = build_messages(retrieval.question, retrieval, build_asker_context(user))
        try:
            result = self.llm.chat(messages)
        except LLMError as exc:
            log.error("LLM failed: %s", exc)
            raise ServiceUnavailableError("The assistant is temporarily unavailable. Please try again shortly.") from exc

        log.info(
            "chat role=%s chunks=%d prompt_tokens=%s answer_tokens=%s llm_ms=%s",
            user.role.value,
            len(retrieval.chunks),
            result.prompt_tokens,
            result.completion_tokens,
            result.duration_ms,
        )
        return ChatResponse(
            answer=result.content,
            found=True,
            sources=sources,
            model=result.model,
            duration_ms=_elapsed_ms(started),
        )


def _elapsed_ms(started: float) -> int:
    return int((time.perf_counter() - started) * 1000)
