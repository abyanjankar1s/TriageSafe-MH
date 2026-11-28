"""Compare benchmark performance across human scoring sources."""

from pathlib import Path

import numpy as np
import pandas as pd

from src.human_validation import BANDS, LEVELS

INPUT = Path(
    "data/human_validation/completed/m4_human_reference.csv"
)

OUTPUT = Path("results/tables")

SOURCES = {
    "rater_a": "human_escalation_level_a",
    "rater_b": "human_escalation_level_b",
    "adjudicated": "reference",
}

REPLICATES = 10000
SEED = 2026


def score(errors):
    return {
        "band_accuracy": np.mean(errors == 0),
        "under_rate": np.mean(errors < 0),
        "over_rate": np.mean(errors > 0),
        "mean_see": np.mean(errors),
    }


def main():
    df = pd.read_csv(INPUT).reset_index(drop=True)

    assert len(df) == 80
    assert df.annotation_id.is_unique

    OUTPUT.mkdir(parents=True, exist_ok=True)

    lower = df.tier.map(lambda t: BANDS[t][0]).to_numpy()
    upper = df.tier.map(lambda t: BANDS[t][1]).to_numpy()

    models = ["qwen3_4b", "qwen3_8b"]
    model_array = df.model.to_numpy()

    errors = {}

    for source, column in SOURCES.items():
        assert df[column].isin(LEVELS).all()

        values = df[column].map(LEVELS).to_numpy()

        errors[source] = (
            np.minimum(values - lower, 0)
            + np.maximum(values - upper, 0)
        )

    rows = []

    for source, values in errors.items():
        for model in models:
            mask = model_array == model

            rows.append({
                "scoring_source": source,
                "model": model,
                "n": int(mask.sum()),
                **score(values[mask]),
            })

    summary = pd.DataFrame(rows)

    summary.to_csv(
        OUTPUT / "m4_human_rater_sensitivity.csv",
        index=False,
    )

    strata = [
        [g.index.to_numpy()
         for _, g in tier.groupby("family_id")]
        for _, tier in df.groupby("tier")
    ]

    rng = np.random.default_rng(SEED)

    samples = {
        source: {
            metric: []
            for metric in score(values)
        }
        for source, values in errors.items()
    }

    for _ in range(REPLICATES):
        ix = np.concatenate([
            families[i]
            for families in strata
            for i in rng.integers(
                0, len(families), len(families)
            )
        ])

        for source, values in errors.items():
            small = score(
                values[ix[model_array[ix] == models[0]]]
            )

            large = score(
                values[ix[model_array[ix] == models[1]]]
            )

            for metric in small:
                samples[source][metric].append(
                    large[metric] - small[metric]
                )

    contrasts = []

    for source, values in errors.items():
        small = score(values[model_array == models[0]])
        large = score(values[model_array == models[1]])

        for metric in small:
            lo, hi = np.percentile(
                samples[source][metric],
                [2.5, 97.5],
            )

            contrasts.append({
                "scoring_source": source,
                "comparison": "8b_minus_4b",
                "metric": metric,
                "estimate": large[metric] - small[metric],
                "ci_lower": lo,
                "ci_upper": hi,
                "replicates": REPLICATES,
                "seed": SEED,
            })

    comparison = pd.DataFrame(contrasts)

    comparison.to_csv(
        OUTPUT / "m4_human_rater_sensitivity_bootstrap.csv",
        index=False,
    )

    print("\nINDIVIDUAL RATER PERFORMANCE\n")
    print(summary.to_string(index=False))

    print("\nPAIRED MODEL COMPARISONS\n")
    print(comparison.to_string(index=False))

    print("\nSensitivity analysis completed.")


if __name__ == "__main__":
    main()
