"""Generate M4 figures from aggregate CSVs; run from repository root."""
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.ticker import PercentFormatter

T = Path('results/tables')
O = Path('results/figures')
O.mkdir(parents=True, exist_ok=True)
plt.rcParams.update({'font.size': 10, 'axes.spines.top': False, 'axes.spines.right': False, 'pdf.fonttype': 42})
MODELS = ['qwen3_4b', 'qwen3_8b']
NAMES = ['Qwen3-4B', 'Qwen3-8B']
COLORS = ['#64748b', '#087f8c']

def read(name):
    return pd.read_csv(T / ('m4_' + name + '.csv'))

def save(fig, name):
    fig.tight_layout()
    for ext in ['png', 'pdf']:
        fig.savefig(O / f'm4_{name}.{ext}', dpi=300, bbox_inches='tight')
    plt.close(fig)
    print('Saved:', name)

def forest(ax, rows, labels, percent=True, zero=True):
    assert len(rows) == len(labels)
    v = rows.estimate.to_numpy()
    lo = rows.ci_lower.to_numpy()
    hi = rows.ci_upper.to_numpy()
    y = np.arange(len(v))
    ax.hlines(y, lo, hi, color=COLORS[0], linewidth=2)
    ax.scatter(v, y, color=COLORS[1], zorder=3)
    ax.set_yticks(y, labels)
    ax.invert_yaxis()
    if zero: ax.axvline(0, color='gray', linestyle='--', linewidth=1)
    if percent: ax.xaxis.set_major_formatter(PercentFormatter(1))
    ax.grid(axis='x', alpha=.2)

def main():
    baseline = read('baseline_comparison')
    baseline = baseline[baseline.model.str.startswith('Always')]
    assert len(baseline) == 5
    auto = read('rubric_sensitivity_overall').query("rubric == 'primary'")
    assert len(auto) == 4
    labels = baseline.model.tolist() + [f'{m.replace("qwen3_", "Qwen3-").upper()} / {j}' for m,j in zip(auto.model,auto.judge)]
    vals = pd.concat([baseline.band_accuracy,auto.band_accuracy]).to_numpy()
    fig, ax = plt.subplots(figsize=(8,5))
    ax.barh(labels, vals, color=[COLORS[0]]*5+[COLORS[1]]*4)
    ax.invert_yaxis(); ax.set_xlim(0,1); ax.xaxis.set_major_formatter(PercentFormatter(1))
    ax.set_xlabel('Band accuracy'); ax.set_title('Fixed-level baselines vs independent-judge evaluations')
    for i,v in enumerate(vals): ax.text(v+.015,i,f'{v:.1%}',va='center')
    save(fig,'01_baselines')

    human = read('human_benchmark')
    tiers = ['T1','T2','T3','T4','T5']
    fig, ax = plt.subplots(figsize=(8,4.5))
    x = np.arange(5)
    for i,m in enumerate(MODELS):
        v = human[human.model.eq(m)].set_index('tier').loc[tiers,'band_accuracy']
        ax.bar(x+(i-.5)*.35,v,.35,label=NAMES[i],color=COLORS[i])
    ax.set_xticks(x,tiers); ax.set_ylim(0,1.08); ax.yaxis.set_major_formatter(PercentFormatter(1))
    ax.set_ylabel('Band accuracy'); ax.set_title('Adjudicated-reference accuracy by severity (8 responses per bar)'); ax.legend()
    save(fig,'02_severity')

    ext = read('extended_bootstrap')
    cue = ext[
        ext.group.isin(MODELS)
        & ext.judge.isin(['phi', 'mistral'])
        & ext.metric.eq('cue_accuracy_gap')
    ]
    if len(cue)!=4:
        raise ValueError(f'Expected four cue accuracy gap rows; available metrics: {ext.metric.unique()}')
    fig,ax=plt.subplots(figsize=(8,3.8))
    forest(ax,cue,[f'{NAMES[MODELS.index(m)]} / {j}' for m,j in zip(cue.group,cue.judge)])
    ax.set_xlabel('Direct minus cue-shifted accuracy (percentage points)'); ax.set_title('Cue-condition accuracy gaps (95% bootstrap CI)')
    save(fig,'03_cue_effects')

    cm=read('human_confusion_matrices')
    pairs=[('rater_a','rater_b'),('phi','reference'),('mistral','reference'),('phi','mistral')]
    levels=[f'E{i}' for i in range(5)]
    pretty={'rater_a':'Rater A','rater_b':'Rater B','phi':'Phi','mistral':'Mistral','reference':'Adjudicated'}
    fig,axes=plt.subplots(2,2,figsize=(8,8))
    for ax,(a,b) in zip(axes.flat,pairs):
        sub=cm[cm['first'].eq(a)&cm['second'].eq(b)]
        mat=sub.pivot(index='first_level',columns='second_level',values='count').loc[levels,levels].to_numpy()
        assert mat.sum()==80
        ax.imshow(mat,cmap='Blues',vmin=0,vmax=80)
        for i in range(5):
            for j in range(5): ax.text(j,i,str(mat[i,j]),ha='center',va='center',color='black')
        ax.set_xticks(range(5),levels); ax.set_yticks(range(5),levels)
        ax.set_xlabel(pretty[b]); ax.set_ylabel(pretty[a]); ax.set_title(f'{pretty[a]} vs {pretty[b]}')
    save(fig,'04_confusion_matrices')

    boot=read('human_bootstrap')
    k=boot[boot.metric.eq('linear_weighted_kappa')].set_index('comparison').loc[['phi','mistral']].reset_index()
    fig,ax=plt.subplots(figsize=(7,3))
    forest(ax,k,['Phi vs reference','Mistral vs reference'],percent=False)
    ax.set_xlim(0,1); ax.set_xlabel('Linear-weighted Cohen’s kappa'); ax.set_title('Human-reference agreement (95% bootstrap CI)')
    save(fig,'05_judge_reliability')

    perf=read('human_performance_bootstrap')
    metrics=['band_accuracy','under_rate','over_rate']
    fig,ax=plt.subplots(figsize=(8,4.5)); x=np.arange(3)
    for i,m in enumerate(MODELS):
        r=perf[perf.comparison.eq(m)].set_index('metric').loc[metrics]
        pos=x+(i-.5)*.35
        ax.bar(pos,r.estimate,.35,color=COLORS[i],label=NAMES[i])
        ax.errorbar(pos,r.estimate,yerr=[np.maximum(0,r.estimate-r.ci_lower),np.maximum(0,r.ci_upper-r.estimate)],fmt='none',ecolor='black',capsize=3)
    ax.set_xticks(x,['Band accuracy','Under-escalation','Over-escalation']); ax.set_ylim(0,1.05); ax.yaxis.set_major_formatter(PercentFormatter(1)); ax.legend()
    ax.set_title('Adjudicated-reference performance (95% bootstrap CI)')
    save(fig,'06_human_performance')

    sens=read('human_rater_sensitivity_bootstrap')
    r=sens[sens.metric.eq('band_accuracy') & sens.comparison.eq('8b_minus_4b')].set_index('scoring_source').loc[['rater_a','rater_b','adjudicated']].reset_index()
    fig,ax=plt.subplots(figsize=(8,3.5))
    forest(ax,r,['Rater A','Rater B (developer)','Adjudicated reference'])
    ax.set_xlabel('8B minus 4B accuracy (percentage points)'); ax.set_title('Evaluator sensitivity (95% paired bootstrap CI)')
    save(fig,'07_rater_sensitivity')

if __name__=='__main__':
    main()
