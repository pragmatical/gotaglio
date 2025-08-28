# Implementation plan - Realtime session config (voice, turn_detection, modalities)

This plan defines discrete, verifiable steps to implement configurable session parameters for the Azure OpenAI Realtime model.

## Pre-flight
- [ ] Confirm no dependency changes needed (pure config/validation change)
- [ ] Ensure logging stays via `logging.getLogger(__name__)`; no prints
- [ ] No feature flags required; maintain defaults for backward compatibility

## Implementation
- [ ] Update `gotaglio/azure_openai_realtime.py`
  - [ ] Add private helpers:
    - [ ] `_resolve_opt(context, key, default)` to apply precedence: `context[key]` > `context.get("realtime", {}).get(key)` > `self._config.get(key, default)`
    - [ ] `_normalize_modalities(value)` to validate literals and return a deduped, order-preserving list
    - [ ] `_normalize_turn_detection(value)` to support `None` -> `{ "type": "none" }`, and pass-through for `server_vad`/`semantic_vad` with validation; raise on unknown `type`
  - [ ] In `_send_session_config`, resolve and include `voice`, `modalities`, `turn_detection` using the helpers
  - [ ] Validation errors raise `ValueError` with clear messages
- [ ] Add docstrings/comments explaining supported shapes

## Validation
- [ ] Update `tests/test_azure_openai_realtime.py`
  - [ ] Add tests asserting emitted session payload for:
    - [ ] Defaults (unchanged behavior)
    - [ ] `voice` override via model config and via `context`
    - [ ] `modalities` override valid and invalid values
    - [ ] `turn_detection=None` (disabled), `server_vad`, and `semantic_vad`
    - [ ] Precedence: `context` > model config
- [ ] Run tests and iterate until green

## Samples and documentation
- [ ] Update `documentation/realtime.md` with examples for configuring these fields
- [ ] Optionally add examples in `models.json.template`

## Rollout
- [ ] No dependency updates required in `pyproject.toml`
- [ ] Update planning index in `planning/README.md`

Contract notes for helpers
- _normalize_modalities(value)
  - Input: list[str] or str (comma-separated is NOT supported; raise)
  - Allowed members: "text", "audio"
  - Output: list[str] with unique values in original order (e.g., ["text", "audio"]) 
  - Raises ValueError on invalid members or types
- _normalize_turn_detection(value)
  - Input: None or dict
  - None -> {"type": "none"}
  - dict.type in {"server_vad", "semantic_vad"} -> pass through only known keys
    - server_vad known keys: threshold, prefix_padding_ms, silence_duration_ms, create_response, interrupt_response
    - semantic_vad known keys: eagerness, create_response, interrupt_response
  - Unknown type -> ValueError
