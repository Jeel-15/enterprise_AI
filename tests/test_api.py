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