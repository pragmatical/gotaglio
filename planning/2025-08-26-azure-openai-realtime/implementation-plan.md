# Implementation plan — Azure OpenAI Realtime model

This plan defines discrete, verifiable steps for the agent to implement the feature. Check off each step as it’s completed.

## Pre-flight
- [ ] Confirm dependencies: choose `websockets` (or `aiohttp`) for WS client; add to `pyproject.toml`
- [ ] Verify lazy import pattern in `gotaglio/lazy_imports.py` and add import for chosen client
- [ ] Ensure no step-type changes are required (model-based implementation only)

## Model implementation
- [ ] Create `AzureOpenAIRealtime` class in `gotaglio/models.py`
  - [ ] Constructor stores config, registers model by name
  - [ ] `metadata()` returns config without secrets
  - [ ] `async infer(messages, context=None) -> str` implemented
- [ ] Input resolution in `infer`
  - [ ] Accept `context["audio_file"]` or `context["audio_bytes"]`
  - [ ] Read file bytes if path provided; error if neither present
- [ ] Connection details
  - [ ] Build WS URL from `endpoint`, `api` (api-version), and `deployment`
  - [ ] Send `api-key` header
- [ ] Session setup and streaming
  - [ ] Optionally send `session.update` with `voice` and `modalities`
  - [ ] Send `input_audio_buffer.start` with `sample_rate_hz`
  - [ ] Transmit audio bytes (single chunk MVP)
  - [ ] Send `input_audio_buffer.commit`
  - [ ] Send `response.create`
- [ ] Receive loop and event capture
  - [ ] Append ordered events with `sequence`, `type`, `ts`, `payload`
  - [ ] Accumulate `final_text` from `response.delta` events
  - [ ] Stop on `response.completed` or `session.completed` (or timeout)
  - [ ] Attach events to `context["realtime_events"]`
- [ ] Error handling
  - [ ] Timeout handling with partial events annotated
  - [ ] Add structured error event on exceptions

## Registration
- [ ] Update `register_models` in `gotaglio/models.py` to handle `AZURE_OPEN_AI_REALTIME`

## Samples and docs
- [ ] Add `samples/realtime/` with a small WAV file and a sample pipeline stage calling the model
- [ ] Add `documentation/realtime.md` describing configuration, case placeholder, and CLI usage

## Tests
- [ ] Unit tests using a mocked WS client
  - [ ] Happy path: connect, send audio, receive deltas and completed
  - [ ] Timeout path: ensure partial events and error recorded
  - [ ] Missing audio: raise validation error
  - [ ] Event order: strictly increasing `sequence`
- [ ] Ensure tests run via `pytest -q`

## Integration and telemetry
- [ ] Ensure logs flow through Python logging; no prints
- [ ] Optional: persist events to JSONL in a stage helper using `shared.write_log_file`

## Rollout
- [ ] Add `websockets` (or `aiohttp`) to `pyproject.toml`
- [ ] Note feature flag `GOTAGLIO_ENABLE_REALTIME` (if applicable)
- [ ] Update `README.md` or `documentation/realtime.md`
