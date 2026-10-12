import json


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