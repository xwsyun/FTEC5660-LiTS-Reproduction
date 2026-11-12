"""Offline integrity checks for the upstream scorer and prompt boundary."""
from pathlib import Path
import re
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "demos")]
from lits_benchmark.crosswords import load_crosswords, CrosswordsTransition, crosswords_policy_usr_prompt

data = load_crosswords(str(ROOT / "demos/crosswords/data/mini0505.json"))
assert len(data) >= 100
for x in data:
    blank = x["init_state_str"]
    assert CrosswordsTransition.goal_check(x["query_or_goals"], blank) == (False, 0.0)
    rows = x["query_or_goals"].splitlines()[:5]
    perfect = "Current Board:\n" + "\n".join(rows) + "\n\n"
    assert CrosswordsTransition.goal_check(x["query_or_goals"], perfect) == (True, 1.0)
    bad = list("".join(rows))
    bad[0] = "Z" if bad[0] != "Z" else "X"
    damaged = "Current Board:\n" + "\n".join("".join(bad[i:i+5]) for i in range(0,25,5)) + "\n\n"
    assert CrosswordsTransition.goal_check(x["query_or_goals"], damaged) == (False, 0.8)
    sentinel = "PRIVATE_GROUND_TRUTH_MUST_NOT_ENTER_PROMPT"
    prompt = crosswords_policy_usr_prompt().format(init_state=blank,goals=sentinel,actions="")
    assert sentinel not in prompt
print(f"PASS: {len(data)} puzzles: blank/perfect/corrupt-board scoring and answer boundary")
