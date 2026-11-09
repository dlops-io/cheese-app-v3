"""The chat routes, the same for every mode. A mode only supplies `respond`, which turns the chat so
far and a new message into a reply.

Nothing about a chat stays in memory: each message rebuilds the conversation from the saved history,
so any copy of the API can answer it. The routes are plain `def` because Gemini, Chroma and the CNN
are blocking calls: FastAPI runs a `def` route in a thread, so one slow answer does not stop the API.
"""

import time
import uuid
from collections.abc import Callable
from typing import Annotated

from fastapi import APIRouter, Header, HTTPException, Path, Response

from api.utils.chat_utils import ChatHistoryManager, ChatMessage

# Both ids end up in file paths, so only a UUID gets through
UUID_PATTERN = r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
SessionId = Annotated[str, Header(alias="X-Session-ID", pattern=UUID_PATTERN)]
ChatId = Annotated[str, Path(pattern=UUID_PATTERN)]
MessageId = Annotated[str, Path(pattern=UUID_PATTERN)]


def make_title(message: ChatMessage) -> str:
    title = message.content or "Image chat"
    return f"{title[:50]}..." if len(title) > 50 else title


def create_router(model: str, respond: Callable[[ChatHistoryManager, list[dict], dict], dict]) -> APIRouter:
    router = APIRouter()
    chat_manager = ChatHistoryManager(model=model)

    def add_turn(chat: dict, message: ChatMessage, session_id: str) -> dict:
        if not message.content and not message.image:
            raise HTTPException(status_code=422, detail="Message must contain text or an image")

        user_message = {**message.model_dump(), "message_id": str(uuid.uuid4()), "role": "user"}
        reply = respond(chat_manager, chat["messages"], user_message)
        chat["messages"] += [user_message, {"message_id": str(uuid.uuid4()), **reply}]
        chat_manager.save_chat(chat, session_id)
        return chat

    @router.get("/chats")
    def get_chats(x_session_id: SessionId, limit: int | None = None):
        """Get all chats, optionally limited to a specific number"""
        return chat_manager.get_recent_chats(x_session_id, limit)

    @router.get("/chats/{chat_id}")
    def get_chat(chat_id: ChatId, x_session_id: SessionId):
        """Get a specific chat by ID"""
        chat = chat_manager.get_chat(chat_id, x_session_id)
        if not chat:
            raise HTTPException(status_code=404, detail="Chat not found")
        return chat

    @router.post("/chats")
    def start_chat(message: ChatMessage, x_session_id: SessionId):
        """Start a new chat with an initial message"""
        chat = {
            "chat_id": str(uuid.uuid4()),
            "title": make_title(message),
            "dts": int(time.time()),
            "messages": [],
        }
        return add_turn(chat, message, x_session_id)

    @router.post("/chats/{chat_id}")
    def continue_chat(chat_id: ChatId, message: ChatMessage, x_session_id: SessionId):
        """Add a message to an existing chat"""
        chat = chat_manager.get_chat(chat_id, x_session_id)
        if not chat:
            raise HTTPException(status_code=404, detail="Chat not found")
        chat["dts"] = int(time.time())
        return add_turn(chat, message, x_session_id)

    @router.get("/images/{chat_id}/{message_id}.png")
    def get_chat_image(chat_id: ChatId, message_id: MessageId):
        """Serve an image from the chat history"""
        image = chat_manager.load_image(chat_manager.image_name(chat_id, message_id))
        if image is None:
            raise HTTPException(status_code=404, detail="Image not found")
        return Response(image, media_type="image/png")

    return router
