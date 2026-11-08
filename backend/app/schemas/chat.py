from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=500, examples=["Is there a bond at Ironclad?"])


class SourceOut(BaseModel):
    doc_id: str
    filename: str
    pages: list[int]
    refs: list[int]  # citation numbers in the answer that point to this document


class ChatResponse(BaseModel):
    answer: str
    found: bool               # False -> no relevant material, LLM was not called
    sources: list[SourceOut]
    model: str | None = None
    duration_ms: int          # total time for this request
