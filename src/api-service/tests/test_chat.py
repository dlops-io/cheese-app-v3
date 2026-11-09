import uuid
from types import SimpleNamespace

import httpx
import pytest
from google.genai import errors

from api.utils import llm_rag_utils, llm_utils


def text_of(content):
    return [part.text for part in content.parts if part.text]


def test_chat_needs_a_session_id(client):
    assert client.get("/api/llm/chats").status_code == 422


def test_session_id_cannot_reach_other_folders(client):
    assert client.get("/api/llm/chats", headers={"X-Session-ID": "../../etc"}).status_code == 422


def test_empty_message_is_refused(client, session, gemini):
    assert client.post("/api/llm/chats", json={"content": ""}, headers=session).status_code == 422
    assert gemini == []


def test_unknown_chat_is_a_404(client, session):
    chat_id = uuid.uuid4()
    assert client.get(f"/api/llm/chats/{chat_id}", headers=session).status_code == 404
    response = client.post(f"/api/llm/chats/{chat_id}", json={"content": "hi"}, headers=session)
    assert response.status_code == 404


def test_new_chat_is_saved(client, session, gemini):
    chat = client.post("/api/llm/chats", json={"content": "What is Brie?"}, headers=session).json()

    assert chat["title"] == "What is Brie?"
    assert [m["role"] for m in chat["messages"]] == ["user", "assistant"]
    assert chat["messages"][1]["content"] == "answer 1"
    assert client.get(f"/api/llm/chats/{chat['chat_id']}", headers=session).json() == chat
    assert [c["chat_id"] for c in client.get("/api/llm/chats", headers=session).json()] == [chat["chat_id"]]


def test_chats_belong_to_their_session(client, session, gemini):
    chat = client.post("/api/llm/chats", json={"content": "hi"}, headers=session).json()
    other = {"X-Session-ID": str(uuid.uuid4())}
    assert client.get(f"/api/llm/chats/{chat['chat_id']}", headers=other).status_code == 404


def test_every_message_rebuilds_the_conversation_from_history(client, session, gemini):
    """Nothing is kept in memory, so any copy of the API can continue any chat."""
    chat = client.post("/api/llm/chats", json={"content": "first"}, headers=session).json()
    client.post(f"/api/llm/chats/{chat['chat_id']}", json={"content": "second"}, headers=session)

    history = gemini[1]["history"]
    assert [content.role for content in history] == ["user", "model"]
    assert text_of(history[0]) == ["first"]
    assert text_of(history[1]) == ["answer 1"]


def test_system_instruction_reaches_gemini(client, session, monkeypatch):
    created = {}

    class FakeChat:
        def send_message(self, parts):
            return type("Response", (), {"text": "ok"})

    def fake_create(**kwargs):
        created.update(kwargs)
        return FakeChat()

    monkeypatch.setattr(llm_utils, "llm_client", SimpleNamespace(chats=SimpleNamespace(create=fake_create)))
    client.post("/api/llm/chats", json={"content": "hi"}, headers=session)
    assert created["config"].system_instruction == llm_utils.SYSTEM_INSTRUCTION


def test_gemini_failure_is_a_502(client, session, monkeypatch):
    class FailingChat:
        def send_message(self, parts):
            raise errors.ClientError(404, {"error": {"message": "model retired"}})

    chats = SimpleNamespace(create=lambda **_: FailingChat())
    monkeypatch.setattr(llm_utils, "llm_client", SimpleNamespace(chats=chats))
    response = client.post("/api/llm/chats", json={"content": "hi"}, headers=session)
    assert response.status_code == 502
    assert "model retired" in response.json()["detail"]


def test_image_chat_keeps_the_image_for_later(client, session, gemini, jpeg):
    chat = client.post("/api/llm/chats", json={"image": jpeg}, headers=session).json()
    assert chat["title"] == "Image chat"
    user_message = chat["messages"][0]
    assert "image" not in user_message

    url = f"/api/llm/{user_message['image_path']}"
    assert client.get(url).status_code == 200

    client.post(f"/api/llm/chats/{chat['chat_id']}", json={"content": "and this?"}, headers=session)
    first_turn = gemini[1]["history"][0]
    assert first_turn.parts[0].inline_data.mime_type == "image/jpeg"
    assert text_of(first_turn) == [llm_utils.IMAGE_PROMPT]


def test_bad_image_is_a_400(client, session, gemini):
    response = client.post("/api/llm/chats", json={"image": "bm90IGFuIGltYWdl"}, headers=session)
    assert response.status_code == 400
    assert gemini == []


def test_cnn_prediction_reaches_the_next_question(client, session, gemini, cnn, jpeg):
    chat = client.post("/api/llm-cnn/chats", json={"image": jpeg}, headers=session).json()
    reply = chat["messages"][1]
    assert reply["role"] == "cnn"
    assert reply["results"]["prediction_label"] == "brie"
    assert gemini == []

    url = f"/api/llm-cnn/chats/{chat['chat_id']}"
    client.post(url, json={"content": "What goes with it?"}, headers=session)
    assert "identified the image of a cheese as brie" in text_of(gemini[0]["history"][-1])[0]


def test_cnn_can_take_a_second_image(client, session, cnn, jpeg):
    chat = client.post("/api/llm-cnn/chats", json={"image": jpeg}, headers=session).json()
    url = f"/api/llm-cnn/chats/{chat['chat_id']}"
    chat = client.post(url, json={"image": jpeg}, headers=session).json()
    assert [m["role"] for m in chat["messages"]] == ["user", "cnn", "user", "cnn"]


def test_cnn_still_loading_is_a_503(client, session, jpeg):
    assert client.post("/api/llm-cnn/chats", json={"image": jpeg}, headers=session).status_code == 503


@pytest.fixture
def chunks(monkeypatch):
    monkeypatch.setattr(llm_rag_utils, "find_chunks", lambda query: ["Brie is soft.", "Brie is French."])


def test_rag_sends_the_chunks_to_gemini(client, session, gemini, chunks):
    client.post("/api/llm-rag/chats", json={"content": "What is Brie?"}, headers=session)
    assert gemini[0]["parts"] == ["What is Brie?\nBrie is soft.\nBrie is French."]
    assert gemini[0]["system_instruction"] == llm_rag_utils.SYSTEM_INSTRUCTION


def test_rag_without_chroma_is_a_503(client, session, monkeypatch):
    monkeypatch.setattr(llm_rag_utils, "generate_query_embedding", lambda query: [0.0])

    def no_chroma():
        raise ValueError("Could not connect to a Chroma server")

    monkeypatch.setattr(llm_rag_utils, "chroma_client", no_chroma)
    response = client.post("/api/llm-rag/chats", json={"content": "hi"}, headers=session)
    assert response.status_code == 503
    assert "Chroma" in response.json()["detail"]


def test_chroma_going_away_after_connecting_is_a_503(client, session, monkeypatch):
    def unreachable(name):
        raise httpx.ConnectError("Name or service not known")

    monkeypatch.setattr(llm_rag_utils, "generate_query_embedding", lambda query: [0.0])
    monkeypatch.setattr(llm_rag_utils, "chroma_client", lambda: SimpleNamespace(get_collection=unreachable))
    response = client.post("/api/llm-rag/chats", json={"content": "hi"}, headers=session)
    assert response.status_code == 503
    assert "Chroma" in response.json()["detail"]
