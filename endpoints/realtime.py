#!/usr/bin/env python

import asyncio
import base64
import json
import logging
import os
import uuid
from typing import Optional

import aiohttp
import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
import socket
from urllib.parse import urlparse

load_dotenv()

logger = logging.getLogger(__name__)

class Realtime:
    def __init__(
        self,
        *,
        max_file_seconds: Optional[int] = None,
        auto_close_on_first_response: bool = False,
        text_only_output: bool = False,
    ) -> None:
        """Realtime session proxy to Azure OpenAI Realtime API.

        Args:
            max_file_seconds: If provided, enforce a maximum audio duration per
                connection based on bytes appended via input_audio_buffer.append
                (assumes PCM16 24 kHz). Use for /realtime-file uploads.
            auto_close_on_first_response: If True, close client socket after the
                first full response is observed.
            text_only_output: If True, configure the session for text-only
                output (no audio synthesis), while still accepting audio input.
        """
        # Unique id for this connection/session for log correlation
        self.session_id = uuid.uuid4().hex[:8]
        # Config
        self.api_key = os.environ.get("AZURE_OPENAI_API_KEY")
        self.endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT", "").rstrip("/")
        self.deployment = os.environ.get("AZURE_OPENAI_REALTIME_MODEL_NAME")
        self.voice_choice = os.environ.get("AZURE_OPENAI_REALTIME_VOICE_CHOICE")
        self.api_version = os.environ.get("AZURE_OPENAI_REALTIME_API_VERSION")
        # Options
        self.max_file_seconds = max_file_seconds
        self.auto_close_on_first_response = auto_close_on_first_response
        self.text_only_output = text_only_output
        # Runtime state
        self.session: Optional[aiohttp.ClientSession] = None
        self.ws_openai: Optional[aiohttp.ClientWebSocketResponse] = None
        self.client_connected = True
        self._audio_bytes_received = 0

    def _ensure_env(self) -> None:
        """Validate required environment variables before connecting."""
        required = {
            "AZURE_OPENAI_API_KEY": self.api_key,
            "AZURE_OPENAI_ENDPOINT": self.endpoint,
            "AZURE_OPENAI_REALTIME_MODEL_NAME": self.deployment,
            "AZURE_OPENAI_REALTIME_API_VERSION": self.api_version,
        }
        missing = [k for k, v in required.items() if not v]
        if missing:
            raise RuntimeError(
                f"Missing required environment variables: {', '.join(missing)}"
            )

    async def connect_to_realtime_api(self) -> None:
        # Validate environment/config before attempting to connect
        self._ensure_env()

        headers = {
            "api-key": self.api_key,
            # Azure Realtime commonly expects this beta header
            "OpenAI-Beta": "realtime=v1",
        }
        base_url = self.endpoint.replace("https://", "wss://")
        url = f"{base_url}/openai/realtime?api-version={self.api_version}&deployment={self.deployment}"

        try:
            # Close any previous session/socket defensively
            if self.ws_openai and not self.ws_openai.closed:
                await self.ws_openai.close()
            if self.session and not self.session.closed:
                await self.session.close()

            self.session = aiohttp.ClientSession()
            # Heartbeat helps keep NATs alive; bump max_msg_size if needed for larger frames
            self.ws_openai = await self.session.ws_connect(
                url,
                headers=headers,
                timeout=60,
                heartbeat=20.0,
                max_msg_size=10 * 1024 * 1024,
                protocols=["realtime"],
            )
            logger.info("[%s] Connected to Azure Realtime", self.session_id)
            await self.send_session_config()
        except Exception as e:
            logger.exception("Failed to connect to Azure OpenAI")
            if self.session and not self.session.closed:
                await self.session.close()
            err = str(e)
            raise ConnectionError(f"Cannot connect to Azure OpenAI Realtime API: {err}")
        

    

    async def send_session_config(self) -> None:
        # Load prompt from local file
        prompt_path = os.environ.get("PROMPT_TEMPLATE_PATH")
        if not prompt_path or not os.path.isfile(prompt_path):
            logger.warning("[%s] PROMPT_TEMPLATE_PATH missing or not a file: %s", self.session_id, prompt_path)
            prompt_text = ""
        else:
            with open(prompt_path, "r", encoding="utf-8") as f:
                prompt_text = f.read()

        # Basic realtime instructions
        enhanced_prompt = (
            "Respond in spanish. " + prompt_text
        )

        # Simple session configuration
        session_cfg = {
            "modalities": ["text"] if self.text_only_output else ["text", "audio"],
            "instructions": enhanced_prompt,
            # Always allow audio input via PCM16
            "input_audio_format": "pcm16",
            "input_audio_transcription": {"model": "whisper-1"},
            # For interactive/mic sessions use server_vad; for file uploads (auto-close mode) omit VAD
            # to rely on explicit commit.
            # We'll add turn_detection only when not auto-closing on first response
            "tools": [],
            "tool_choice": "auto",
        }
        if not self.auto_close_on_first_response:
            session_cfg["turn_detection"] = {"type": "server_vad", "threshold": 0.2, "silence_duration_ms": 5000}
        if not self.text_only_output:
            # Provide voice/output audio only when not text-only
            session_cfg.update({
                "voice": self.voice_choice,
                "output_audio_format": "pcm16",
            })

        config = {"type": "session.update", "session": session_cfg}

        await self.ws_openai.send_json(config)
        logger.info("[%s] Sent session config", self.session_id)

    async def _forward_messages(self, websocket: WebSocket) -> None:
        try:
            logger.info("[%s] Starting realtime session", self.session_id)
            await self.connect_to_realtime_api()

            # Structured concurrency: cancel sibling on error automatically
            async with asyncio.TaskGroup() as tg:
                tg.create_task(self._from_client_to_openai(websocket))
                tg.create_task(self._from_openai_to_client(websocket))

        except WebSocketDisconnect:
            self.client_connected = False
        except Exception:
            logger.exception("[%s] Error in message forwarding", self.session_id)
            self.client_connected = False
            try:
                await websocket.send_json(
                    {
                        "type": "error",
                        "error": {"message": "Server error: see server logs", "code": "internal_error"},
                    }
                )
            except Exception:
                pass
        finally:
            await self.cleanup()

    async def _from_client_to_openai(self, websocket: WebSocket) -> None:
        while self.client_connected:
            try:
                message = await websocket.receive_text()
                message_data = json.loads(message)

                # Simple audio format handling
                if message_data.get("type") == "input_audio_buffer.append":
                    if "data" in message_data and "audio" not in message_data:
                        message_data["audio"] = message_data.pop("data")

                    # Enforce optional max file duration (assumes PCM16 at 24kHz)
                    if self.max_file_seconds and isinstance(message_data.get("audio"), str):
                        try:
                            b64 = message_data["audio"]
                            # Compute bytes from base64 length without full decode for speed
                            padding = b64.endswith("==") and 2 or (b64.endswith("=") and 1 or 0)
                            bytes_len = (len(b64) * 3) // 4 - padding
                            self._audio_bytes_received += max(bytes_len, 0)
                            # 24_000 samples/sec * 2 bytes per sample (PCM16 mono)
                            max_bytes = int(self.max_file_seconds) * 24000 * 2
                            if self._audio_bytes_received > max_bytes:
                                logger.warning(
                                    "[%s] Max file duration exceeded: %ss (received ~%.2fs)",
                                    self.session_id,
                                    self.max_file_seconds,
                                    self._audio_bytes_received / (24000 * 2),
                                )
                                await websocket.send_json(
                                    {
                                        "type": "error",
                                        "error": {
                                            "message": f"File too long. Max duration is {self.max_file_seconds} seconds.",
                                            "code": "file_too_long",
                                        },
                                    }
                                )
                                # Stop forwarding further data
                                self.client_connected = False
                                break
                        except Exception:  # best-effort; don't block on size check
                            logger.exception("[%s] Failed to enforce max duration", self.session_id)

                await self.ws_openai.send_json(message_data)
            except WebSocketDisconnect:
                self.client_connected = False
                break
            except Exception:
                logger.exception("[%s] Error forwarding client message", self.session_id)
                break

    async def _from_openai_to_client(self, websocket: WebSocket) -> None:
        if not self.ws_openai or self.ws_openai.closed:
            logger.error("[%s] OpenAI WebSocket not ready", self.session_id)
            return

        try:
            async for msg in self.ws_openai:
                if msg.type == aiohttp.WSMsgType.TEXT:
                    try:
                        message = json.loads(msg.data)

                        # Handle errors
                        if message.get("type") == "error":
                            await self._handle_error(message, websocket)
                            continue

                        # Forward all other messages
                        await websocket.send_text(msg.data)

                        # Optionally auto-close on first full response for file uploads
                        if self.auto_close_on_first_response and message.get("type") in {"response.completed", "response.done"}:
                            try:
                                await websocket.close(code=1000)
                            finally:
                                self.client_connected = False
                                break

                    except json.JSONDecodeError:
                        logger.exception("[%s] Failed to parse JSON from OpenAI", self.session_id)
                    except Exception:
                        logger.exception("[%s] Error processing OpenAI message", self.session_id)
        except Exception:
            logger.exception("[%s] Error in OpenAI-to-client forwarding", self.session_id)
            raise

    async def _handle_error(self, message, websocket) -> None:
        """Simple error handling"""
        error_details = message.get("error", {})
        error_message = (
            error_details.get("message", "Unknown error")
            if isinstance(error_details, dict)
            else str(error_details)
        )

        logger.error("[%s] OpenAI API error: %s", self.session_id, error_message)

        await websocket.send_json(
            {
                "type": "error",
                "error": {"message": f"API Error: {error_message}", "code": "api_error"},
            }
        )

    async def cleanup(self) -> None:
        """Close OpenAI websocket and HTTP session, reset flags."""
        self.client_connected = False
        try:
            if self.ws_openai and not self.ws_openai.closed:
                await self.ws_openai.close()
        finally:
            self.ws_openai = None
        try:
            if self.session and not self.session.closed:
                await self.session.close()
        finally:
            self.session = None


app = FastAPI()

@app.get("/realtime_test.html")
async def serve_realtime_test_html():
    """Serve the test client HTML page from the endpoints directory."""
    html_path = os.path.join(os.path.dirname(__file__), "realtime_test.html")
    try:
        with open(html_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read(), media_type="text/html")
    except FileNotFoundError:
        return HTMLResponse(content="realtime_test.html not found", status_code=404)


@app.websocket("/realtime")
async def realtime_websocket(websocket: WebSocket):
    try:
        await websocket.accept()
        # Use a per-connection instance to avoid shared state between clients
        await Realtime()._forward_messages(websocket)
    except WebSocketDisconnect:
        # Client disconnected, optionally log or cleanup
        logger.info("WebSocket client disconnected")
    except Exception:
        logger.exception("Exception in /realtime websocket endpoint")
        try:
            await websocket.send_json({
                "type": "error",
                "error": {"message": "Server error: see server logs", "code": "internal_error"},
            })
        except Exception:
            pass

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
