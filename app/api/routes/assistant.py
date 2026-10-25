"""
Assistant control and conversation API endpoints.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from app.core.assistant import get_assistant

router = APIRouter(prefix="/api/assistant", tags=["Assistant"])


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4096, description="User prompt text")


class ChatResponse(BaseModel):
    reply: str
    state: str
    intent: str
    conversation_id: str | None = None


class StateResponse(BaseModel):
    state: str
    previous_state: str
    last_transition_time: str


@router.get("/state", response_model=StateResponse)
def get_state():
    """Return current assistant state and transition metadata."""
    assistant = get_assistant()
    return StateResponse(
        state=assistant.state_manager.current_state.value,
        previous_state=assistant.state_manager.previous_state.value,
        last_transition_time=assistant.state_manager.last_transition_time.isoformat(),
    )


@router.post("/wake")
def wake_assistant():
    """Awaken Zero assistant."""
    assistant = get_assistant()
    greeting_or_briefing = assistant.wake(force_briefing=False)
    return {
        "status": "awakened",
        "state": assistant.state_manager.current_state.value,
        "message": greeting_or_briefing,
    }


@router.post("/sleep")
def sleep_assistant():
    """Transition Zero assistant to sleep mode."""
    assistant = get_assistant()
    sleep_message = assistant.sleep()
    return {
        "status": "sleeping",
        "state": assistant.state_manager.current_state.value,
        "message": sleep_message,
    }


@router.post("/chat", response_model=ChatResponse)
@router.post("/message", response_model=ChatResponse)
def chat_with_assistant(req: ChatRequest):
    """Send text message to Zero assistant and receive reply."""
    assistant = get_assistant()
    result = assistant.process_input(req.message)
    return ChatResponse(
        reply=result["reply_text"],
        state=result["state"],
        intent=result["intent"],
        conversation_id=result.get("conversation_id"),
    )
