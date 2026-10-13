import json

from fastapi.testclient import TestClient

from ai_platform.main import app

client = TestClient(app)


def test_health():
    assert client.get("/health").json() == {"status": "ok"}


def test_providers_list():
    data = client.get("/providers").json()
    assert "groq" in data["available"]


def test_chat_ok(monkeypatch):
    async def fake(prompt, provider=None):
        return "fake reply", "fake"

    monkeypatch.setattr("ai_platform.main.generate", fake)
    r = client.post("/chat", json={"message": "unique test message", "use_cache": False})
    assert r.status_code == 200
    assert r.json()["reply"] == "fake reply"
    assert r.json()["provider"] == "fake"


def test_chat_validation_error():
    r = client.post("/chat", json={"message": ""})
    assert r.status_code == 422


def test_chat_stream(monkeypatch):
    async def fake_stream(prompt, provider=None):
        for t in ["Hel", "lo"]:
            yield t, "fake"

    monkeypatch.setattr("ai_platform.main.stream_generate", fake_stream)
    r = client.post(
        "/chat/stream", json={"message": "stream test unique", "use_cache": False}
    )
    events = [json.loads(b[6:]) for b in r.text.split("\n\n") if b.startswith("data: ")]
    assert events[0]["type"] == "meta"
    assert "".join(e["text"] for e in events if e["type"] == "token") == "Hello"
    assert events[-1]["type"] == "done"