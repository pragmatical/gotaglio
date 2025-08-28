# Implementation plan — Realtime prompt update via session.update

## Pre-flight
- [ ] Confirm where pipeline-level config flows into model context (inspect `pipeline.py`, `pipeline_spec.py`)
- [ ] No new dependencies needed; reuse existing `websockets` and logging
- [ ] Ensure no breaking changes to model constructor or registration

## Implementation
- [ ] `_send_session_config`:
  - [ ] Resolve instructions by precedence: `context.get("instructions")` or `context.get("realtime", {}).get("instructions")` (pipeline), else `self._config.get("instructions")`, else current default behavior
  - [ ] Preserve existing options (voice, modalities, formats)
  - [ ] Send `session.update` payload
- [ ] `infer` mid-session update:
  - [ ] After sending `response.create`, check `context.get("session_update_instructions")` or `context.get("realtime", {}).get("session_update_instructions")`
  - [ ] If present and non-empty, send a second `session.update` with only the `instructions` field (or full session body) and append an event
- [ ] Event capture
  - [ ] Reuse existing `append_event` to record `session.update` sends (already done for the initial one); add a separate marker for the mid-session update
- [ ] Logging
  - [ ] Use `logging.getLogger(__name__)`; remove any stray prints in this path

## Validation
- [ ] Unit tests in `tests/test_azure_openai_realtime.py` or new test file
  - [ ] Test initial instructions precedence (context > pipeline key > model config > default)
  - [ ] Test that a mid-session update is sent when configured
  - [ ] Test that no update is sent when not configured
- [ ] Run `pytest -q`

## Samples and documentation
- [ ] Update `documentation/realtime.md` with instructions section
- [ ] Add example in `samples/realtime/` showing pipeline config with `realtime.instructions` and optional `realtime.session_update_instructions`

## Rollout
- [ ] No dependency updates required
- [ ] Note precedence in `README.md` if relevant
