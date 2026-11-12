"""Aggregate completed raw experiments; refuse incomplete or duplicate trials."""
import argparse
import csv
import json
from pathlib import Path
import statistics as stats

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--results",default="reproduction/results")
    args=p.parse_args()
    root=Path(args.results)
    config=json.loads((root/"config.json").read_text())
    records={}
    for path in root.glob("*/trial_*/puzzle_*/result.json"):
        row=json.loads(path.read_text())
        key=(row["condition"],row["trial"],row["index"])
        if key in records:
            raise ValueError(f"Duplicate completed job: {key}")
        logs=[json.loads(s) for s in (path.parent/"inferencelogger.log").read_text().splitlines() if s.strip()]
        row["input_tokens"]=sum(x["input_tokens"] for x in logs)
        row["output_tokens"]=sum(x["output_tokens"] for x in logs)
        assert len(logs)==row["calls"], (key,len(logs),row["calls"])
        row["source"]=str(path.relative_to(root))
        records[key]=row
    expected={(c,t,i) for c in ["baseline","crossing_prompt"] for t in range(config["trials"]) for i in config["indices"]}
    if set(records)!=expected:
        raise ValueError(f"Incomplete results: {len(records)}/{len(expected)}. Missing: {sorted(expected-set(records))[:10]}")
    trials=[]
    for c in ["baseline","crossing_prompt"]:
        for t in range(config["trials"]):
            rows=[records[(c,t,i)] for i in config["indices"]]
            trials.append({"condition":c,"trial":t,"n":len(rows),
                "word_accuracy":stats.mean(r["word_accuracy"] for r in rows),
                "puzzle_accuracy":stats.mean(int(r["solved"]) for r in rows),
                "calls":sum(r["calls"] for r in rows),
                "input_tokens":sum(r["input_tokens"] for r in rows),
                "output_tokens":sum(r["output_tokens"] for r in rows),
                "mean_seconds":stats.mean(r["seconds"] for r in rows),
                "invalid_action_jobs":sum(bool(r["errors"]) for r in rows)})
    summary={"config":config,"trials":trials,"conditions":{}}
    for c in ["baseline","crossing_prompt"]:
        subset=[r for r in trials if r["condition"]==c]
        summary["conditions"][c]={}
        for metric in ("word_accuracy","puzzle_accuracy","calls","input_tokens","output_tokens","mean_seconds","invalid_action_jobs"):
            vals=[r[metric] for r in subset]
            summary["conditions"][c][metric]={"mean":stats.mean(vals),
                 "sd":stats.stdev(vals) if len(vals)>1 else 0,
                 "variance":stats.variance(vals) if len(vals)>1 else 0}
    summary["paired_word_accuracy_deltas"]=[trials[config["trials"]+t]["word_accuracy"]-trials[t]["word_accuracy"] for t in range(config["trials"])]
    (root/"summary.json").write_text(json.dumps(summary,indent=2))
    with (root/"per_puzzle.csv").open("w") as f:
        keys=["condition","trial","index","solved","word_accuracy","calls","steps","seconds","input_tokens","output_tokens","source"]
        w=csv.DictWriter(f,keys,extrasaction="ignore"); w.writeheader(); w.writerows(records.values())
    print(json.dumps(summary,indent=2))

if __name__=="__main__": main()
