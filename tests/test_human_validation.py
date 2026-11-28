import numpy as np
import pandas as pd
import pytest
from sklearn.metrics import cohen_kappa_score
from src.human_validation import metrics, require, BANDS
from src.human_performance import bootstrap, score


def test_perfect_agreement():
    m = metrics([0,1,2,3,4],[0,1,2,3,4])
    assert m['linear_weighted_kappa'] == m['quadratic_weighted_kappa'] == 1
    assert m['exact_agreement'] == 1

@pytest.mark.parametrize('weight',['linear','quadratic'])
def test_kappa_matches_sklearn(weight):
    a,b = [0,1,2,3,4,2],[1,1,3,2,4,0]
    assert metrics(a,b)[weight+'_weighted_kappa'] == pytest.approx(cohen_kappa_score(a,b,labels=list(range(5)),weights=weight))


def test_signed_direction():
    assert metrics([1,2],[2,3])['mean_signed_disagreement'] == 1
    assert metrics([2,3],[1,2])['mean_signed_disagreement'] == -1


def test_undefined_kappa():
    assert np.isnan(metrics([1,1],[1,1])['linear_weighted_kappa'])


def test_validation_guard():
    with pytest.raises(ValueError,match='Invalid human label'):
        require(False,'Invalid human label')


def test_score():
    np.testing.assert_allclose(score(np.array([-2,0,0,1])),[.5,.25,.25,-.25])


def test_paired_bootstrap():
    d = pd.DataFrame([dict(tier=t,family_id=f'{t}_{f}',model=m,reference=f'E{BANDS[t][0]}') for t in BANDS for f in range(4) for m in ['qwen3_4b','qwen3_8b'] for _ in range(2)])
    a = bootstrap(d,replicates=20)
    pd.testing.assert_frame_equal(a,bootstrap(d,replicates=20))
    assert (a.loc[a.comparison=='8b_minus_4b',['estimate','ci_lower','ci_upper']]==0).all().all()
