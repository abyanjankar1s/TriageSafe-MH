"""Paired stratified family bootstrap for human-reference performance."""
from pathlib import Path
import numpy as np
import pandas as pd
from src.human_validation import BANDS, LEVELS, load


def score(see):
    return np.array([(see == 0).mean(), (see < 0).mean(), (see > 0).mean(), see.mean()])


def bootstrap(d, replicates=10000, seed=2026):
    d = d.reset_index(drop=True)
    models = d.model.to_numpy()
    names = ['qwen3_4b', 'qwen3_8b']
    assert set(models) == set(names)
    x = d.reference.map(LEVELS).to_numpy()
    lo = d.tier.map(lambda t: BANDS[t][0]).to_numpy()
    hi = d.tier.map(lambda t: BANDS[t][1]).to_numpy()
    see = np.minimum(x-lo, 0) + np.maximum(x-hi, 0)
    strata = [[g.index.to_numpy() for _, g in t.groupby('family_id')] for _, t in d.groupby('tier')]
    def evaluate(ix):
        a, b = [score(see[ix][models[ix] == m]) for m in names]
        return np.stack([a,b,b-a])
    point = evaluate(np.arange(len(d)))
    rng = np.random.default_rng(seed)
    samples = np.array([evaluate(np.concatenate([s[i] for s in strata for i in rng.integers(0,len(s),len(s))])) for _ in range(replicates)])
    lower, upper = np.percentile(samples,[2.5,97.5],axis=0)
    return pd.DataFrame([dict(comparison=n,metric=k,estimate=point[i,j],ci_lower=lower[i,j],ci_upper=upper[i,j],replicates=replicates,seed=seed) for i,n in enumerate(names+['8b_minus_4b']) for j,k in enumerate(['band_accuracy','under_rate','over_rate','mean_see'])])


if __name__ == '__main__':
    d = load(Path('data/human_validation/completed'),Path('results/tables/m4_paired_judgments.csv'),Path('results/raw'))
    result = bootstrap(d)
    result.to_csv('results/tables/m4_human_performance_bootstrap.csv',index=False)
    print(result.to_string(index=False))
