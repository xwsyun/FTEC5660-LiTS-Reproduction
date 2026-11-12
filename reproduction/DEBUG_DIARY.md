# Debug diary

## 2026-11-12: selection and setup

- Selected instructor-listed LiTS, Crosswords chain baseline, because upstream includes static puzzle data and a deterministic exact word evaluator.
- Fixed upstream revision before changes; plan recorded in PROTOCOL.md before outcomes were observed.
- Avoided full optional GPU/database installation for a hosted-API-only experiment. Building an isolated Python 3.12 environment with the actual imported dependencies.
- Initial pip resolution including aioboto3 caused extensive dependency backtracking; cancelled this installation and removed the unused async Bedrock dependency from the focused environment.
- Existing API access was checked without printing credentials. Model discovery returns deepseek-flash and deepseek-v4-pro. Use the former; do not assume the older homework model name remains available.
- LiTS originally uses a vLLM-style thinking toggle for custom endpoints. Added the documented DeepSeek thinking toggle in the shared model adapter, equally in both experiment arms.
- DeepSeek documentation says top_p is fixed at 1.0 for flash non-thinking mode. Updated the pre-run configuration accordingly.
- The exact original paper sample IDs and publication-time code are not established. Treat this as an adapted, scoped reproduction rather than a directly comparable benchmark replication.

## Smoke check and measured-run observations

- The initial smoke run exposed a harness assumption that EnvState had a history attribute. EnvState is iterable; using iteration fixed this before the measured run. The failed smoke evidence is kept separately and is not in the measured sample.
- Held-out index 99 completed under both prompts, and score/token aggregation passed. This was an execution check, not evidence for choosing or tuning the intervention.
- During measured-run inspection, a terminal action-error step without next_state was found to make EnvState.env_state fall back to init_state. The measured run keeps this behavior unchanged. A post-hoc audit reports the last valid trajectory board as a separate diagnostic.
- Some responses include explanations or invalid word lengths despite the action-only instruction. These are model action failures, retained in the outcomes. Upstream retries can increase actual calls beyond the ten-step limit.
- audit.py reconstructs each logged prompt from the current observed state and the fixed intervention, checks valid-response alignment to trajectory actions, and independently recomputes row/column scores.
