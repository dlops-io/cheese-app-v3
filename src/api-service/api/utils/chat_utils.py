import base64
import json
from functools import cache
from pathlib import Path

from fastapi import HTTPException
from google.api_core.exceptions import NotFound
from google.cloud import storage
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


class LocalStorage:
    """Files in a folder: one API on one laptop."""

    def __init__(self, root: str):
        self.root = Path(root)

    def read(self, path: str) -> bytes | None:
        file = self.root / path
        return file.read_bytes() if file.exists() else None

    def write(self, path: str, data: bytes) -> None:
        file = self.root / path
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_bytes(data)

    def list(self, folder: str) -> list[str]:
        return [str(file.relative_to(self.root)) for file in (self.root / folder).glob("*.json")]


class GcsStorage:
    """Objects in a Cloud Storage bucket: every copy of the API sees the same chats, and they outlive
    the pods and the cluster."""

    def __init__(self, bucket: str):
        self.bucket = storage.Client().bucket(bucket)

    def read(self, path: str) -> bytes | None:
        try:
            return self.bucket.blob(path).download_as_bytes()
        except NotFound:
            return None

    def write(self, path: str, data: bytes) -> None:
        self.bucket.blob(path).upload_from_string(data)

    def list(self, folder: str) -> list[str]:
        blobs = self.bucket.client.list_blobs(self.bucket, prefix=f"{folder}/", delimiter="/")
        return [blob.name for blob in blobs if blob.name.endswith(".json")]


@cache
def chat_storage() -> LocalStorage | GcsStorage:
    """Connect on first use. Set CHAT_BUCKET to keep chats in Cloud Storage."""
    if settings.CHAT_BUCKET:
        return GcsStorage(settings.CHAT_BUCKET)
    return LocalStorage(settings.PERSISTENT_DIR)


class ChatHistoryManager:
    """Keeps each chat as JSON, and its images next to it."""

    def __init__(self, model: str, history_dir: str = "chat-history"):
        self.history_dir = f"{history_dir}/{model}"

    def _chat_path(self, chat_id: str, session_id: str) -> str:
        return f"{self.history_dir}/{session_id}/{chat_id}.json"

    def image_name(self, chat_id: str, message_id: str) -> str:
        """An image's path relative to the chat history: this is what a saved message keeps"""
        return f"images/{chat_id}/{message_id}.png"

    def load_image(self, image_name: str) -> bytes | None:
        return chat_storage().read(f"{self.history_dir}/{image_name}")

    def save_chat(self, chat: dict, session_id: str) -> None:
        """Save a chat. Images are saved separately and replaced by their path."""
        for message in chat["messages"]:
            if message.get("image"):
                image_name = self.image_name(chat["chat_id"], message["message_id"])
                chat_storage().write(f"{self.history_dir}/{image_name}", decode_image(message["image"]))
                message["image_path"] = image_name
            message.pop("image", None)

        data = json.dumps(chat, indent=2, ensure_ascii=False).encode("utf-8")
        chat_storage().write(self._chat_path(chat["chat_id"], session_id), data)

    def get_chat(self, chat_id: str, session_id: str) -> dict | None:
        """Get a specific chat by ID, or None if there is no such chat"""
        data = chat_storage().read(self._chat_path(chat_id, session_id))
        return json.loads(data) if data else None

    def get_recent_chats(self, session_id: str, limit: int | None = None) -> list[dict]:
        """Get recent chats, newest first, optionally limited to a specific number"""
        paths = chat_storage().list(f"{self.history_dir}/{session_id}")
        chats = [json.loads(chat_storage().read(path)) for path in paths]
        chats.sort(key=lambda chat: chat.get("dts", 0), reverse=True)
        return chats[:limit] if limit else chats
