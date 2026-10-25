"""
Conversation history search and management REST API endpoints for Zero AI.
"""

import logging
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from app.memory.conversation_store import ConversationStore

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/conversations", tags=["Conversations"])


@router.get("")
def list_conversations(limit: int = Query(default=50, ge=1, le=200)):
    """List recent conversations."""
    convs = ConversationStore.list_conversations(limit=limit)
    return {
        "count": len(convs),
        "conversations": [
            {
                "id": c.id,
                "title": c.title,
                "created_at": c.created_at.isoformat(),
                "updated_at": c.updated_at.isoformat(),
                "summary": c.summary,
            }
            for c in convs
        ],
    }


@router.get("/search")
def search_conversations(query: str = Query(..., min_length=1, description="Keyword search query")):
    """Search conversation titles and message contents."""
    conv_matches = ConversationStore.search_conversations(query)
    msg_matches = ConversationStore.search_messages(query)

    return {
        "query": query,
        "matched_conversations_count": len(conv_matches),
        "matched_messages_count": len(msg_matches),
        "conversations": [
            {
                "id": c.id,
                "title": c.title,
                "updated_at": c.updated_at.isoformat(),
            }
            for c in conv_matches
        ],
        "messages": [
            {
                "id": m.id,
                "conversation_id": m.conversation_id,
                "role": m.role,
                "content": m.content,
                "timestamp": m.timestamp.isoformat(),
            }
            for m in msg_matches
        ],
    }


@router.get("/{conv_id}")
def get_conversation_detail(conv_id: str):
    """Retrieve all messages for a specific conversation thread."""
    messages = ConversationStore.get_messages(conv_id)
    return {
        "conversation_id": conv_id,
        "message_count": len(messages),
        "messages": [
            {
                "id": m.id,
                "role": m.role,
                "content": m.content,
                "timestamp": m.timestamp.isoformat(),
                "intent": m.intent,
            }
            for m in messages
        ],
    }


@router.delete("/{conv_id}")
def delete_conversation(conv_id: str):
    """Delete a conversation thread and its messages."""
    success = ConversationStore.delete_conversation(conv_id)
    if not success:
        raise HTTPException(status_code=404, detail="Conversation not found.")
    return {"status": "deleted", "conversation_id": conv_id}


@router.delete("")
def clear_all_history():
    """Clear all conversation history."""
    ConversationStore.clear_all_conversations()
    return {"status": "cleared", "message": "All conversations have been deleted."}
