# Planning

This folder holds planning documents for features and improvements, structured to be Copilot-friendly and implementation-driven.

Conventions (per-feature folders):
- Create a folder per feature: `planning/yyyy-mm-dd-feature-slug/`
- Inside each folder:
	- `feature-plan.md` — problem, goals, design, impacted code, tests, rollout
	- `implementation-plan.md` — step-by-step checklist the agent will follow
- Keep actionable checklists up to date; Copilot will use them to track progress

Suggested workflow:
1. Create a new folder for your feature
2. Copy `feature-plan-template.md` to `feature-plan.md`
3. Copy `implementation-plan-template.md` (optional) to `implementation-plan.md`
4. Fill in both plans with enough detail for implementation
5. Create a GitHub issue using `github-issue-template.md` and save it as `github-issue.md` in the same folder (link it in your PR)
5. Link to impacted files with backticks (e.g., `gotaglio/pipeline.py`)
6. Reference the plans from PR descriptions

Index (add your plans here):
- 2025-08-26-azure-openai-realtime/
- 2025-08-28-realtime-session-config/
