import asyncio
import json
import types
import pytest

from gotaglio.models import AzureOpenAIRealtime
from gotaglio.realtime_utils import assert_strictly_increasing_sequences, save_events_jsonl

class DummyRegistry:
    def register_model(self, name, model):
        setattr(self, name, model)

@pytest.mark.asyncio
async def test_realtime_model_happy_path(monkeypatch, tmp_path):
    # Prepare model with minimal config
    registry = DummyRegistry()
    model = AzureOpenAIRealtime(registry, {
        "name": "azure-realtime",
        "type": "AZURE_OPEN_AI_REALTIME",
        "endpoint": "https://example.openai.azure.com",
        "api": "2024-06-01",
        "deployment": "gpt-4o-realtime-preview",
        "key": "sk-test",
        "sample_rate_hz": 16000,
        "timeout_s": 3,
    })

    # Fake audio bytes
    audio_path = tmp_path / "hello.wav"
    audio_path.write_bytes(b"FAKEAUDIO")

    # Mock websockets.connect context manager
    messages = [
        json.dumps({"type": "response.delta", "delta": {"text": "Hello"}}),
        json.dumps({"type": "response.delta", "delta": {"text": ", world"}}),
        json.dumps({"type": "response.completed"}),
    ]

    class DummyWS:
        def __init__(self):
            self.sent = []
            self._recv_iter = iter(messages)
        async def __aenter__(self):
            return self
        async def __aexit__(self, exc_type, exc, tb):
            return False
        async def send(self, data):
            self.sent.append(data)
        async def recv(self):
            try:
                return next(self._recv_iter)
            except StopIteration:
                await asyncio.sleep(0)
                return json.dumps({"type": "response.completed"})

    def fake_connect(url, extra_headers=None, ping_timeout=None):
        return DummyWS()

    # Patch websockets.connect
    import gotaglio.lazy_imports as li
    monkeypatch.setattr(li.websockets, 'connect', fake_connect)

    context = {"audio_file": str(audio_path)}
    result = await model.infer(messages=[], context=context)

    assert result == "Hello, world"
    assert isinstance(context.get("realtime_events"), list)
    assert any(ev.get("type") == "response.create" for ev in context["realtime_events"])
    # Check sequences strictly increasing
    assert_strictly_increasing_sequences(context["realtime_events"])
    # Exercise JSONL writer
    out = tmp_path / "events.jsonl"
    save_events_jsonl(context["realtime_events"], str(out))
    assert out.exists() and out.stat().st_size > 0

@pytest.mark.asyncio
async def test_realtime_model_missing_audio():
    registry = DummyRegistry()
    model = AzureOpenAIRealtime(registry, {
        "name": "azure-realtime",
        "type": "AZURE_OPEN_AI_REALTIME",
        "endpoint": "https://example.openai.azure.com",
        "api": "2024-06-01",
        "deployment": "gpt-4o-realtime-preview",
        "key": "sk-test",
    })

    with pytest.raises(ValueError):
        await model.infer(messages=[], context={})


@pytest.mark.asyncio
async def test_realtime_model_timeout(monkeypatch, tmp_path):
    registry = DummyRegistry()
    model = AzureOpenAIRealtime(registry, {
        "name": "azure-realtime",
        "type": "AZURE_OPEN_AI_REALTIME",
        "endpoint": "https://example.openai.azure.com",
        "api": "2024-06-01",
        "deployment": "gpt-4o-realtime-preview",
        "key": "sk-test",
        "sample_rate_hz": 16000,
        "timeout_s": 0.01,
    })

    audio_path = tmp_path / "hello.wav"
    audio_path.write_bytes(b"FAKEAUDIO")

    class DummyWS:
        def __init__(self):
            self.sent = []
        async def __aenter__(self):
            return self
        async def __aexit__(self, exc_type, exc, tb):
            return False
        async def send(self, data):
            self.sent.append(data)
        async def recv(self):
            # never yields within timeout
            import asyncio
            await asyncio.sleep(0.1)
            return "{}"

    def fake_connect(url, extra_headers=None, ping_timeout=None):
        return DummyWS()

    import gotaglio.lazy_imports as li
    monkeypatch.setattr(li.websockets, 'connect', fake_connect)

    context = {"audio_file": str(audio_path)}
    result = await model.infer(messages=[], context=context)
    # In timeout path, result may be empty string; ensure error event present
    ev_types = [ev.get("type") for ev in context.get("realtime_events", [])]
    assert any(t in ("error.timeout", "error") for t in ev_types)
