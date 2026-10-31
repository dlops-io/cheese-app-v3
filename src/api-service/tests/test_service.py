from api.routers import chat
from api.utils import llm_rag_utils


def test_docs_are_served_under_api(client):
    assert client.get("/api/docs").status_code == 200
    assert client.get("/api/status").json() == {"version": "3.0.0"}


def test_newsletters_need_no_redirect(client):
    response = client.get("/api/newsletters", params={"limit": 2}, follow_redirects=False)
    assert response.status_code == 200
    assert len(response.json()) == 2


def test_missing_content_is_a_404(client):
    assert client.get("/api/newsletters/nope").status_code == 404
    assert client.get("/api/newsletters/image/nope.png").status_code == 404
    assert client.get("/api/podcasts/nope").status_code == 404
    assert client.get("/api/podcasts/audio/nope.mp3").status_code == 404


def test_podcasts(client):
    podcast = client.get("/api/podcasts", params={"limit": 1}, follow_redirects=False).json()[0]
    assert client.get(f"/api/podcasts/{podcast['id']}").json() == podcast


def test_liveness_needs_nothing(client):
    assert client.get("/healthz").json() == {"ok": True}


def test_not_ready_until_the_model_is_loaded(client):
    response = client.get("/readyz")
    assert response.status_code == 503
    assert "CNN" in response.json()["detail"]


def test_not_ready_without_chroma(client, cnn, monkeypatch):
    def no_chroma():
        raise ValueError("Could not connect to a Chroma server")

    monkeypatch.setattr(llm_rag_utils, "chroma_client", no_chroma)
    response = client.get("/readyz")
    assert response.status_code == 503
    assert "Chroma" in response.json()["detail"]


def test_ready(client, cnn, monkeypatch):
    fake_chroma = type("Client", (), {"heartbeat": lambda self: 1})()
    monkeypatch.setattr(llm_rag_utils, "chroma_client", lambda: fake_chroma)
    assert client.get("/readyz").status_code == 200


def test_long_title_is_cut():
    message = chat.ChatMessage(content="x" * 60)
    assert chat.make_title(message) == "x" * 50 + "..."
