"""Build the report and recording notes from audited evidence; no invented scores."""
import argparse
import json
from pathlib import Path
import statistics as st
from xml.sax.saxutils import escape
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, Image, Preformatted
from reportlab.lib.units import inch
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--results',default='reproduction/results')
    p.add_argument('--output',required=True)
    args=p.parse_args()
    root=Path(args.results); out=Path(args.output); out.mkdir(parents=True,exist_ok=True)
    s=json.loads((root/'summary.json').read_text()); audit=json.loads((root/'audit.json').read_text())
    assert audit['status']=='PASS' and audit['jobs_checked']==180
    c=s['conditions']; b=c['baseline']; m=c['crossing_prompt']
    delta=100*(m['word_accuracy']['mean']-b['word_accuracy']['mean'])
    direction='increased' if delta>0 else 'decreased' if delta<0 else 'left unchanged'
    total_calls=sum(x['calls'] for x in s['trials'])
    total_in=sum(x['input_tokens'] for x in s['trials']); total_out=sum(x['output_tokens'] for x in s['trials'])
    pct=lambda x:f'{100*x:.2f}%'
    avg=lambda d,k,scale=1:f"{d[k]['mean']*scale:.2f} +/- {d[k]['sd']*scale:.2f}"
    # A descriptive paired plot; trial points, not inferential confidence intervals.
    plt.rcParams.update({'font.size':11,'axes.spines.top':False,'axes.spines.right':False})
    fig,ax=plt.subplots(figsize=(6.7,2.7))
    for t in range(3):
        vals=[100*x['word_accuracy'] for x in s['trials'] if x['trial']==t]
        ax.plot([0,1],vals,color='black',marker=['o','s','^'][t],linestyle=['-','--',':'][t],label=f'Trial {t+1}',linewidth=1.6)
    ax.set_xticks([0,1],['Original prompt','Crossing prompt']);ax.set_ylabel('Final word accuracy (%)')
    ax.set_ylim(0,35);ax.grid(axis='y',alpha=.2);ax.legend(ncol=3,frameon=False,loc='upper center')
    fig.tight_layout();fig.savefig(out/'trial_accuracy.png',dpi=200);plt.close(fig)
    styles=getSampleStyleSheet()
    styles.add(ParagraphStyle(name='BodyX',fontName='Helvetica',fontSize=10.3,leading=14,spaceAfter=9,textColor=colors.black))
    styles.add(ParagraphStyle(name='SmallX',fontName='Helvetica',fontSize=8.5,leading=11,spaceAfter=6))
    styles.add(ParagraphStyle(name='H1X',fontName='Helvetica-Bold',fontSize=20,leading=24,spaceAfter=15,textColor=colors.black))
    styles.add(ParagraphStyle(name='H2X',fontName='Helvetica-Bold',fontSize=12,leading=16,spaceBefore=8,spaceAfter=7,textColor=colors.black))
    story=[]
    def para(t,style='BodyX'): story.append(Paragraph(t.replace('color="#146B72"','color="#000000"'),styles[style]))
    def head(t): para(t,'H1X')
    def sub(t): para(t,'H2X')
    def page(): story.append(PageBreak())
    def table(rows,widths=None):
        data=[[Paragraph(escape(str(v)).replace('\n','<br/>'),styles['SmallX']) for v in row] for row in rows]
        tab=Table(data,colWidths=widths,hAlign='LEFT',repeatRows=1)
        tab.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.white),('VALIGN',(0,0),(-1,-1),'TOP'),('BOTTOMPADDING',(0,0),(-1,-1),7),('TOPPADDING',(0,0),(-1,-1),7),('LINEBELOW',(0,0),(-1,0),.8,colors.black),('LINEBELOW',(0,1),(-1,-1),.3,colors.black)]))
        story.append(tab);story.append(Spacer(1,10))
    head('Reproducing LiTS Crossword Chains')
    para('A scoped reproduction with a crossing-consistency prompt intervention','H2X')
    para('FTEC5660 Individual Project 2 | Experimental run: 12-13 November 2026','SmallX')
    sub('Abstract')
    para(f'This project executes the released LiTS environment-grounded chain on 30 fixed 5x5 crosswords, with three stochastic trials per condition. The original prompt is compared with one appended instruction block that encourages cross-letter consistency. Both conditions use DeepSeek Flash with the same execution limits. Across 180 puzzle runs, final returned-state word accuracy changes from {avg(b,"word_accuracy",100)}% to {avg(m,"word_accuracy",100)}% (mean +/- sample SD across trial means), a difference of {delta:+.2f} percentage points. This is a model-substituted reproduction of a released multi-step agent behavior, not an exact replication of the paper benchmark.')
    sub('1. Target and rationale')
    para('The source is LiTS: A Modular Framework for LLM Tree Search [1,2], one of the instructor-listed projects. The specific target is the Crosswords / Chain row in Table 3, not MCTS, BFS, or the whole framework. That row reports 6.67% puzzle accuracy and 10.33% partial word accuracy on 30 examples with Claude 3.5 Sonnet. These values provide context only: the original subset IDs and publication-time configuration were not established, and this project changes the model and fixes its own sample and budget.')
    para('Crosswords provide a small, inspectable environment with an exact evaluator. The selected program is agentic: each model call chooses an action, the environment changes the board, and the next call observes that changed state. It is not a single prompt evaluated once.')
    sub('2. Reused architecture')
    table([['Stage','Released component and role'],['Observe / decide','EnvGroundedPolicy formats the current board and clues; the model returns one placement such as h1. apple.'],['Validate / act','CrosswordsTransition validates the action and writes letters into the board, including crossing entries.'],['Loop / evaluate','EnvChain repeats up to 10 steps; the exact goal checker evaluates rows and columns. A successful goal check can stop early.']],[105,390])
    para('The chain, policy, crossword transition, data loader, and scoring code remain unchanged. The goal checker uses reference answers internally, including for early stopping. Those answers are not included in model prompts. This oracle stopping behavior is inherited from the original chain.','SmallX')
    page();head('Controlled setup and intervention')
    sub('3. Experimental design')
    table([['Setting','Value shared by both conditions'],['Source revision','25e94d862cb4514c22d9a80a635e392461769df7'],['Sample','mini0505.json indices 0-29, selected before measured outputs; index 99 is a separate smoke check.'],['Replication','3 trials x 30 puzzles x 2 conditions = 180 runs. Condition order is reversed in trial 2. Up to 3 puzzle jobs run concurrently.'],['Model / endpoint','deepseek-flash (listed as DeepSeek-V4.1-Flash at setup); https://api.deepseek.com'],['Decoding','Thinking disabled; initial temperature 0.8; top_p 1.0; max output 128 tokens per call; one action per policy step.'],['Budget / retry','10 environment steps; original policy allows 3 attempts per action, with retry temperature increasing to 1.0. Actual API calls may exceed 10.'],['Primary endpoint','Returned-state word accuracy: correct rows plus correct columns, divided by 10. Puzzle success means all 10 are correct.']],[105,390])
    para('The dataset contains 156 puzzles. Its SHA-256 is<br/><font size="8">50590d5886fac5e0971f483df93668a8f3c638d8312a490655b869a93d569154</font>. No local random seed can guarantee deterministic hosted API outputs. Trial IDs identify repeated runs rather than matched random-number streams.')
    sub('4. The single experimental change')
    para('Only the modified condition appends this block to the original user prompt:')
    para(escape(s['config']['intervention']).replace('\n','<br/>'),'SmallX')
    para('Hypothesis: emphasizing existing crossing letters may reduce destructive placements and improve final word accuracy. The instruction does not enforce consistency in code, provide answers, add tools, increase the step limit, or add a separate verification call. Because early letters can be wrong, preserving them may also lock in mistakes.')
    para('A shared compatibility edit in lits/lm/openai_chat.py sends DeepSeek\'s documented thinking toggle [3], replacing the vLLM-style toggle only for this endpoint. Both arms use the same adapter. The original prompt has no system message in this configuration; the warnings about a missing system prompt do not indicate an absent user prompt.','SmallX')
    page();head('Measured results')
    sub('5. Primary outcomes')
    table([['Metric','Original prompt','Crossing prompt'],['Word accuracy (%)',avg(b,'word_accuracy',100),avg(m,'word_accuracy',100)],['Puzzle accuracy (%)',avg(b,'puzzle_accuracy',100),avg(m,'puzzle_accuracy',100)],['API calls / 30-puzzle trial',avg(b,'calls'),avg(m,'calls')],['Input tokens / trial',avg(b,'input_tokens'),avg(m,'input_tokens')],['Output tokens / trial',avg(b,'output_tokens'),avg(m,'output_tokens')],['Seconds / puzzle',avg(b,'mean_seconds'),avg(m,'mean_seconds')],['Jobs with terminal action error / trial',avg(b,'invalid_action_jobs'),avg(m,'invalid_action_jobs')]],[215,140,140])
    para('Entries are mean +/- sample SD across three trial-level values. Timing measures each puzzle\'s elapsed duration while jobs run concurrently, not serial benchmark latency. Token counts are API usage records; no monetary estimate is inferred from current pricing.','SmallX')
    para('The process stopped after 173 completed jobs and resumed the seven unfinished jobs on 13 November. Incomplete traces are preserved separately; cost totals below cover completed jobs only. This interruption adds a time-of-run limitation.','SmallX')
    story.append(Image(str(out/'trial_accuracy.png'),width=495,height=199.5))
    table([['Trial','Original word %','Modified word %','Difference (pp)']]+[[t+1,f"{s['trials'][t]['word_accuracy']*100:.2f}",f"{s['trials'][t+3]['word_accuracy']*100:.2f}",f"{s['paired_word_accuracy_deltas'][t]*100:+.2f}"] for t in range(3)],[65,145,145,140])
    para(f'The prompt intervention {direction} mean final word accuracy by {abs(delta):.2f} percentage points in this sample. Across both arms there were {total_calls:,} API calls, {total_in:,} input tokens and {total_out:,} output tokens. All 180 completed outcomes are included. No best-trial selection is used.')
    para(f'Sample variances of trial mean word accuracy (fraction scale) are {b["word_accuracy"]["variance"]:.8f} and {m["word_accuracy"]["variance"]:.8f}. Three trials and a fixed convenience sample do not establish statistical significance or generalization.','SmallX')
    page();head('Failure analysis and diagnostics')
    sub('6. A state-accessor issue in the released code')
    para('When action validation exhausts its three attempts, the policy returns a terminal error step without next_state. EnvChain appends that step. EnvState.env_state reads only the last step and falls back to init_state if next_state is absent. Therefore the returned board can become blank even though earlier trajectory steps contain placements. The primary endpoint retains this released behavior; no fix was applied during the measured run.')
    para('The supplementary endpoint below scans the saved trajectory for the last valid board. It was added after this issue was observed and is explicitly post hoc. It diagnoses sensitivity to state handling; it is not a second intervention or a replacement primary metric.')
    diag=[]
    for cond,label in [('baseline','Original'),('crossing_prompt','Modified')]:
        a=[x for x in audit['trials'] if x['condition']==cond]
        vals=[x['last_valid_word_accuracy'] for x in a]
        diag.append([label,f'{st.mean(vals)*100:.2f} +/- {st.stdev(vals)*100:.2f}',sum(x['state_fallback_jobs'] for x in a),sum(x['invalid_responses'] for x in a)])
    table([['Condition','Last-valid word %','Fallback jobs / 90','Invalid responses']]+diag,[90,160,120,125])
    diagnostic_means={cond:st.mean(x['last_valid_word_accuracy'] for x in audit['trials'] if x['condition']==cond) for cond in ['baseline','crossing_prompt']}
    diagnostic_delta=100*(diagnostic_means['crossing_prompt']-diagnostic_means['baseline'])
    para(f'The last-valid-state difference is {diagnostic_delta:+.2f} percentage points, compared with {delta:+.2f} points for the primary returned-state endpoint. These endpoints answer different questions: output quality returned by the unmodified chain versus the quality of its last valid placement state. The diagnostic does not remove action failures from the primary analysis.','SmallX')
    sub('7. Inspectable examples')
    rows={}
    for path in root.glob('*/trial_*/puzzle_*/result.json'):
        r=json.loads(path.read_text()); rows[(r['condition'],r['trial'],r['index'])]=r
    pairs=[(rows[('crossing_prompt',t,i)]['word_accuracy']-rows[('baseline',t,i)]['word_accuracy'],t,i) for t in range(3) for i in range(30)]
    selected=[max(pairs),min(pairs)]
    for label,(_,t,i) in zip(['Largest observed improvement','Largest observed regression'],selected):
        a=rows[('baseline',t,i)];z=rows[('crossing_prompt',t,i)]
        sub(f'{label}: trial {t+1}, puzzle index {i}')
        para(f'Original: {pct(a["word_accuracy"])}; modified: {pct(z["word_accuracy"])}. Calls: {a["calls"]} versus {z["calls"]}. Raw evidence is in results/baseline/trial_{t}/puzzle_{i:03d}/ and the matching crossing_prompt directory. These cases were selected after the experiment to illustrate variation, not to estimate the treatment effect.')
        grids=[]
        for r in [a,z]: grids.append(r['final_board'].split('Current Board:\n',1)[1].split('\n\n',1)[0])
        table([['Original returned board','Modified returned board'],[grids[0],grids[1]]],[247.5,247.5])
    para('Action validity is not semantic correctness: a five-letter, unfilled-position action may still contradict the clue or overwrite a crossing answer. A prompt can request better behavior without guaranteeing it.','SmallX')
    page();head('Reproduction and evidence integrity')
    sub('8. How to reproduce')
    para('Project repository: <link href="https://github.com/xwsyun/FTEC5660-LiTS-Reproduction" color="#146B72">github.com/xwsyun/FTEC5660-LiTS-Reproduction</link>','SmallX')
    para('From the submitted repository root, use Python 3.12. Keep the API key in an ignored local .env file. The measured artifact can be audited without making API calls; running a new experiment requires API access.')
    commands='''python3.12 -m venv .venv
source .venv/bin/activate
pip install -r reproduction/requirements.txt
python reproduction/checks.py
unzip -n reproduction/results.zip -d reproduction
python reproduction/analyze.py --results reproduction/results
python reproduction/audit.py --results reproduction/results
# Optional new run; real API calls:
python reproduction/run.py --smoke --output reproduction/smoke_new
python reproduction/run.py --output reproduction/results_new'''
    story.append(Preformatted(commands,styles['SmallX']));story.append(Spacer(1,10))
    para('The direct dependency pins are in requirements.txt; the resolved environment is captured in requirements-lock.txt. The public repository packages raw traces in results.zip; extract it once before auditing. run.py records the fixed dataset hash, model settings, prompt intervention and source revision in config.json. Use a new output directory for new trials; existing completed jobs are skipped on resume.')
    table([['Evidence','Purpose'],['PROTOCOL.md / DEBUG_DIARY.md','Pre-run scope and choices; setup difficulties and later diagnostic findings.'],['calls.jsonl / inferencelogger.log','Every successful API prompt/response, generation parameters, timing, and usage. No credentials.'],['trajectory.json / result.json','Environment steps and final returned-state score for every puzzle.'],['summary.json / per_puzzle.csv','Complete-set aggregation and per-puzzle outcomes.'],['audit.json','Independent board-score check, exact prompt reconstruction, response/trajectory alignment, and post-hoc last-valid-state diagnostic.']],[200,295])
    sub('9. Verification and troubleshooting')
    para('Offline tests cover all 156 puzzles: an empty board scores 0, the reference board scores 1, and changing one letter reduces word accuracy to 0.8 because one row and one column become incorrect. A sentinel reference-answer string never enters the rendered prompt. The final audit reconstructs every actual prompt from board observations plus the condition-specific suffix and checks each saved score using an independent row/column comparison.')
    para('Setup required a focused hosted-API environment rather than all optional GPU/database packages. An unused asynchronous AWS dependency caused resolver backtracking and was removed. Eager imports still required IPython and other listed packages. A smoke-run harness bug assumed state.history existed; iterating EnvState fixed it before measured trials. The failed smoke artifacts are excluded from the measured dataset.')
    page();head('Discussion, reflection, and sources')
    sub('10. What was and was not reproduced')
    para('The released chain can be executed end to end: actions depend on changing observations, trajectories are saved, and exact crossword outcomes can be recomputed. This reproduces a concrete multi-step behavior from the authors\' code. It does not validate the original numerical result, the full paper, or the effectiveness of tree search. A different model, an unmatched subset, a later code revision and explicitly chosen decoding/step limits prevent a fair direct numerical comparison with Table 3.')
    para(f'The controlled within-project comparison estimates the effect of one appended prompt block under these settings. Its observed mean change is {delta:+.2f} percentage points in primary word accuracy. The modification also changes prompt length, so input-token overhead is part of the intervention cost. Retry frequency is an outcome, not a controlled equality of total API calls.')
    sub('11. Reflection and limitations')
    para('The most useful reproducibility lesson is to inspect what a saved final state actually means. Successful execution, a fully populated board, and a correct puzzle are different events. The terminal-error fallback demonstrates how state access can affect an evaluation without any change in the model. Reporting both the unchanged endpoint and a labeled diagnostic makes that limitation visible.')
    para('The intervention is only a natural-language preference. It cannot enforce crossing consistency, and confidence is self-assessed. Stronger enforcement or repairing the state accessor would be worthwhile future experiments, but neither is mixed into this prompt-only comparison. The first 30 puzzles are a convenience sample; three repeats measure limited stochastic variability. Hosted model aliases and service behavior may change, and no API seed guarantees exact reruns.')
    para('AI assistance was used for implementation, debugging, analysis scripting and report drafting. The submission owner should review the evidence, adapt the reflection to their own understanding, and present the work personally. The raw evidence and executable checks are supplied so the claims can be inspected rather than accepted from prose alone.','SmallX')
    sub('References')
    para('[1] Xinzhe Li and Yaguang Tao. LiTS: A Modular Framework for LLM Tree Search. arXiv:2603.00631v1, 2026. Table 3. <link href="https://arxiv.org/html/2603.00631v1" color="#146B72">arxiv.org/html/2603.00631v1</link>','SmallX')
    para('[2] Authors\' repository. <link href="https://github.com/xinzhel/lits-llm" color="#146B72">github.com/xinzhel/lits-llm</link>. Revision 25e94d862cb4514c22d9a80a635e392461769df7. Source files: lits/agents/chain/env_chain.py; lits/components/policy/env_grounded.py; lits/structures/env_grounded.py; demos/lits_benchmark/crosswords.py. Apache-2.0 license retained.','SmallX')
    para('[3] DeepSeek API documentation, Thinking Mode. <link href="https://api-docs.deepseek.com/guides/thinking_mode/" color="#146B72">api-docs.deepseek.com/guides/thinking_mode/</link>. Accessed 12 November 2026.','SmallX')
    def footer(canvas,doc):
        canvas.setStrokeColor(colors.black);canvas.line(50,40,545,40)
        canvas.setFont('Helvetica',8);canvas.setFillColor(colors.black)
        canvas.drawString(50,27,'FTEC5660 | LiTS crossword reproduction');canvas.drawRightString(545,27,str(doc.page))
    SimpleDocTemplate(str(out/'FTEC5660_Reproducibility_Report.pdf'),pagesize=(595.28,841.89),rightMargin=50,leftMargin=50,topMargin=45,bottomMargin=54,title='Reproducing LiTS Crossword Chains').build(story,onFirstPage=footer,onLaterPages=footer)
    notes=f'''FTEC5660 Project 2 录制讲稿与操作提示（目标 10-12 分钟，最多 15 分钟）

录制前：用自己的话理解和修改讲稿。展示本次报告和仓库即可，不需要额外幻灯片。
不要展示 .env、API key 或账单页面。用 Zoom 录制自己的讲解和屏幕，完成后检查链接权限。

0:00-1:00 报告第 1 页：选题
我选择复现 LiTS 的 crossword chain。它每次观察当前棋盘、输出一个填词动作，执行后再观察，因此是多步 agent，而不是一次问答。我使用作者的链式控制器、策略、环境和评分代码。

1:00-2:30 报告第 2 页：范围与设置
我复现的是论文 Table 3 中 crossword chain 的行为，不声称精确复现原论文成绩。论文用 Claude 3.5 Sonnet；我用 deepseek-flash。样本固定为前 30 题，两种条件各重复 3 次，总共 180 次。最大 10 步，每次最多 128 个输出 token。原策略保留动作验证和最多 3 次尝试，因此调用数可能超过 10。

2:30-3:30 展示 reproduction/run.py 的 INTERVENTION
唯一实验修改是在原用户提示后追加一段说明：优先考虑已知交叉字母和较有把握的词，避免冲突。两组使用相同模型、同样的预算和环境。DeepSeek thinking 开关是两组共享的兼容修改，不是实验条件差异。

3:30-5:00 报告第 3 页：结果
原提示最终词准确率是 {avg(b,'word_accuracy',100)}%，修改后是 {avg(m,'word_accuracy',100)}%。这里加减号是三个 trial 平均值的样本标准差，不是置信区间。平均差是 {delta:+.2f} 个百分点。
完整 puzzle 准确率分别为 {pct(b['puzzle_accuracy']['mean'])} 和 {pct(m['puzzle_accuracy']['mean'])}。一共用了 {total_calls} 次调用，输入 {total_in} tokens，输出 {total_out} tokens。不要把这些结果和论文当作相同条件下的模型排名。

5:00-7:00 报告第 4 页及 trajectory.json：失败分析
我发现终止错误步骤没有 next_state 时，原来的 EnvState.env_state 会返回初始棋盘。因此主指标保留原代码行为，同时另算轨迹里的最后有效棋盘作为事后诊断。这个诊断不是另一个实验修改，也没有覆盖主结果。再解释报告中的改进和退步例子：它们是事后选出来的示例，平均效果来自全部 180 次运行。

7:00-9:00 终端演示（无需 API key，不产生新 API 费用）
在仓库根目录激活环境，然后依次执行：
unzip -n reproduction/results.zip -d reproduction
python reproduction/checks.py
python reproduction/analyze.py --results reproduction/results
python reproduction/audit.py --results reproduction/results
说明检查涵盖评分、完整性、调用数以及每个实际 prompt 与轨迹状态的一致性。打开一个 calls.jsonl，展示下一次 prompt 含更新的棋盘。避免把 query 中的 ground truth 误称为模型看到的输入。

9:00-10:30 报告第 6 页：反思
运行成功不代表答案正确；填满棋盘也不代表正确。复现时要核对最后状态、重试规则、模型模式和评分对象。这个实验只测试提示词偏好，不能强制保证交叉一致。固定前 30 题和 3 次重复也不能支持泛化或显著性结论。
说明 AI 工具用于代码、分析和报告辅助；自己需要理解并解释过程，不要声称未使用辅助工具。

提交三件套：
1. 这份英文报告 PDF（不得超过 10 页）。
2. 自己的 GitHub 仓库链接（保留 README、代码、结果和提交记录）。
3. 自己录制的 Zoom 视频链接（不超过 15 分钟，检查老师能访问）。
Blackboard 截止：2026-11-13 23:59 香港时间。录制完成前不要把材料误当成已提交。
'''
    (out/'recording_notes_zh.txt').write_text(notes)
    print(json.dumps({'pdf':str(out/'FTEC5660_Reproducibility_Report.pdf'),'notes':str(out/'recording_notes_zh.txt'),'word_delta_pp':delta}))

if __name__=='__main__': main()
