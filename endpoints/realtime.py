#!/usr/bin/env python

import asyncio
import json
import logging
import os

import aiohttp
# from common.schemas import ResponseSchema
from fastapi import FastAPI, WebSocket
from fastapi.responses import HTMLResponse
from fastapi import WebSocket, WebSocketDisconnect
from dotenv import load_dotenv

load_dotenv("credentials.env")

logger = logging.getLogger(__name__)

class Realtime:
    def __init__(self):
        self.api_key = os.environ.get("AZURE_OPENAI_API_KEY")
        self.endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT", "").rstrip("/")
        self.deployment = os.environ.get("AZURE_OPENAI_REALTIME_MODEL_NAME")
        self.voice_choice = os.environ.get("AZURE_OPENAI_REALTIME_VOICE_CHOICE")
        self.api_version = os.environ.get("AZURE_OPENAI_REALTIME_API_VERSION")

        self.session = None
        self.ws_openai = None
        self.client_connected = True

    async def connect_to_realtime_api(self):
        headers = {"api-key": self.api_key}
        base_url = self.endpoint.replace("https://", "wss://")
        url = f"{base_url}/openai/realtime?api-version={self.api_version}&deployment={self.deployment}"

        try:
            self.session = aiohttp.ClientSession()
            self.ws_openai = await self.session.ws_connect(url, headers=headers, timeout=30)
            await self.send_session_config()
        except Exception as e:
            logger.error("Failed to connect to Azure OpenAI: %s", str(e))
            if self.session and not self.session.closed:
                await self.session.close()
            raise ConnectionError(f"Cannot connect to Azure OpenAI Realtime API: {str(e)}")

    async def send_session_config(self):
        # Load prompt from local file
        prompt_path = os.environ.get("PROMPT_TEMPLATE_PATH")
        with open(prompt_path, "r", encoding="utf-8") as f:
            prompt_text = f.read()

        # Basic realtime instructions
        enhanced_prompt = (
            "Respond in spanish. " + prompt_text
        )

        # Simple session configuration
        config = {
            "type": "session.update",
            "session": {
                "modalities": ["text"],
                "instructions": enhanced_prompt,
                "voice": self.voice_choice,
                "input_audio_format": "pcm16",
                "output_audio_format": "pcm16",
                "turn_detection": {"type": "server_vad", "threshold": 0.2, "silence_duration_ms": 500},
                "tools": [],
                "tool_choice": "auto",
            },
        }

        await self.ws_openai.send_json(config)

    async def _forward_messages(self, websocket: WebSocket):
        try:
            logger.info("Starting realtime session")
            await self.connect_to_realtime_api()

            # Start forwarding tasks
            client_task = asyncio.create_task(self._from_client_to_openai(websocket))
            openai_task = asyncio.create_task(self._from_openai_to_client(websocket))

            # Wait for either task to complete
            done, pending = await asyncio.wait(
                [client_task, openai_task], return_when=asyncio.FIRST_EXCEPTION
            )

            # Cancel pending tasks
            for task in pending:
                task.cancel()

            # Check for exceptions
            for task in done:
                if task.exception():
                    raise task.exception()

        except WebSocketDisconnect:
            self.client_connected = False
        except Exception as e:
            logger.error("Error in message forwarding: %s", str(e))
            self.client_connected = False
            try:
                await websocket.send_json(
                    {
                        "type": "error",
                        "error": {"message": f"Server error: {str(e)}", "code": "internal_error"},
                    }
                )
            except Exception:
                pass
        finally:
            await self.cleanup()

    async def _from_client_to_openai(self, websocket: WebSocket):
        while self.client_connected:
            try:
                message = await websocket.receive_text()
                message_data = json.loads(message)

                # Simple audio format handling
                if message_data.get("type") == "input_audio_buffer.append":
                    if "data" in message_data and "audio" not in message_data:
                        message_data["audio"] = message_data.pop("data")

                await self.ws_openai.send_json(message_data)
            except WebSocketDisconnect:
                self.client_connected = False
                break
            except Exception as e:
                logger.error("Error forwarding client message: %s", str(e))
                break

    async def _from_openai_to_client(self, websocket: WebSocket):
        if not self.ws_openai or self.ws_openai.closed:
            logger.error("OpenAI WebSocket not ready")
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

                    except json.JSONDecodeError:
                        logger.error("Failed to parse JSON from OpenAI")
                    except Exception as e:
                        logger.error("Error processing OpenAI message: %s", str(e))
        except Exception as e:
            logger.error("Error in OpenAI-to-client forwarding: %s", str(e))
            raise

    async def _handle_error(self, message, websocket):
        """Simple error handling"""
        error_details = message.get("error", {})
        error_message = (
            error_details.get("message", "Unknown error")
            if isinstance(error_details, dict)
            else str(error_details)
        )

        logger.error("OpenAI API error: %s", error_message)

        await websocket.send_json(
            {
                "type": "error",
                "error": {"message": f"API Error: {error_message}", "code": "api_error"},
            }
        )

    async def cleanup(self):
        if self.ws_openai and not self.ws_openai.closed:
            await self.ws_openai.close()
        if self.session and not self.session.closed:
            await self.session.close()


app = FastAPI()
realtime_instance = Realtime()


@app.websocket("/realtime")
async def realtime_websocket(websocket: WebSocket):
    try:
        await websocket.accept()
        await realtime_instance._forward_messages(websocket)
    except WebSocketDisconnect:
        # Client disconnected, optionally log or cleanup
        logger.info("WebSocket client disconnected")
        await realtime_instance.cleanup()
    except Exception as e:
        logger.error(f"Exception in /realtime websocket endpoint: {e}")
        try:
            await websocket.send_json({
                "type": "error",
                "error": {"message": f"Server error: {str(e)}", "code": "internal_error"},
            })
        except Exception:
            pass
        await realtime_instance.cleanup()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
