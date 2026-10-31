import base64
import json
import os
from pathlib import Path

from fastapi import HTTPException
from pydantic import BaseModel, Field

from api import settings


class ChatMessage(BaseModel):
    content: str | None = Field(None, description="The message content")
    image: str | None = Field(None, description="The image content")


def decode_image(image: str) -> bytes:
    """A base64 image, with or without its `data:image/...;base64,` prefix, as bytes"""
    try:
        return base64.b64decode(image.split(",", 1)[-1], validate=True)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Image processing failed: {e}")


class ChatHistoryManager:
    """Keeps each chat as a JSON file, and its images as files next to it."""

    def __init__(self, model: str, history_dir: str = "chat-history"):
        self.history_dir = os.path.join(settings.PERSISTENT_DIR, history_dir, model)
        self.images_dir = os.path.join(self.history_dir, "images")

    def _chat_path(self, chat_id: str, session_id: str) -> str:
        return os.path.join(self.history_dir, session_id, f"{chat_id}.json")

    def image_path(self, chat_id: str, message_id: str) -> Path:
        return Path(self.images_dir, chat_id, f"{message_id}.png")

    def _save_image(self, chat_id: str, message_id: str, image: str) -> str:
        """Save an image to a file and return its path relative to the chat history"""
        path = self.image_path(chat_id, message_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(decode_image(image))
        return os.path.relpath(path, self.history_dir)

    def load_image(self, relative_path: str) -> bytes | None:
        path = Path(self.history_dir, relative_path)
        return path.read_bytes() if path.exists() else None

    def save_chat(self, chat: dict, session_id: str) -> None:
        """Save a chat to a file. Images are saved separately and replaced by their path."""
        for message in chat["messages"]:
            if message.get("image"):
                message["image_path"] = self._save_image(
                    chat["chat_id"], message["message_id"], message["image"]
                )
            message.pop("image", None)

        os.makedirs(os.path.join(self.history_dir, session_id), exist_ok=True)
        with open(self._chat_path(chat["chat_id"], session_id), "w", encoding="utf-8") as f:
            json.dump(chat, f, indent=2, ensure_ascii=False)

    def get_chat(self, chat_id: str, session_id: str) -> dict | None:
        """Get a specific chat by ID, or None if there is no such chat"""
        try:
            with open(self._chat_path(chat_id, session_id), encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            return None

    def get_recent_chats(self, session_id: str, limit: int | None = None) -> list[dict]:
        """Get recent chats, newest first, optionally limited to a specific number"""
        chats = []
        for path in Path(self.history_dir, session_id).glob("*.json"):
            with path.open(encoding="utf-8") as f:
                chats.append(json.load(f))
        chats.sort(key=lambda chat: chat.get("dts", 0), reverse=True)
        return chats[:limit] if limit else chats
