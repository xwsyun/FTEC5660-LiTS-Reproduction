"""Audit saved evidence offline; supplementary last-valid-state analysis is post hoc."""
import argparse
import json
from pathlib import Path
import statistics as stats
from run import INTERVENTION, crosswords_policy_usr_prompt, CrosswordsTransition

def score(query, board):
    rows = board.split('Current Board:\n', 1)[1].splitlines()[:5]
    assert len(rows) == 5 and all(len(r) == 5 for r in rows)
    words = rows + [''.join(r[c] for r in rows) for c in range(5)]
    return sum(a == b for a, b in zip(words, query.splitlines())) / 10

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--results', default='reproduction/results')
    args = p.parse_args()
    root = Path(args.results)
    summary = json.loads((root/'summary.json').read_text())
    diagnostics = []
    for path in sorted(root.glob('*/trial_*/puzzle_*/result.json')):
        r = json.loads(path.read_text())
        traj = json.loads((path.parent/'trajectory.json').read_text())
        calls = [json.loads(s) for s in (path.parent/'calls.jsonl').read_text().splitlines()]
        assert len(calls) == r['calls']
        state, steps = traj['state']['init_state'], traj['state']['steps']
        pos = invalid = 0
        template = crosswords_policy_usr_prompt()
        for call in calls:
            expected = template.format(init_state=state, goals=traj['query'], actions='')
            if r['condition'] == 'crossing_prompt':
                expected += INTERVENTION
            assert call['prompt'] == expected, (path, call['call'], 'prompt mismatch')
            action = call['response'].strip()
            if CrosswordsTransition.validate_action(state, action):
                assert steps[pos]['action'] == action
                state = steps[pos]['next_state']
                pos += 1
            else:
                invalid += 1
        returned = steps[-1].get('next_state') or traj['state']['init_state']
        assert returned == r['final_board']
        assert score(traj['query'], returned) == r['word_accuracy']
        assert r['solved'] == (r['word_accuracy'] == 1)
        diagnostics.append({k:r[k] for k in ('condition','trial','index')} | {
            'invalid_responses':invalid, 'last_valid_word_accuracy':score(traj['query'],state),
            'returned_word_accuracy':r['word_accuracy'],
            'state_fallback':state != returned, 'source':str(path.relative_to(root))})
    trials=[]
    for c in ('baseline','crossing_prompt'):
        for t in range(summary['config']['trials']):
            rows=[r for r in diagnostics if r['condition']==c and r['trial']==t]
            trials.append({'condition':c,'trial':t,
                'last_valid_word_accuracy':stats.mean(r['last_valid_word_accuracy'] for r in rows),
                'invalid_responses':sum(r['invalid_responses'] for r in rows),
                'state_fallback_jobs':sum(r['state_fallback'] for r in rows)})
    out={'status':'PASS','jobs_checked':len(diagnostics),
         'note':'Post-hoc diagnostic; primary returned-state endpoint is unchanged.',
         'trials':trials,'per_puzzle':diagnostics}
    (root/'audit.json').write_text(json.dumps(out,indent=2))
    print(json.dumps({k:v for k,v in out.items() if k!='per_puzzle'},indent=2))

if __name__=='__main__': main()
