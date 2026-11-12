# FTEC5660: LiTS crossword reproduction protocol

Recorded before the measured experiment, 2026-11-12 (Hong Kong).

## Scope and source

- Instructor list project 3: https://github.com/xinzhel/lits-llm
- Upstream revision: 25e94d862cb4514c22d9a80a635e392461769df7
- Paper: https://arxiv.org/html/2603.00631v1, Table 3, Crosswords / Chain.
- Reported reference: 6.67% full-puzzle accuracy, 10.33% mean word accuracy, 30 examples, Claude 3.5 Sonnet. These are contextual references, NOT expected matching numbers under a different model and sample.
- Reuse upstream EnvChain, EnvGroundedPolicy, CrosswordsTransition, data loader, and scoring. Do not reimplement the agent.

## Planned experiment

- A held-out smoke-test puzzle at index 99 is for debugging only.
- Measured sample: first 30 puzzles of demos/crosswords/data/mini0505.json (indices 0-29), chosen before examining outputs.
- Three independent trials per condition. API stochasticity is not guaranteed reproducible by local RNG seeds.
- Baseline: original crossword user prompt.
- Modified: append one instruction block encouraging cross-letter consistency and selection of constrained entries; no extra answer information, tools, search, retries, or budget.
- Both: deepseek-flash (API model listing identifies DeepSeek-V4.1-Flash), non-thinking mode, temperature 0.8, top_p 1.0, max output 128 tokens per call, 10 environment steps. DeepSeek documentation fixes top_p to 1.0 in this mode.
- Retain original action-validation/retry behavior. Count all actual calls, including retries.
- Alternate condition order between trials. At most three puzzles in flight.
- Primary metric: final-board word accuracy (correct rows and columns / 10), averaged over puzzles. Secondary: exact puzzle success, actual calls, input/output tokens, wall time, action errors.
- Report mean and sample standard deviation/variance over the three trial-level averages. No claim of statistical significance or population generalization from a small convenience sample.
- Failed API jobs must be recorded separately, not silently scored as wrong or dropped. Resume only incomplete jobs.

## Comparability limitations

The model differs from the paper; current upstream revision may differ from the publication revision. The exact paper subset IDs and chain configuration must be checked; do not claim an exact replication if unavailable. This is a scoped reproduction of the multi-step chain behavior with an isolated prompt intervention.

## Integrity

Ground-truth answers stay in the environment evaluator and must not appear in model prompts. Keep raw prompts/responses, trajectories, configuration, dataset hash, and per-puzzle outcomes. Do not select the best trial. No keys in logs or commits.
