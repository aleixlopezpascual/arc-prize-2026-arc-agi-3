import json

from src.agents.openai_tool_agent import OpenAIToolAgent


class _FakeResponse:
    def __init__(self, body: bytes) -> None:
        self._body = body

    def __enter__(self):
        return self

    def __exit__(self, *exc_info: object) -> bool:
        return False

    def read(self) -> bytes:
        return self._body


def _capture_payload(monkeypatch) -> dict:
    captured: dict = {}

    def fake_urlopen(req, timeout=None, context=None):
        captured["payload"] = json.loads(req.data.decode("utf-8"))
        body = json.dumps({"choices": [{"message": {"content": "ok"}}]}).encode("utf-8")
        return _FakeResponse(body)

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    return captured


def test_payload_includes_seed_and_temperature_when_set(tmp_path, monkeypatch):
    captured = _capture_payload(monkeypatch)
    agent = OpenAIToolAgent(
        api_key="dummy", cache_path=tmp_path / "c.json", seed=7, temperature=0.6
    )
    assert agent._call_api("hi") == "ok"
    assert captured["payload"]["seed"] == 7
    assert captured["payload"]["temperature"] == 0.6


def test_payload_unchanged_when_seed_and_temperature_unset(tmp_path, monkeypatch):
    captured = _capture_payload(monkeypatch)
    agent = OpenAIToolAgent(api_key="dummy", cache_path=tmp_path / "c.json")
    agent._call_api("hi")
    assert "seed" not in captured["payload"]
    assert "temperature" not in captured["payload"]
