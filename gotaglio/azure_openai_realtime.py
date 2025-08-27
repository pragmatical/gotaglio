from typing import Any

# Import Model from models; this works because models defines Model before importing us
from .models import Model  # type: ignore
from .lazy_imports import websockets


class AzureOpenAIRealtime(Model):
    """
    Azure OpenAI Realtime (WebSocket) model wrapper for streaming audio input and
    capturing streamed events. MVP uses WebSocket transport only.

    Expected config keys:
    - name: str
    - type: "AZURE_OPEN_AI_REALTIME"
    - endpoint: Azure resource endpoint (e.g., https://<resource>.openai.azure.com)
    - api: api version (e.g., 2024-06-01)
    - deployment: realtime-capable deployment name (e.g., gpt-4o-realtime-preview)
    - key: API key
    Optional:
    - sample_rate_hz: default 16000
    - timeout_s: default 60
    - voice: optional voice name
    - modalities: optional list, e.g., ["text", "audio"]
    """

    def __init__(self, registry, configuration):
        self._config = configuration
        registry.register_model(configuration["name"], self)

    async def infer(self, messages, context=None):
        """
        `messages` are ignored for realtime audio; use `context` for:
          - context["audio_file"]: path to audio file to send
          - context["audio_bytes"]: raw audio bytes
        Returns a best-effort final text response. Also attaches captured events to
        context under `context["realtime_events"]`.
        """
        # Resolve inputs
        audio_bytes = None
        audio_path = None
        if context is not None:
            audio_bytes = (context or {}).get("audio_bytes")
            audio_path = (context or {}).get("audio_file")

        if audio_bytes is None and audio_path:
            with open(str(audio_path), "rb") as f:
                audio_bytes = f.read()

        if not audio_bytes:
            raise ValueError(
                "AzureOpenAIRealtime.infer requires audio_file or audio_bytes in context"
            )

        timeout_s = float(self._config.get("timeout_s", 60))

        # Event capture
        events: list[dict[str, Any]] = []
        seq = 0

        def create_event(ev_type: str) -> dict:
            return {"type": ev_type}
        
        def create_error_event(ev_type: str,error_message):
            ev=create_event(ev_type)
            ev["message"]=error_message
            return ev

        def create_audio_event(ev_type: str, audio_bytes: bytes) -> dict:
            """Create a REDACTED audio event for logs.
            We intentionally do NOT include the raw/base64 audio in the event log.
            """
            return {"type": ev_type, "size": len(audio_bytes), "redacted": True}

        def create_response_event(ev_type: str, message=None) -> dict:
            ev = create_event(ev_type)
            if message is not None:
                ev["message"] = message
            return ev

        async def append_event(event: dict):
            nonlocal seq
            record = dict(event)
            record["sequence"] = seq
            # Attach a timestamp (float seconds since epoch) for observability
            try:
                import time
                record["timestamp"] = time.time()
            except Exception:
                # If clock retrieval fails (unlikely), omit timestamp gracefully
                pass
            events.append(record)
            seq += 1

        # Pre-connection debug info
        try:
            await append_event(create_event("audio.resolved"))
            await append_event(create_event("debug.ws"))
        except Exception:
            pass

        import json as _json

        final_text: str | None = None
        try:
            async with self._connect_websocket(context) as ws:
                await append_event(create_event("session.connected"))
                print("WebSocket connection established")

                # Send session configuration as the first message
                await self._send_session_config(ws, context)
                # Append a minimal event indicating config was sent
                await append_event(create_event("session.update"))

                # Send audio bytes (single chunk for MVP)
                # Build the full send frame including base64 audio, but log a redacted event.
                # Ensure audio is PCM16 mono @ 24 kHz as required by Azure Realtime.
                send_frame = self._make_audio_append_message(audio_bytes, context)
                await ws.send(_json.dumps(send_frame))
                await append_event(create_audio_event("input_audio_buffer.append", audio_bytes))

                # Commit audio and request response
                commit = create_event("input_audio_buffer.commit")
                await ws.send(_json.dumps(commit))
                await append_event(commit)

                create = create_event("response.create")
                await ws.send(_json.dumps(create))
                await append_event(create)

                # Receive and process responses
                final_text = await self._receive_responses(
                    ws,
                    timeout_s,
                    create_response_event,
                    append_event,
                )

        except Exception as e:
            # Log a simple error event; details can be inspected in logs
            await append_event(create_error_event("error", str(e)))

        # Attach events to context for assessment
        if context is not None:
            context["realtime_events"] = events

        return final_text or ""

    def _make_audio_append_message(self, audio_bytes: bytes, context=None):
        """Create the audio buffer append payload in the expected format.
        Returns a JSON-serializable dict with base64 data under the 'audio' key.
        This implementation does not perform conversion; callers should supply
        PCM16 mono @ 24kHz for best results.
        """
        import base64
        return {
            "type": "input_audio_buffer.append",
            "audio": base64.b64encode(audio_bytes).decode("ascii"),
        }

    async def _receive_responses(
        self,
        ws,
        timeout_s: float,
        create_response_event,
        append_event,
    ):
        """Receive messages from the websocket and aggregate final text.
        Records events via append_event and returns the aggregated final text.
        """
        import asyncio
        import json as _json

        done = False
        while not done:
            try:
                raw = await asyncio.wait_for(ws.recv(), timeout=timeout_s)
            except asyncio.TimeoutError:
                await append_event(create_response_event("error.timeout"))
                break

            # Ignore binary frames entirely
            if isinstance(raw, (bytes, bytearray)):
                continue

            try:
                message = _json.loads(raw)
            except Exception:
                # Non-JSON, ignore body content
                continue

            if not isinstance(message, dict):
                continue

            t = message.get("type")

            # Errors
            if t == "error":
                await append_event(create_response_event("response.error", message))
                continue

            # Only record selected response events
            if t in ("response.text.delta", "response.done"):
                await append_event(create_response_event(t, message))
            # If response.done is received close the websocket
            if t == "response.done":
                try:
                    if hasattr(ws, "close"):
                        await ws.close()
                except Exception:
                    await append_event(create_response_event("ws.close_error"))
                done = True
            continue


    async def _send_session_config(self, ws, context=None):
        """
        Send the initial session.update payload to configure the Azure Realtime session.
        Modeled after endpoints/realtime.py but using the websockets API.
        """
        import os
        import json as _json

        # Load optional prompt template from env
        prompt_text = ""
        try:
            prompt_path = os.environ.get("PROMPT_TEMPLATE_PATH")
            if prompt_path and os.path.isfile(prompt_path):
                with open(prompt_path, "r", encoding="utf-8") as f:
                    prompt_text = f.read()
        except Exception:
            # Ignore prompt issues silently for robustness
            pass

        # Allow context to override/augment instructions if provided
        ctx_instructions = (context or {}).get("instructions") if context else None
        if isinstance(ctx_instructions, str) and ctx_instructions:
            prompt_text = ctx_instructions

        # Basic realtime instructions (keep parity with previous behavior)
        enhanced_prompt = "Respond in spanish. " + (prompt_text or "")

        # Config from model settings, with defaults
        voice = self._config.get("voice", "alloy")
        modalities = self._config.get("modalities", ["text"])

        payload = {
            "type": "session.update",
            "session": {
                "modalities": modalities,
                "instructions": enhanced_prompt,
                "voice": voice,
                "input_audio_format": "pcm16",
                "output_audio_format": "pcm16",
                "turn_detection": {"type": "none"},
                "tools": [],
                "tool_choice": "auto",
            },
        }

        await ws.send(_json.dumps(payload))

    def _connect_websocket(self, context=None):
        """
        Create and return a websockets connection context manager to Azure OpenAI Realtime.
        Validates config, builds URL and headers, and applies sensible timeouts.
        Returns the async context manager so callers can `async with` it for proper cleanup.
        """
        # Validate required config
        required = ["endpoint", "api", "deployment", "key"]
        missing = [k for k in required if not self._config.get(k)]
        if missing:
            raise ConnectionError(f"Missing required config: {', '.join(missing)}")

        endpoint = str(self._config["endpoint"]).rstrip("/")
        api = self._config["api"]
        deployment = self._config["deployment"]
        key = self._config["key"]
        timeout_s = float(self._config.get("timeout_s", 60))

        base_url = endpoint.replace("https://", "wss://")
        url = f"{base_url}/openai/realtime?api-version={api}&deployment={deployment}"
        headers = {"api-key": key}

        # Return context manager; handshake occurs when entering the context
        return websockets.connect(url, extra_headers=headers, ping_timeout=timeout_s)

    def metadata(self):
        return {k: v for k, v in self._config.items() if k != "key"}
