# FTEC5660 individual reproducibility project

## Research question

Can the released LiTS environment-grounded chain solve mini crosswords using an accessible hosted model, and does a crossing-consistency prompt change final word accuracy under an unchanged execution budget?

This directory contains a scoped, model-substituted reproduction of the **Crosswords / Chain** experiment in Table 3 of LiTS (arXiv:2603.00631v1), plus one isolated user-prompt intervention. It is not a reproduction of the full paper or its MCTS result.

## Install and run

Use Python 3.12. From the repository root:

```sh
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r reproduction/requirements.txt
```

Create a local ignored `.env` containing `DEEPSEEK_API_KEY=your_key`.

```sh
python reproduction/checks.py
unzip -n reproduction/results.zip -d reproduction
python reproduction/analyze.py --results reproduction/results
python reproduction/audit.py --results reproduction/results
```

For new API experiments:

```sh
python reproduction/run.py --smoke --output reproduction/smoke_new
python reproduction/run.py --output reproduction/results_new
python reproduction/analyze.py --results reproduction/results_new
```

The smoke check uses puzzle 99, which is excluded from the measured sample. The full experiment uses indices 0-29, both conditions and three trials, at most three puzzle jobs at a time. It makes real billable API calls; counts include upstream invalid-action retries. See PROTOCOL.md for controls and limitations. Run with a new output directory to conduct a genuinely new experiment; the runner skips completed jobs in an existing directory.

## What is reused and what is changed

- Upstream commit: `25e94d862cb4514c22d9a80a635e392461769df7`.
- Reused unchanged: EnvChain, EnvGroundedPolicy, CrosswordsTransition, original puzzle loader/data and exact board scorer.
- Shared compatibility adaptation: DeepSeek thinking toggle in `lits/lm/openai_chat.py`. Both conditions use non-thinking mode.
- Experimental change: `INTERVENTION` in `reproduction/run.py`, appended only for `crossing_prompt`.
- Experimental model: `deepseek-flash`, which the API identifies as DeepSeek-V4.1-Flash at setup time. It differs from the paper's Claude 3.5 Sonnet.
- No reference answers are interpolated into model prompts. Tests check this boundary.

## Artifacts

Each completed puzzle has `result.json`, `trajectory.json`, `calls.jsonl` and `inferencelogger.log`. The analyzer checks completeness, detects duplicate completed runs, reconciles calls against token records, and produces `summary.json` and `per_puzzle.csv`. Incomplete infrastructure failures are preserved as `error.json`; invalid model actions remain part of the measured performance.

## Measured results (180 completed jobs)

| Metric, mean +/- sample SD across 3 trials | Original | Crossing prompt |
|---|---:|---:|
| Returned-state word accuracy | 26.22 +/- 3.08% | 18.56 +/- 1.71% |
| Exact puzzle accuracy | 3.33 +/- 0.00% | 0.00 +/- 0.00% |
| Calls per 30-puzzle trial | 346.67 +/- 6.03 | 351.67 +/- 6.11 |

The modification reduced mean word accuracy by 7.67 percentage points. This is a negative result, not evidence of an improvement. All 180 outcomes are retained. The post-hoc last-valid-board diagnostic is 28.89% versus 21.67%; the original terminal-error state fallback is unchanged in the primary analysis.

The run was interrupted after 173 completed jobs and resumed the seven unfinished jobs on 13 November. Partial traces are retained. Completed-job token totals exclude abandoned partial attempts; this interruption is a temporal limitation.

Raw evidence is in `results.zip` (extract once with the command above). [summary.json](summary.json), [per_puzzle.csv](per_puzzle.csv), and [audit.json](audit.json) are convenient copies of the archived aggregates. The audit checks every prompt and score. [Report](FTEC5660_Reproducibility_Report.pdf); [recording notes](recording_notes_zh.txt).

To regenerate the report, install `requirements-report.txt` and run `python reproduction/build_report.py --output report-output` after extracting and auditing the results. The report generator consumes the completed evidence only.

## Sources

- Paper: https://arxiv.org/html/2603.00631v1
- Authors' code: https://github.com/xinzhel/lits-llm
- DeepSeek thinking control: https://api-docs.deepseek.com/guides/thinking_mode/

Original Apache-2.0 license and attribution remain in the repository.
