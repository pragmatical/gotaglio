# Support Azure OpenAI Realtime API in pipelines

## Problem
We need to run speech-in/speech-out and streamed text/audio interactions against Azure OpenAI Realtime API from a gotaglio pipeline. The API streams many event types over WebSocket or WebRTC. Today, gotaglio lacks a first-class pipeline step that:
- Accepts local audio input (file/bytes/stream)
- Initiates a Realtime session (WS first; optional WebRTC later)
- Sends audio and receives streamed events
- Captures and persists all events for assessment/analysis
- Exposes a simple contract for downstream steps and CLI users

## Goals (acceptance criteria)
- [ ] New pipeline step type that performs realtime inference against Azure OpenAI (WebSocket transport MVP)
- [ ] Input: audio file path or bytes (16 kHz mono PCM/WAV/MP3/Opus; document supported codecs)
- [ ] Output: structured result containing final transcript, model responses, plus a complete ordered list of raw streamed events
- [ ] Capture 100% of event frames/messages with timestamps and types for assessment
- [ ] Config via model/step options: endpoint, api version, resource, deployment, key/credential, transport (ws|webrtc), timeouts, sampling rate
- [ ] Graceful handling of reconnects/timeouts; partial session captured with error metadata
- [ ] Unit tests with mocked WebSocket; deterministic event capture ordering
- [ ] CLI example and sample pipeline spec

## Non-goals
- Full WebRTC support in MVP (plan and interface slots included, implemented later)
- Browser client or UI; this is headless pipeline integration
- Multi-turn session orchestration beyond single audio input (can extend later)

## Design

### High-level flow
1. Resolve model configuration (Azure endpoint, api-version, deployment, key)
2. Open Realtime connection (WebSocket MVP)
3. Initialize session parameters (voice, modalities, transcription settings)
4. Stream or upload audio content
5. Receive streamed events; normalize to internal `RealtimeEvent` records and append to `EventCapture`
6. Derive convenience outputs: final transcript, final text response(s), optional audio output references if provided by API
7. Close connection and return `RealtimeResult`

### Public pipeline API
- Step kind: `realtime_infer` (alias: `azure_realtime_infer`)
- Inputs
  - `audio`: str|bytes|pathlib.Path (path to audio file) or an iterator of bytes for streaming (optional in MVP; start with file)
  - `options` (dict):
    - `transport`: "ws" | "webrtc" (default: "ws")
    - `sample_rate_hz`: int (default 16000)
    - `format`: "wav"|"mp3"|"flac"|"opus" (best-effort detection from file extension)
    - `timeout_s`: float (default 60)
    - `save_events_path`: Optional[str] — if provided, persist captured events as JSONL
  - `model` (dict or model name mapped via `models.json`):
    - `provider`: "azure-openai"
    - `deployment`: string
    - `api_version`: string
    - `endpoint`: string (https://{resource}.openai.azure.com)
    - `key`: env var name or direct value (prefer env var)
- Outputs
  - `RealtimeResult`:
    - `events`: List[RealtimeEvent]
    - `transcript`: Optional[str]
    - `responses`: List[str] (aggregated text outputs, if any)
    - `meta`: dict (timings, reconnects, bytes sent, etc.)

### Data structures
- RealtimeEvent
  - `type`: str (e.g., "session.created", "response.delta", "response.completed", "input_audio.buffer.committed", "error")
  - `ts`: float (monotonic or utc iso string)
  - `payload`: dict (raw event content)
  - `sequence`: int (incremental index for ordering)
- EventCapture
  - Methods: `append(event)`, `to_jsonl(fp)`, `summary()`
- RealtimeResult
  - Aggregates events and derived fields (transcript, responses)

### Transport and client
- MVP: WebSocket using `websockets` or `aiohttp` client; keep implementation async internally with a sync wrapper for pipeline compatibility
- Optional future: WebRTC using `aiortc` (behind feature flag)

### Authentication
- Azure OpenAI Realtime requires the Azure resource endpoint, API version, and either API key or AAD bearer token
- Support API key via `AZURE_OPENAI_API_KEY` or step-level `key` resolved from env

### Event normalization
- Maintain received order using a local `sequence` counter
- Add `received_at` timestamp for latency analysis
- Preserve raw payload for later parsing; derive transcript/responses using event types defined by Azure Realtime

### Persistence
- If `save_events_path` provided, write as JSONL (one event per line) plus a compact `result.json` with summary
- Optional: store audio copy into sibling folder for reproducibility

### Error handling
- Timeouts: cancel send/recv tasks, return partial events with `meta.error`
- Protocol errors: include last event and server error payloads
- Network errors: retry connect once (configurable), annotate in `meta`

### CLI example
- Example invocation via pipeline spec and `gotag run` that points to `samples/` audio file

## Impacted code
- `gotaglio/pipeline.py`: add new step execution path for `realtime_infer`
- `gotaglio/pipeline_spec.py`: schema/validation for new step kind and options
- `gotaglio/models.py`: allow Azure OpenAI realtime-capable model config fields
- `gotaglio/registry.py`: register new step kind
- `gotaglio/endpoints/realtime.py`: leverage or extend if present; otherwise create `endpoints/azure_realtime.py`
- `gotaglio/subcommands/run_cmd.py`: no change expected; ensure args pass-through works
- `samples/` and `documentation/`: add sample and docs
- New: `gotaglio/clients/azure_realtime.py` (client + DTOs)

## Edge cases and risks
- Large audio files causing long send times or server-side truncation
- Unsupported codecs or sample rates; require conversion (follow-up: ffmpeg/sox integration)
- Clock skew in timestamps; we use local receive time for ordering
- Partial sessions due to disconnects; ensure events flushed to disk
- Secrets handling in logs; scrub keys and auth headers
- Azure deployment model differences (region, apiVersion variability)

## Test plan
- Unit tests (mocked transport):
  - Connect -> send audio -> receive deterministic sequence of events -> verify `events`, `transcript`, `responses`
  - Timeout path returns partial events and proper meta
  - Persistence: JSONL written and loadable
- Integration tests (optional, skipped w/o creds):
  - Real connect to Azure with short sample audio; verify at least basic event flow
- Contract tests:
  - Step schema validation errors on missing required fields

## Migration/compat
- Backwards compatible; adds new step kind. No breaking changes.
- Env vars: `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_API_VERSION`, `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_DEPLOYMENT` (usable defaults when not specified at step)

## Rollout
- Feature flag: `GOTAGLIO_ENABLE_REALTIME` (default on if deps available)
- Log metrics: total events, bytes sent/received, duration, error count
- Docs: add `documentation/realtime.md` and sample pipeline

## Example pipeline spec (illustrative)
```jsonc
{
  "name": "azure-realtime-transcribe-and-respond",
  "steps": [
    {
      "id": "infer",
      "kind": "realtime_infer",
      "model": {
        "provider": "azure-openai",
        "endpoint": "${AZURE_OPENAI_ENDPOINT}",
        "api_version": "2024-06-01",
        "deployment": "gpt-4o-realtime-preview",
        "key": "${AZURE_OPENAI_API_KEY}"
      },
      "inputs": {
        "audio": "samples/audio/hello.wav"
      },
      "options": {
        "transport": "ws",
        "sample_rate_hz": 16000,
        "timeout_s": 45,
        "save_events_path": "logs/runs/${run_id}/events.jsonl"
      }
    }
  ]
}
```

## Tasks
- [ ] Define DTOs: `RealtimeEvent`, `RealtimeResult`, `EventCapture`
- [ ] Implement `clients/azure_realtime.py` (WS MVP): connect, send audio, receive events, normalize, capture
- [ ] Add pipeline step execution in `pipeline.py` and register kind in `registry.py`
- [ ] Extend `pipeline_spec.py` to validate new step schema and options
- [ ] Add model fields in `models.py` with env resolution helpers
- [ ] Persistence: JSONL writer and summary artifact
- [ ] Unit tests with transport mocks; contract tests for schema validation
- [ ] Sample audio and pipeline under `samples/realtime/`
- [ ] Docs page `documentation/realtime.md`
- [ ] Optional: add `--save-events` CLI flag passthrough
- [ ] Optional (follow-up): WebRTC transport via `aiortc`

## Links
- Azure OpenAI Realtime: https://learn.microsoft.com/azure/ai-services/openai/realtime-overview
- Example event types: https://learn.microsoft.com/azure/ai-services/openai/realtime-websocket
- Gotaglio files: `gotaglio/pipeline.py`, `gotaglio/pipeline_spec.py`, `gotaglio/models.py`, `gotaglio/registry.py`
