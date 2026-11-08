from fastapi import APIRouter, Depends

from app.core.deps import get_chat_service, get_current_user
from app.db.models import User
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.chat_service import ChatService

router = APIRouter(prefix="/api/chat", tags=["chat"])


# Plain `def` (not async): retrieval and the LLM call are blocking, so FastAPI
# runs this in its threadpool instead of blocking the event loop.
@router.post("", response_model=ChatResponse)
def chat(
    data: ChatRequest,
    user: User = Depends(get_current_user),
    service: ChatService = Depends(get_chat_service),
):
    """Ask the placement assistant. Answers use only documents this user may access."""
    return service.answer(data.question, user)
