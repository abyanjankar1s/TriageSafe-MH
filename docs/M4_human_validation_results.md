# Milestone 4: Human Validation Results

## 1. Experimental Scope

- 40 synthetic scenarios.
- 20 matched scenario families.
- Five severity tiers.
- Two cue conditions.
- Two subject models.
- 80 generated responses.
- Two automated judges.
- 160 original human annotations.
- 40 adjudicated disagreements.
- 10,000 stratified family-cluster bootstrap replicates.

## 2. Human Rater Assignments

Rater A was the second human annotator.

Rater B was the benchmark developer and graduate
researcher.

The actual assignments differed from the original
planned protocol.

## 3. Human-Human Agreement

| Metric | Result |
|---|---:|
| Exact agreement | 50.00% |
| Unweighted Cohen's kappa | 0.3157 |
| Linear-weighted kappa | 0.4566 |
| Quadratic-weighted kappa | 0.5912 |
| Within one escalation level | 92.50% |
| Mean absolute disagreement | 0.5875 |

The results indicate moderate ordinal agreement,
with meaningful uncertainty in category interpretation.

## 4. Automated Judge Agreement

| Metric | Phi-3.5 | Mistral-7B |
|---|---:|---:|
| Exact agreement with reference | 42.50% | 31.25% |
| Linear-weighted kappa | 0.4688 | 0.4579 |
| Quadratic-weighted kappa | 0.6531 | 0.7004 |
| Within one level | 95.00% | 96.25% |
| Mean absolute disagreement | 0.625 | 0.725 |

Linear-weighted kappa was the primary agreement metric.

The paired difference between judges was 0.0108,
with a 95% bootstrap confidence interval of
-0.0577 to 0.0724.

The results do not establish superiority of either
judge on the primary agreement metric.

## 5. Human-Reference Model Performance

| Metric | Qwen3-4B | Qwen3-8B |
|---|---:|---:|
| Band accuracy | 67.5% | 85.0% |
| Under-escalation | 30.0% | 12.5% |
| Over-escalation | 2.5% | 2.5% |
| Mean signed escalation error | -0.375 | -0.175 |

The paired band accuracy difference was 17.5
percentage points, with a 95% bootstrap confidence
interval of 7.5 to 27.5 percentage points.

## 6. Severity-Tier Performance

| Tier | Qwen3-4B | Qwen3-8B |
|---|---:|---:|
| T1 | 87.5% | 87.5% |
| T2 | 100.0% | 100.0% |
| T3 | 87.5% | 100.0% |
| T4 | 62.5% | 87.5% |
| T5 | 0.0% | 50.0% |

Under the adjudicated reference, the highest-risk
tier remained challenging for both models.

Each model was evaluated on eight scenarios per tier.

## 7. Individual-Rater Sensitivity

| Source | Qwen3-4B | Qwen3-8B | Difference |
|---|---:|---:|---:|
| Rater A | 65.0% | 67.5% | +2.5 pp |
| Rater B | 67.5% | 85.0% | +17.5 pp |
| Adjudicated | 67.5% | 85.0% | +17.5 pp |

Paired 95% bootstrap confidence intervals:

- Rater A: -7.5 to +12.5 percentage points.
- Rater B: +7.5 to +27.5 percentage points.
- Adjudicated: +7.5 to +27.5 percentage points.

Under Rater A, both models had a 30% under-escalation
rate.

Under Rater B and the adjudicated reference, the
larger model reduced observed under-escalation
from 30% to 12.5%.

The direction of the observed accuracy advantage
was consistent, but its magnitude and statistical
certainty depended on evaluator choice.

## 8. Adjudication Limitations

The adjudicated reference matched Rater B on
79 of 80 responses.

Of the 40 disputed responses, 39 were resolved
in favor of Rater B.

Because Rater B developed the benchmark, the
reference may reflect developer-related bias.

Differences in rubric familiarity are a possible
explanation for disagreement but have not been
independently established.

Joint adjudication and blinding during adjudication
have not been independently confirmed.

The reference is an operational benchmark standard,
not clinically validated ground truth.

## 9. Reproducibility

With authorized access to the private annotations:

    python -m src.human_validation
    python -m src.human_performance
    python -m src.human_agreement_details
    python -m src.human_rater_sensitivity

Using the publicly shareable aggregate tables:

    python -m src.plot_m4_results

Individual human annotations and annotation keys
are excluded from the public repository.

## 10. Conclusion

Human validation provides evidence about the
reliability and limitations of automated escalation
classification.

The findings demonstrate that model safety
benchmark conclusions can be sensitive to the
evaluation source.

Neither model nor automated judge is established
as clinically reliable by this experiment.
