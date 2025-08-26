from abc import ABC, abstractmethod
from typing import Any, cast

from .constants import app_configuration
from .exceptions import ExceptionContext
from .lazy_imports import azure_ai_inference, azure_core_credentials, openai, websockets
from .shared import read_data_file


class Model(ABC):
    # `context` parameter provides entire test case context to
    # assist in implementing mocks that can pull the expected
    # value ouf of the context. Real models ignore the `context`
    # parameter.
    @abstractmethod
    @abstractmethod
    async def infer(self, messages, context=None) -> str:
        pass

    @abstractmethod
    def metadata(self) -> dict[str, Any]:
        pass


class AzureAI(Model):
    def __init__(self, registry, configuration):
        self._config = configuration
        self._client = None
        registry.register_model(configuration["name"], self)

    async def infer(self, messages, context=None):
        if not self._client:
            endpoint = self._config["endpoint"]
            key = self._config["key"]
            self._client = azure_ai_inference.ChatCompletionsClient(
                endpoint=endpoint,
                credential=azure_core_credentials.AzureKeyCredential(key),
            )

        response = self._client.complete(messages=messages)

        return cast(str, response.choices[0].message.content)

    def metadata(self):
        return {k: v for k, v in self._config.items() if k != "key"}


class AzureOpenAI(Model):
    def __init__(self, registry, configuration):
        self._config = configuration
        self._client = None
        registry.register_model(configuration["name"], self)

    async def infer(self, messages, context=None):
        if not self._client:
            endpoint = self._config["endpoint"]
            key = self._config["key"]
            api = self._config["api"]
            self._client = openai.AzureOpenAI(
                api_key=key,
                api_version=api,
                azure_endpoint=endpoint,
            )

        # Pull runtime settings from context if provided (e.g., infer.model.settings)
        settings = (context or {}).get("model_settings", {})
        max_tokens = settings.get("max_tokens", 800)
        temperature = settings.get("temperature", 0.7)
        top_p = settings.get("top_p", 0.95)
        frequency_penalty = settings.get("frequency_penalty", 0)
        presence_penalty = settings.get("presence_penalty", 0)

        response = self._client.chat.completions.create(
            model=self._config["deployment"],
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
            top_p=top_p,
            frequency_penalty=frequency_penalty,
            presence_penalty=presence_penalty,
            stop=None,
            stream=False,
        )

        return response.choices[0].message.content

    def metadata(self):
        return {k: v for k, v in self._config.items() if k != "key"}


class AzureOpenAI5(Model):
    """
    Azure OpenAI (GPT-5 family) model wrapper.

    Differences vs AzureOpenAI:
    - Uses `max_completion_tokens` instead of `max_tokens`.
    """

    def __init__(self, registry, configuration):
        self._config = configuration
        self._client = None
        registry.register_model(configuration["name"], self)

    async def infer(self, messages, context=None):
        if not self._client:
            endpoint = self._config["endpoint"]
            key = self._config["key"]
            api = self._config["api"]
            self._client = openai.AzureOpenAI(
                api_key=key,
                api_version=api,
                azure_endpoint=endpoint,
            )

        # Pull runtime settings from context if provided (e.g., infer.model.settings)
        settings = (context or {}).get("model_settings", {})
        # Prefer max_completion_tokens when provided; fall back to max_tokens for backward compatibility
        max_completion_tokens = settings.get(
            "max_completion_tokens", settings.get("max_tokens", 800)
        )
        temperature = settings.get("temperature", 0.7)
        top_p = settings.get("top_p", 0.95)
        frequency_penalty = settings.get("frequency_penalty", 0)
        presence_penalty = settings.get("presence_penalty", 0)

        response = self._client.chat.completions.create(
            model=self._config["deployment"],
            messages=messages,
            max_completion_tokens=max_completion_tokens,
            frequency_penalty=frequency_penalty,
            presence_penalty=presence_penalty,
            stop=None,
            stream=False,
        )

        return response.choices[0].message.content

    def metadata(self):
        return {k: v for k, v in self._config.items() if k != "key"}


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

        # Connection details
        endpoint = self._config["endpoint"].rstrip("/")
        api = self._config["api"]
        deployment = self._config["deployment"]
        key = self._config["key"]

        base_url = endpoint.replace("https://", "wss://")
        ws_url = f"{base_url}/openai/realtime?api-version={api}&deployment={deployment}"

        headers = {
            "api-key": key,
        }

        timeout_s = float(self._config.get("timeout_s", 60))
        sample_rate = int(self._config.get("sample_rate_hz", 16000))

        # Event capture
        events: list[dict[str, Any]] = []
        seq = 0

        async def append_event(ev_type: str, payload: Any):
            nonlocal seq
            from time import time

            events.append(
                {
                    "sequence": seq,
                    "type": ev_type,
                    "ts": time(),
                    "payload": payload,
                }
            )
            seq += 1

        final_text: str | None = None

        import asyncio
        import json as _json

        try:
            async with websockets.connect(ws_url, extra_headers=headers, ping_timeout=timeout_s) as ws:
                await append_event("session.connected", {"url": ws_url})

                # Send optional session settings (voice/modalities)
                session_cfg: dict[str, Any] = {}
                voice = self._config.get("voice")
                if voice:
                    session_cfg["voice"] = voice
                modalities = self._config.get("modalities")
                if modalities:
                    session_cfg["modalities"] = modalities
                if session_cfg:
                    msg = {"type": "session.update", "session": session_cfg}
                    await ws.send(_json.dumps(msg))
                    await append_event("session.update", msg)

                # Start input audio
                start_input = {"type": "input_audio_buffer.start", "sample_rate": sample_rate}
                await ws.send(_json.dumps(start_input))
                await append_event("input_audio_buffer.start", start_input)

                # Send audio bytes (single chunk for MVP)
                await ws.send(audio_bytes)
                await append_event("input_audio_buffer.append", {"size": len(audio_bytes)})

                # Commit audio and request response
                commit = {"type": "input_audio_buffer.commit"}
                await ws.send(_json.dumps(commit))
                await append_event("input_audio_buffer.commit", commit)

                create = {"type": "response.create"}
                await ws.send(_json.dumps(create))
                await append_event("response.create", create)

                # Receive loop
                done = False
                while not done:
                    try:
                        raw = await asyncio.wait_for(ws.recv(), timeout=timeout_s)
                    except asyncio.TimeoutError:
                        await append_event("error.timeout", {"message": "recv timeout"})
                        break

                    if isinstance(raw, (bytes, bytearray)):
                        await append_event("binary", {"size": len(raw)})
                        continue

                    await append_event("message", raw)
                    try:
                        data = _json.loads(raw)
                    except Exception:
                        # Non-JSON, ignore body content
                        continue

                    t = data.get("type")
                    if t == "response.delta":
                        delta = data.get("delta") or {}
                        text = delta.get("text")
                        if text:
                            final_text = (final_text or "") + text
                    elif t in ("response.completed", "session.completed"):
                        done = True

        except Exception as e:
            await append_event("error", {"message": str(e)})

        # Attach events to context for assessment
        if context is not None:
            context["realtime_events"] = events

        return final_text or ""

    def metadata(self):
        return {k: v for k, v in self._config.items() if k != "key"}


def register_models(registry):
    config_files = app_configuration["model_config_files"]
    credentials_files = app_configuration["model_credentials_files"]

    # Read the model configuration file
    config = None
    for config_file in config_files:
        config = read_data_file(config_file, True, True)
        if config:
            break

    # Read the credentials file
    credentials = None
    for credentials_file in credentials_files:
        credentials = read_data_file(credentials_file, True, True)
        if credentials:
            break

    if config and credentials:
        # Merge in keys from credentials file
        for model in config:
            if model["name"] in credentials:
                model["key"] = credentials[model["name"]]

    if config:
        # Construct and register models.
        # TODO: lazy construction of models on first use
        for model in config:
            with ExceptionContext(f"While registering model '{model['name']}':"):
                if model["type"] == "AZURE_AI":
                    AzureAI(registry, model)
                elif model["type"] == "AZURE_OPEN_AI":
                    AzureOpenAI(registry, model)
                elif model["type"] == "AZURE_OPEN_AI_5":
                    AzureOpenAI5(registry, model)
                elif model["type"] == "AZURE_OPEN_AI_REALTIME":
                    AzureOpenAIRealtime(registry, model)
                else:
                    raise ValueError(
                        f"Model {model['name']} has unsupported model type: {model['type']}"
                    )
