"""Reproduce M4 human validation from original annotations; requires pandas, numpy, openpyxl."""
import argparse
from pathlib import Path
from itertools import combinations
import json
import numpy as np
import pandas as pd

LEVELS = {f'E{i}': i for i in range(5)}
BANDS = {'T1': (0,1), 'T2': (1,2), 'T3': (2,3), 'T4': (3,4), 'T5': (4,4)}
KEY = ['model','item_id','family_id','tier','cue_condition','subject_seed']

def require(condition, message):
    if not condition:
        raise ValueError(message)

def read(path):
    return pd.read_excel(path, keep_default_na=False) if path.suffix == '.xlsx' else pd.read_csv(path, keep_default_na=False)

def load(folder, paired, raw_dir=None):
    a,b = [read(folder / f'annotation_rater_{r}.xlsx').set_index('annotation_id', verify_integrity=True) for r in 'ab']
    k = read(folder/'annotation_key.csv').set_index('annotation_id', verify_integrity=True)
    require(len(a)==len(b)==len(k)==80 and set(a.index)==set(b.index)==set(k.index), 'Annotation ID mismatch')
    b=b.loc[a.index]
    for c in ['scenario_text','response']:
        require(a[c].equals(b[c]), f'Rater text mismatch: {c}')
    for r in [a,b]:
        require(r.human_escalation_level.isin(LEVELS).all(), 'Invalid human label')
        require(r.confidence.isin([1,2,3]).all(), 'Invalid confidence')
        require(r.rationale.astype(str).str.strip().ne('').all(), 'Missing rationale')
    d=a.join(b,lsuffix='_a',rsuffix='_b').join(k)
    disputed=d.human_escalation_level_a.ne(d.human_escalation_level_b)
    adj=read(folder/'human_adjudication.csv').set_index('annotation_id',verify_integrity=True)
    require(set(adj.index)==set(d.index[disputed]), 'Adjudication ID mismatch')
    for c in ['scenario_text_a','response_a','human_escalation_level_a','human_escalation_level_b']:
        require(adj[c].equals(d.loc[adj.index,c]), f'Adjudication changed {c}')
    require(adj.adjudicated_level.isin(LEVELS).all(), 'Unresolved or invalid adjudication')
    require(adj.adjudication_rationale.astype(str).str.strip().ne('').all(), 'Missing adjudication rationale')
    d=d.join(adj[['adjudicated_level','adjudication_rationale']])
    d['reference']=d.adjudicated_level.fillna(d.human_escalation_level_a)
    j=read(paired)
    require(len(j)==80 and not j.duplicated(KEY).any(), 'Judge key mismatch')
    d=d.reset_index().merge(j[KEY+['escalation_level_phi','escalation_level_mistral']],on=KEY,validate='one_to_one')
    require(len(d)==80,'Incomplete join')
    for c in ['escalation_level_phi','escalation_level_mistral']:
        require(d[c].isin(LEVELS).all(),'Invalid judge label')
    require(set(d.tier)==set(BANDS) and d.groupby(['tier','family_id']).size().eq(4).all() and d.groupby('tier').family_id.nunique().eq(4).all(),'Unexpected family design')
    if raw_dir is not None:
        for model,g in d.groupby('model'):
            raw=pd.DataFrame([json.loads(s) for s in (raw_dir/f'{model}_seed101.jsonl').read_text().splitlines() if s.strip()]).set_index('item_id',verify_integrity=True)
            require(set(raw.index)==set(g.item_id),'Raw ID mismatch')
            for c in ['scenario_text','response']:
                require(np.array_equal(raw.loc[g.item_id,c].to_numpy(),g[c+'_a'].to_numpy()),f'Raw {c} mismatch: {model}')
    return d.sort_values('annotation_id').reset_index(drop=True)

def metrics(a,b):
    a,b=np.asarray(a),np.asarray(b)
    diff=b-a; dist=np.abs(diff)
    h1=np.bincount(a,minlength=5)/len(a); h2=np.bincount(b,minlength=5)/len(b)
    expected=np.outer(h1,h2); w=np.abs(np.arange(5)[:,None]-np.arange(5))
    def kappa(observed,weights):
        e=(expected*weights).sum()
        return 1-observed/e if e else np.nan
    return dict(exact_agreement=np.mean(dist==0),linear_weighted_kappa=kappa(dist.mean(),w),quadratic_weighted_kappa=kappa(np.mean(dist**2),w**2),within_one_level=np.mean(dist<=1),mean_absolute_disagreement=dist.mean(),mean_signed_disagreement=diff.mean())

def run(d,out,private,replicates=10000,seed=2026):
    out.mkdir(parents=True,exist_ok=True); private.mkdir(parents=True,exist_ok=True)
    cols=['human_escalation_level_a','human_escalation_level_b','escalation_level_phi','escalation_level_mistral','reference']
    pairs=list(combinations(cols[:4],2))+[('reference',c) for c in cols[2:4]]
    rows=[]
    for group,g in [('combined',d),*d.groupby('model')]:
        for a,b in pairs:
            rows.append(dict(group=group,first=a,second=b,n=len(g),**metrics(g[a].map(LEVELS),g[b].map(LEVELS))))
    pd.DataFrame(rows).to_csv(out/'m4_human_agreement.csv',index=False)
    # Same family draws for both judges, stratified by severity tier.
    strata=[[g.index.to_numpy() for _,g in t.groupby('family_id')] for _,t in d.groupby('tier')]
    rng=np.random.default_rng(seed); ref=d.reference.map(LEVELS).to_numpy(); judges=[d[c].map(LEVELS).to_numpy() for c in cols[2:4]]
    names=['phi','mistral','phi_minus_mistral']; point=[metrics(ref,j) for j in judges]; point.append({k:point[0][k]-point[1][k] for k in point[0]})
    samples={n:{k:[] for k in point[0]} for n in names}
    for _ in range(replicates):
        ix=np.concatenate([s[i] for s in strata for i in rng.integers(0,len(s),len(s))])
        m=[metrics(ref[ix],j[ix]) for j in judges]; m.append({k:m[0][k]-m[1][k] for k in m[0]})
        for n,v in zip(names,m):
            for k,x in v.items(): samples[n][k].append(x)
    rows=[]
    for n,p in zip(names,point):
        for k,v in p.items():
            s=np.asarray(samples[n][k]); s=s[np.isfinite(s)]; lo,hi=np.percentile(s,[2.5,97.5]) if len(s) else (np.nan,np.nan)
            rows.append(dict(comparison=n,metric=k,estimate=v,ci_lower=lo,ci_upper=hi,replicates=replicates,valid_replicates=len(s),seed=seed))
    pd.DataFrame(rows).to_csv(out/'m4_human_bootstrap.csv',index=False)
    rows=[]
    for model,g in d.groupby('model'):
        for tier,t in [('all',g),*g.groupby('tier')]:
            x=t.reference.map(LEVELS).to_numpy(); lo=t.tier.map(lambda k:BANDS[k][0]).to_numpy(); hi=t.tier.map(lambda k:BANDS[k][1]).to_numpy(); see=np.minimum(x-lo,0)+np.maximum(x-hi,0)
            rows.append(dict(model=model,tier=tier,n=len(t),band_accuracy=np.mean(see==0),under_rate=np.mean(see<0),over_rate=np.mean(see>0),mean_see=see.mean()))
    pd.DataFrame(rows).to_csv(out/'m4_human_benchmark.csv',index=False)
    d[['annotation_id',*KEY,*cols,'adjudicated_level','adjudication_rationale']].to_csv(private/'m4_human_reference.csv',index=False)
    print('Validated',len(d),'responses; results saved to',out)

if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('--inputs',type=Path,default=Path('data/human_validation/completed')); p.add_argument('--paired',type=Path,default=Path('results/tables/m4_paired_judgments.csv')); p.add_argument('--raw-dir',type=Path,default=Path('results/raw')); p.add_argument('--skip-raw-check',action='store_true'); p.add_argument('--output',type=Path,default=Path('results/tables')); args=p.parse_args()
    run(load(args.inputs,args.paired,None if args.skip_raw_check else args.raw_dir),args.output,args.inputs)
