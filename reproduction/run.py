"""Run upstream LiTS crossword chains with a single prompt intervention."""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import json
import logging
import os
from pathlib import Path
import random
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "demos")]
from dotenv import load_dotenv
from lits.agents.chain.env_chain import EnvChain
from lits.components.policy.env_grounded import EnvGroundedPolicy
from lits.lm.openai_chat import OpenAIChatModel
from lits.lm.base import InferenceLogger
from lits.prompts.prompt import PromptTemplate
from lits_benchmark.crosswords import (
    CrosswordsTransition, crosswords_policy_usr_prompt, load_crosswords,
)

INTERVENTION = """
Before selecting the single action, check the crossing letters already on the board.
Prefer an unfilled entry with several known letters and a confident clue match.
Choose a word that matches both its clue and its existing crossing letters; avoid
overwriting a confident crossing answer with a conflicting guess. If one entry
is uncertain, choose another unfilled entry. Still output ONLY position. word.
"""

class LoggedModel(OpenAIChatModel):
    def __init__(self, *args, trace_path, **kwargs):
        super().__init__(*args, **kwargs)
        self.trace_path = trace_path
        self.calls = 0
        self.api_errors = []

    def __call__(self, prompt, **kwargs):
        started = time.perf_counter()
        self.calls += 1
        try:
            result = super().__call__(prompt, **kwargs)
        except Exception as exc:
            self.api_errors.append(type(exc).__name__)
            raise
        row = {"call": self.calls, "prompt": prompt, "response": result.text,
               "seconds": time.perf_counter() - started,
               "parameters": {k:v for k,v in kwargs.items() if k in
                              ("temperature", "top_p", "max_new_tokens", "role")}}
        with self.trace_path.open("a") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
        return result

def job(args, examples, condition, trial, index):
    out = Path(args.output) / condition / f"trial_{trial}" / f"puzzle_{index:03d}"
    if (out / "result.json").exists():
        return json.loads((out / "result.json").read_text())
    # Never mix a retry with an incomplete trace.
    if out.exists() and any(out.iterdir()):
        out = out.with_name(out.name + f"_retry_{int(time.time())}")
    out.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    model = LoggedModel(args.model, api_key=os.environ["DEEPSEEK_API_KEY"],
                        base_url="https://api.deepseek.com", max_new_tokens=128,
                        inference_logger=InferenceLogger(root_dir=str(out)),
                        recovery_timeout=0, trace_path=out / "calls.jsonl")
    model.client = model.client.with_options(timeout=45, max_retries=0)
    template = crosswords_policy_usr_prompt()
    if condition == "crossing_prompt":
        template = PromptTemplate(template.template + INTERVENTION,
                                  list(template.input_variables))
    policy = EnvGroundedPolicy(
        base_model=model, task_name="crosswords", usr_prompt_spec=template,
        validate_action=CrosswordsTransition.validate_action,
        n_actions=1, temperature=0.8, top_p=1.0, max_new_tokens=128,
        max_steps=10, force_terminating_on_depth_limit=False)
    world = CrosswordsTransition(base_model=model)
    agent = EnvChain(policy, world, max_steps=10)
    item = examples[index]
    try:
        state = agent.run(item["query_or_goals"], item["init_state_str"],
                          query_idx=index, checkpoint_path=str(out / "trajectory.json"))
        solved, accuracy = world.goal_check(item["query_or_goals"], state.env_state)
        row = {"condition":condition, "trial":trial, "index":index,
               "solved":bool(solved), "word_accuracy":accuracy, "calls":model.calls,
               "steps":len(state), "seconds":time.perf_counter()-started,
               "final_board":state.env_state}
        # Invalid model actions count toward performance; transport failures do not.
        errors = [str(s.error) for s in state if s.error]
        row["errors"] = errors
        if model.api_errors:
            raise RuntimeError("API failures: " + repr(model.api_errors))
        (out / "result.json").write_text(json.dumps(row, indent=2))
        return row
    except Exception as exc:
        (out / "error.json").write_text(json.dumps({"type":type(exc).__name__,
            "message":str(exc), "condition":condition, "trial":trial, "index":index},indent=2))
        raise

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--env-file")
    p.add_argument("--model", default="deepseek-flash")
    p.add_argument("--output", default="reproduction/results")
    p.add_argument("--smoke", action="store_true")
    p.add_argument("--workers", type=int, default=3)
    args = p.parse_args()
    if args.env_file:
        load_dotenv(args.env_file)
    else:
        load_dotenv()
    logging.basicConfig(level=logging.WARNING)
    data = ROOT / "demos/crosswords/data/mini0505.json"
    examples = load_crosswords(str(data))
    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)
    config = {"model":args.model, "base_url":"https://api.deepseek.com",
              "dataset_sha256":hashlib.sha256(data.read_bytes()).hexdigest(),
              "indices":[99] if args.smoke else list(range(30)),
              "trials":1 if args.smoke else 3, "temperature":0.8,"top_p":1.0,
              "thinking":"disabled",
              "max_steps":10,"max_new_tokens":128,
              "intervention":INTERVENTION, "upstream":"25e94d862cb4514c22d9a80a635e392461769df7"}
    (out / "config.json").write_text(json.dumps(config,indent=2))
    for trial in range(config["trials"]):
        conditions = ["baseline", "crossing_prompt"]
        if trial % 2:
            conditions.reverse()
        for condition in conditions:
            with ThreadPoolExecutor(max_workers=args.workers) as pool:
                jobs = [pool.submit(job,args,examples,condition,trial,i) for i in config["indices"]]
                for future in as_completed(jobs):
                    row = future.result()
                    print(json.dumps({k:row[k] for k in
                        ("condition","trial","index","word_accuracy","calls","seconds")}),flush=True)

if __name__ == "__main__":
    main()
