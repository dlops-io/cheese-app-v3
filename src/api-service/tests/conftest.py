import base64
import io
import os
import tempfile
import uuid

import pytest
from fastapi.testclient import TestClient
from PIL import Image

# Before anything imports api.settings
os.environ["GCP_PROJECT"] = "test-project"
os.environ["PERSISTENT_DIR"] = tempfile.mkdtemp()

from api import service
from api.utils import llm_cnn_utils, llm_utils


@pytest.fixture
def client():
    """No lifespan: the tests never load the real CNN model"""
    return TestClient(service.app)


@pytest.fixture
def session():
    return {"X-Session-ID": str(uuid.uuid4())}


@pytest.fixture
def gemini(monkeypatch):
    """Stands in for Gemini and records every call it gets"""
    calls = []

    def fake_ask_gemini(system_instruction, history, parts):
        calls.append({"system_instruction": system_instruction, "history": history, "parts": parts})
        return f"answer {len(calls)}"

    monkeypatch.setattr(llm_utils, "ask_gemini", fake_ask_gemini)
    monkeypatch.setattr("api.utils.llm_rag_utils.ask_gemini", fake_ask_gemini)
    return calls


@pytest.fixture
def cnn(monkeypatch):
    """A loaded CNN that always sees a Brie"""
    monkeypatch.setattr(llm_cnn_utils, "cnn_model", object())
    monkeypatch.setattr(
        llm_cnn_utils, "make_prediction", lambda _: {"prediction_label": "brie", "accuracy": 98.5}
    )


@pytest.fixture
def jpeg():
    buffer = io.BytesIO()
    Image.new("RGB", (4, 4), "yellow").save(buffer, format="JPEG")
    return "data:image/jpeg;base64," + base64.b64encode(buffer.getvalue()).decode()
