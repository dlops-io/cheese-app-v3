import uuid

import pytest
from google.api_core.exceptions import NotFound

from api.utils import chat_utils
from api.utils.chat_utils import ChatHistoryManager, GcsStorage, LocalStorage


class FakeBlob:
    def __init__(self, objects, name):
        self.objects = objects
        self.name = name

    def download_as_bytes(self):
        if self.name not in self.objects:
            raise NotFound("no such object")
        return self.objects[self.name]

    def upload_from_string(self, data):
        self.objects[self.name] = data


class FakeBucket:
    def __init__(self, objects):
        self.objects = objects
        self.client = self

    def blob(self, name):
        return FakeBlob(self.objects, name)

    def list_blobs(self, bucket, prefix, delimiter):
        # A delimiter means this folder only, like a real bucket
        return [
            FakeBlob(self.objects, name)
            for name in self.objects
            if name.startswith(prefix) and delimiter not in name[len(prefix) :]
        ]


def fake_gcs(objects):
    storage = GcsStorage.__new__(GcsStorage)
    storage.bucket = FakeBucket(objects)
    return storage


@pytest.fixture(params=["local", "gcs"])
def storage(request, tmp_path, monkeypatch):
    """Both kinds of storage have to behave the same"""
    chosen = LocalStorage(str(tmp_path)) if request.param == "local" else fake_gcs({})
    monkeypatch.setattr(chat_utils, "chat_storage", lambda: chosen)
    return chosen


def chat(chat_id, dts=1, image=None):
    message = {"message_id": str(uuid.uuid4()), "role": "user", "content": "hi", "image": image}
    return {"chat_id": chat_id, "title": "hi", "dts": dts, "messages": [message]}


def test_missing_things_are_none(storage):
    assert storage.read("nope") is None
    assert ChatHistoryManager("llm").get_chat("nope", "session") is None
    assert ChatHistoryManager("llm").get_recent_chats("session") == []


def test_a_saved_chat_comes_back(storage):
    manager = ChatHistoryManager("llm")
    manager.save_chat(chat("a"), "session")
    assert manager.get_chat("a", "session")["title"] == "hi"


def test_recent_chats_are_newest_first_and_stay_in_their_session(storage):
    manager = ChatHistoryManager("llm")
    manager.save_chat(chat("old", dts=1), "session")
    manager.save_chat(chat("new", dts=2), "session")
    manager.save_chat(chat("other", dts=3), "another-session")
    assert [c["chat_id"] for c in manager.get_recent_chats("session")] == ["new", "old"]
    assert [c["chat_id"] for c in manager.get_recent_chats("session", limit=1)] == ["new"]


def test_images_are_kept_apart_from_the_chat(storage):
    manager = ChatHistoryManager("llm")
    saved = chat("a", image="aGVsbG8=")
    manager.save_chat(saved, "session")
    message = manager.get_chat("a", "session")["messages"][0]
    assert "image" not in message
    assert manager.load_image(message["image_path"]) == b"hello"


def test_any_copy_of_the_api_sees_the_same_chats(monkeypatch):
    """Two pods, one bucket: this is what lets the API scale."""
    bucket = {}
    monkeypatch.setattr(chat_utils, "chat_storage", lambda: fake_gcs(bucket))
    ChatHistoryManager("llm").save_chat(chat("a"), "session")
    assert ChatHistoryManager("llm").get_chat("a", "session")["chat_id"] == "a"
