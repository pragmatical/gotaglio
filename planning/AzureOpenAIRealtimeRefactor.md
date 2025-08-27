# AzureOpenAIRealtime Refactor Plan

Status summary (current):
- [x] Phases 0–4 completed and integrated
- [x] Phase 4.5 implemented (event helper refactor with Create → Send → Append flow)
- [x] append_event currently prints only transcript-delta events (filter in place)
- [x] _receive_responses currently minimal (handles timeout, binary frames, first inbound, generic errors, and response.done closure); does not yet aggregate final_text or append response.final
- [x] Session config payload currently sets modalities=["text"], turn_detection="none" (no transcription or server VAD enabled)

Remaining:
- [ ] Phase 5 additional tests (URL/header, session payload, error cases)
- [ ] Phase 6 response handling simplification + timestamps
- [ ] Rollout steps

Goal: Improve reliability and maintainability of `AzureOpenAIRealtime` while keeping the same public class and `infer` signature. Implementation will be modeled on `endpoints/realtime.py` but will continue using the `websockets` library (not `aiohttp`). Public import path must remain `from gotaglio.models import AzureOpenAIRealtime`.

## Guiding constraints
- Preserve class name and method signatures (especially `infer`).
- Preserve external behavior/contract used by tests and registry.
- Keep the `websockets` library for WS transport (do not switch to `aiohttp`).
- Model configuration and message flow on `endpoints/realtime.py`:
  - Validate env/config before connecting.
  - Build the Azure Realtime WS URL correctly.
  - First message after connect is a `session.update` payload (session config).
  - Clean shutdown and error propagation.

## Phase 0 — Planning
- [x] Create this refactor plan document.

## Phase 1 — Extraction (no behavior change)
- [x] Create a new module `gotaglio/azure_openai_realtime.py` and move the `AzureOpenAIRealtime` class into it unchanged.
- [x] In `gotaglio/models.py`, import and re-export `AzureOpenAIRealtime` to preserve the public import path (`from gotaglio.models import AzureOpenAIRealtime`).
- [x] Ensure the registry wiring and tests continue to work without modification.
- [x] Run unit tests to verify no regressions.

Notes:
- Suggested filename: `gotaglio/azure_openai_realtime.py`.
- Keep all existing parameters and defaults as-is in this step.

## Phase 2 — Connection function
- [x] Add a dedicated async method (e.g., `_connect_websocket(self, context) -> websockets.WebSocketClientProtocol`) that:
  - Validates required configuration (similar to `_ensure_env()` in `endpoints/realtime.py`).
  - Builds the Azure OpenAI Realtime WebSocket URL using endpoint, deployment, and api-version.
  - Uses `websockets.connect(...)` with appropriate headers (at minimum `api-key`) and sensible timeouts/limits (`max_size`, `ping_interval`, etc.).
  - Handles connection errors and wraps them in a clear `ConnectionError` with actionable context.
  - Cleans up partially-open connections on failure.

Implementation notes:
- Model URL and headers from `endpoints/realtime.py`:
  - Upgrade `https://` to `wss://`.
  - Path pattern: `/openai/realtime?api-version={apiVersion}&deployment={deployment}`.
  - Header: `{"api-key": <key>}`.

## Phase 3 — Session configuration function
- [x] Add a dedicated async method (e.g., `_send_session_config(self, ws, context)`) that sends the initial `session.update` message right after connecting.
  - Base content on `Realtime.send_session_config` in `endpoints/realtime.py`.
  - Continue using `websockets` API: `await ws.send(json.dumps(payload))`.
  - Keep payload fields compatible with Azure Realtime (modalities, voice, audio formats, transcription, VAD, tools/tool_choice, and optional instructions/prompt).
  - Read optional prompt/template if configured (e.g., via env or context), but handle missing files gracefully.

Configuration inputs to support (read from model init args, context, or env):
- `endpoint`, `api_key`, `deployment` (model name), `api_version`, `voice_choice`.
- Optional: `prompt_template_path` or raw `instructions`.

## Phase 4 — Integrate without changing public API
- [x] Add helper for audio message creation (no behavior change yet):
  - `_make_audio_append_message(self, audio_bytes, context=None)`
    - Returns the first audio payload to send over the websocket.
    - For now, return raw binary bytes to match current behavior; plan to support chunking/base64 if needed later.
- [x] Add helper for receiving/processing responses:
  - `_receive_responses(self, ws, timeout_s, append_event)`
    - Listens on the websocket, handles text/binary frames, aggregates final text, and records events via `append_event`.
    - Mirrors the existing loop logic in `infer` without changing return shapes.
- [x] Update `infer` to call `_connect_websocket(...)`, then `_send_session_config(...)` as the first message, then proceed with the existing message flow (audio append/commit, response handling) while preserving existing return shape.
- [x] Improve error handling based on patterns in `endpoints/realtime.py` (log details, forward structured errors, ensure cleanup in `finally`).
- [x] Ensure cleanup closes the WS connection reliably.

## Phase 4.5 — Event helper refactor (implemented)
- [x] Define a new event flow contract: Create -> Send -> Append
  - Create the event object first.
  - Send the created event to the WebSocket API.
  - Append the exact event object to the local `events` list.
- [x] Add factory helpers for creating events:
  - `create_event(self, ev_type: str) -> dict`
    - Returns a minimal event shape, e.g., `{ "type": ev_type }` (sequence/timestamp added when appending).
  - `create_audio_event(self, ev_type: str, audio_bytes: bytes) -> dict`
    - Returns `{ "type": ev_type, "audio": <audio> }`.
    - Decide `<audio>` representation (raw vs base64) and include `size` if helpful.
    - Consider truncation or a flag to avoid storing large payloads.
- [x] Update append API to accept a pre-built event:
  - `append_event(self, event: dict) -> None`
    - Adds `sequence` (and optional timestamp), pushes to `events`, and logs.
- [x] Migrate call sites in `infer` and `_receive_responses` to the new flow:
  - Replace direct send + inline append with:
    1) `ev = create_event(...)` or `ev = create_audio_event(...)`
    2) `await ws.send(serialize(ev))` (binary or JSON as appropriate)
    3) `await append_event(ev)`
  - Ensure binary frames from server are captured via `create_audio_event` + `append_event`.
- [x] Ensure `context["realtime_events"]` remains compatible with downstream utilities (sequence strictly increasing) and update tests in Phase 5 if schema changes.

## Phase 5 — Tests and validation
- [x] Keep existing tests in `tests/test_realtime_model.py` green
- [x] Add event-flow tests:
  - Audio append event shape (audio base64 + size, ordering append < commit < create)
  - Binary frames from server recorded as audio events
- [ ] Add additional tests around:
  - URL building and header construction.
  - Session config payload correctness (at least minimal snapshot or key assertions).
  - Error cases: missing env/config, connection failures.
- [x] Run all tests and fix any regressions.

## Phase 6 — Response handling refactor (updated to current state)
- Current state (reality check):
  - append_event already filters printing to only transcript-delta events.
  - _receive_responses currently handles: timeout, binary frames (redacted), first inbound marker, generic `error`, and `response.done` (closes and stops). It does not yet parse transcript deltas or aggregate `final_text`, and it does not append a trailing `response.final` event.
  - Session configuration currently sets modalities=["text"], turn_detection="none" (no transcription or server VAD).

- Goal: Simplify `_receive_responses` by aggregating the final text inside the same try block that processes inbound messages and keep printing restricted to transcript delta events. Append a single `response.final` event at loop end.

- Planned changes:
  - Parse `response.audio_transcript.delta` messages; accumulate `final_text` from their `delta` field in-order.
  - Also support `response.output_text.delta` and the generic `response.delta` (where delta.text is present) for compatibility; do not print these, but still accumulate.
  - Keep printing policy: stdout/rich only for `response.audio_transcript.delta` events (append_event filter already in place).
  - On `response.completed`/`session.completed` or `response.done`, close WS and break the loop.
  - After loop: append `{"type": "response.final", "text": final_text or ""}`.

- Tests to add/adjust:
  - Verify stdout only includes `response.audio_transcript.delta` prints while all events are still appended.
  - Verify `final_text` equals concatenation of transcript deltas; include compatibility with `response.output_text.delta` and `response.delta.text`.
  - Verify completion closes WS and `response.final` is appended exactly once.
  - Maintain strictly increasing `sequence` across all events.

## Phase 6.1 — Event timestamps (new)
- Add a timestamp to each appended event for better observability.
  - Implementation: in `append_event`, add `import time` and set `record["timestamp"] = time.time()` (float seconds since epoch).
  - Keep `sequence` as the strict ordering source of truth; `timestamp` is for diagnostics and may be equal for rapid events.
  - Do not change existing tests’ expectations; add a small test asserting `timestamp` exists and is a float for a couple of events.
  - Optional enhancement: consider ISO8601 in a sibling `timestamp_iso` if human readability is needed.

## Edge cases to account for
- Missing or empty `AZURE_OPENAI_*` settings.
- Incorrect endpoint casing or trailing slashes (normalize with `.rstrip('/')`).
- Large frames (`max_size`) for base64 audio chunks.
- Timeouts or transient network faults (clear error messages and resource cleanup).
- Optional prompt file not present (log warning, proceed with empty instructions).

## Success criteria
- Public import and signature unchanged.
- Tests pass without consumer-side changes.
- First message after connect is `session.update` with valid config.
- Cleaner separation of concerns: connect vs config send vs message flow.

## Rollout
- [ ] Land Phase 1 (extraction) in a small PR.
- [ ] Land Phases 2–4 in a follow-up PR.
- [ ] Add/adjust tests in Phase 5 and finalize.
