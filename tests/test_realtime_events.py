import asyncio
import json
import base64
import pytest

from gotaglio.models import AzureOpenAIRealtime


class DummyRegistry:
    def register_model(self, name, model):
        setattr(self, name, model)


@pytest.mark.asyncio
async def test_audio_append_event_shape_and_order(monkeypatch, tmp_path):
    registry = DummyRegistry()
    model = AzureOpenAIRealtime(
        registry,
        {
            "name": "azure-realtime",
            "type": "AZURE_OPEN_AI_REALTIME",
            "endpoint": "https://example.openai.azure.com",
            "api": "2024-06-01",
            "deployment": "gpt-4o-realtime-preview",
            "key": "sk-test",
            "sample_rate_hz": 16000,
            "timeout_s": 3,
        },
    )

    # Prepare fake audio
    audio_path = tmp_path / "hello.wav"
    raw_audio = b"FAKEAUDIO"
    audio_path.write_bytes(raw_audio)

    # WebSocket dummy: yields a quick completion
    class DummyWS:
        def __init__(self):
            self.sent = []
            self._recv_iter = iter([
                json.dumps({"type": "response.completed"}),
            ])

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

    import gotaglio.lazy_imports as li
    monkeypatch.setattr(li.websockets, "connect", fake_connect)

    context = {"audio_file": str(audio_path)}
    result = await model.infer(messages=[], context=context)
    assert isinstance(result, str)

    # 1) Verify sent messages include our audio append event first, then commit, then create
    sent_types = []
    for s in [x for x in context.get("realtime_events", []) if isinstance(x, dict)]:
        pass  # ensure events exist

    sent_json_types = []
    for frame in [m for m in fake_connect(None).sent if False]:
        pass  # not used; above fake_connect creates a new instance

    # Inspect ws.sent captured by the instance used in infer
    # We can't directly access that instance here, so infer from events order + content
    # Confirm there is an input_audio_buffer.append event in events with redacted audio and size only
    events = context.get("realtime_events", [])
    ia_events = [ev for ev in events if ev.get("type") == "input_audio_buffer.append"]
    assert ia_events, "Expected input_audio_buffer.append event present"
    ev = ia_events[0]
    assert "audio" not in ev  # audio should not be logged
    assert ev.get("redacted") is True
    assert "size" in ev and ev["size"] == len(raw_audio)

    # Ensure ordering of key events in event log
    def first_index(event_type: str) -> int:
        for i, e in enumerate(events):
            if e.get("type") == event_type:
                return i
        return -1

    idx_append = first_index("input_audio_buffer.append")
    idx_commit = first_index("input_audio_buffer.commit")
    idx_create = first_index("response.create")
    assert idx_append != -1 and idx_commit != -1 and idx_create != -1
    assert idx_append < idx_commit < idx_create


@pytest.mark.asyncio
async def test_binary_frames_recorded_as_audio_event(monkeypatch, tmp_path):
    registry = DummyRegistry()
    model = AzureOpenAIRealtime(
        registry,
        {
            "name": "azure-realtime",
            "type": "AZURE_OPEN_AI_REALTIME",
            "endpoint": "https://example.openai.azure.com",
            "api": "2024-06-01",
            "deployment": "gpt-4o-realtime-preview",
            "key": "sk-test",
            "sample_rate_hz": 16000,
            "timeout_s": 3,
        },
    )

    audio_path = tmp_path / "hello.wav"
    audio_path.write_bytes(b"FAKEAUDIO")

    class DummyWS:
        def __init__(self):
            self.sent = []
            self._recv_iter = iter([
                b"\x00\x01PCM\x00",  # binary frame
                json.dumps({"type": "response.completed"}),
            ])

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

    import gotaglio.lazy_imports as li
    monkeypatch.setattr(li.websockets, "connect", fake_connect)

    context = {"audio_file": str(audio_path)}
    _ = await model.infer(messages=[], context=context)

    # Verify a 'binary' event exists and is redacted (no audio content)
    events = context.get("realtime_events", [])
    bin_events = [ev for ev in events if ev.get("type") == "binary"]
    assert bin_events, "Expected binary event present"
    ev = bin_events[0]
    assert "audio" not in ev
    assert ev.get("redacted") is True
    assert "size" in ev and isinstance(ev["size"], int) and ev["size"] > 0
