# AzureOpenAIRealtime Refactor Plan

Status summary (current): Phases 0–4 completed and integrated; Phase 4.5 (event helper refactor with Create → Send → Append flow) implemented; added new event-flow tests. Remaining: additional Phase 5 tests (URL/header, session payload, error cases) and rollout steps.

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
- [ ] Run all tests and fix any regressions.

## Phase 6 — Response handling refactor (planning only)
- Goal: Simplify `_receive_responses` by aggregating the final text inside the same try block that processes inbound messages and by filtering printed output to only relevant transcript deltas. Remove the heavy post-loop branching; keep a small post-loop "response.final" append only.

- What to change (targeting the logic that currently runs after events are appended; starts around the current line ~248 in implementation):
  - Move the construction of `final_text` into the main message-processing try block.
  - Only print (stdout/rich) inbound events whose `type` is `response.audio_transcript.delta`.
  - Build `final_text` exclusively from the `delta` field of `response.audio_transcript.delta` messages, concatenated in order.
  - Continue appending all events to `context["realtime_events"]` as before; the print filter should not affect event appending.

- Event factories for responses (clarified):
  - `create_response_event(ev_type: str, text: str | None = None, **kwargs) -> dict`
    - Unified shape: `{ "type": ev_type, "text": <optional>, ...extra }`.
    - Use for: `message`, `error`, `response.completed`, `session.completed`, `ws.first_message`, `binary` (size+redacted), `error.timeout`, and also for transcript deltas if we want a normalized `text` view.
  - Optionally keep a tiny helper for transcript deltas: `create_transcript_delta(delta_text: str) -> dict` returning `{ "type": "response.audio_transcript.delta", "text": delta_text }` to standardize appends.

- Processing flow in `_receive_responses` (reduced and focused):
  Signature remains: `_receive_responses(ws, timeout_s, create_response_event, append_event)`.
  1) Read next frame from the WS with timeout.
  2) If binary: append `create_response_event("binary", size=len(raw), redacted=True)` and continue (do not print).
  3) If text JSON: parse and branch by `type`:
     - `response.audio_transcript.delta`:
       - Extract `delta = (message.get("delta") or "")`.
       - Accumulate: `final_text = (final_text or "") + delta`.
       - Append: `await append_event(create_response_event("response.audio_transcript.delta", text=delta))` (also retain raw fields if desired via kwargs).
       - Print this event only (filtered) for live feedback.
     - `response.output_text.delta`:
       - Treat as non-printed textual delta for compatibility: extract `delta`, accumulate into `final_text`, append an event. Do not print.
     - `response.delta` (generic):
       - If present, handle like above for compatibility, but prefer the specific `response.audio_transcript.delta` path when available.
     - `response.completed` or `session.completed`:
       - Append completion event; optionally call `await ws.close()` and break loop.
     - `error`:
       - Append structured error event with payload for diagnostics; decide whether to stop or continue based on severity.
     - Unknown types:
       - Append as a generic `message` event with the raw payload for later inspection; do not print.
  4) After loop ends due to completion or timeout, append a single `{"type": "response.final", "text": final_text or ""}` event.

- WebSocket closure:
  - On receiving `response.completed` (or `session.completed`), gracefully close the socket after appending the completion event(s). Ensure `async with` exits cleanly; call `await ws.close()` proactively inside the branch if helpful. Handle any close exceptions with a benign `ws.close_error` event.

- Printing policy (new):
  - Only print events with `type == "response.audio_transcript.delta"`.
  - All other inbound events are still appended to `realtime_events` but are not printed to stdout.

- Tests to add in Phase 6:
  - Verify that only `response.audio_transcript.delta` events are printed (mock/spy the print function or capture stdout) while all events are appended.
  - Verify that `final_text` equals the concatenation of all `delta` values from `response.audio_transcript.delta` (and optionally include `response.output_text.delta` for backward compatibility).
  - Verify completion triggers WS close (mockable), no double-closes, and that `response.final` is appended exactly once with the aggregated text.
  - Maintain strictly increasing `sequence` across all events.

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
