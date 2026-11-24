
"""
TriageSafe-MH M4: Extended stratified family-cluster bootstrap.

Preserves matched scenario families, severity tiers,
subject models, and independent judges.

All performance estimates are judge-derived.
"""

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import cohen_kappa_score

from src.metrics import add_item_metrics, summarize_records


ROOT = Path(__file__).resolve().parents[1]

TABLES = ROOT / "results" / "tables"

MODELS = ["qwen3_4b", "qwen3_8b"]
JUDGES = ["phi", "mistral"]
TIERS = ["T1", "T2", "T3", "T4", "T5"]
LABELS = list(range(5))

METRICS = [
    "band_accuracy",
    "under_rate",
    "over_rate",
    "mean_see",
    "mean_escalation",
    "cue_accuracy_gap",
    "cue_shift_effect",
]


def load_data():
    """Load and validate the paired judgment dataset."""

    df = pd.read_csv(
        TABLES / "m4_paired_judgments.csv"
    )

    assert len(df) == 80
    assert df["family_id"].nunique() == 20
    assert set(df["model"]) == set(MODELS)
    assert set(df["tier"]) == set(TIERS)

    assert not df.duplicated(
        ["model", "item_id", "subject_seed"]
    ).any()

    for model in MODELS:
        subset = df[df["model"] == model]

        assert len(subset) == 40

        for _, family in subset.groupby("family_id"):
            assert len(family) == 2

            assert set(family["cue_condition"]) == {
                "direct", "cue_shifted"
            }

            assert family["tier"].nunique() == 1

    for _, family in df.groupby("family_id"):
        assert len(family) == 4
        assert family["tier"].nunique() == 1
        assert family["item_id"].nunique() == 2

    # Confirm matching scenario metadata across models.
    metadata = [
        "item_id",
        "family_id",
        "tier",
        "cue_condition",
        "subject_seed",
    ]

    first = df[df["model"] == MODELS[0]][metadata]
    second = df[df["model"] == MODELS[1]][metadata]

    assert first.sort_values("item_id").reset_index(
        drop=True
    ).equals(
        second.sort_values("item_id").reset_index(
            drop=True
        )
    )

    for judge in JUDGES:
        assert df[f"{judge}_score"].isin(LABELS).all()

    return df


def prepare_arrays(df):
    """Precompute metrics for each matched family."""

    family_ids = sorted(df["family_id"].unique())

    family_tiers = (
        df.groupby("family_id")["tier"]
        .first()
        .reindex(family_ids)
        .to_numpy()
    )

    # Dimensions:
    # family x model x judge x metric
    values = np.zeros(
        (len(family_ids), 2, 2, len(METRICS))
    )

    # family x model x wording condition x judge
    ratings = np.zeros(
        (len(family_ids), 2, 2, 2),
        dtype=int,
    )

    for f, family_id in enumerate(family_ids):

        for m, model in enumerate(MODELS):

            subset = df[
                (df["family_id"] == family_id)
                & (df["model"] == model)
            ]

            for j, judge in enumerate(JUDGES):

                records = subset.to_dict("records")

                for record in records:
                    record["escalation_level"] = record[
                        f"escalation_level_{judge}"
                    ]

                # Reuse the project's canonical metrics.
                enriched = add_item_metrics(records)
                summary = summarize_records(enriched)

                by_cue = {
                    r["cue_condition"]: r
                    for r in enriched
                }

                direct = summarize_records(
                    [by_cue["direct"]]
                )

                shifted = summarize_records(
                    [by_cue["cue_shifted"]]
                )

                # Positive gap means direct wording
                # achieves higher band accuracy.
                cue_gap = (
                    direct["band_accuracy"]
                    - shifted["band_accuracy"]
                )

                # Preserve the original definition:
                # shifted escalation minus direct escalation.
                cue_shift = (
                    by_cue["cue_shifted"]["escalation_numeric"]
                    - by_cue["direct"]["escalation_numeric"]
                )

                values[f, m, j] = [
                    summary["band_accuracy"],
                    summary["under_rate"],
                    summary["over_rate"],
                    summary["mean_see"],
                    summary["mean_escalation"],
                    cue_gap,
                    cue_shift,
                ]

                for c, cue in enumerate(
                    ["direct", "cue_shifted"]
                ):
                    ratings[f, m, c, j] = int(
                        by_cue[cue]["escalation_numeric"]
                    )

    return family_tiers, values, ratings


def calculate_statistics(values, ratings, indices):
    """Calculate metrics for one matched bootstrap sample."""

    selected = values[indices]
    averages = selected.mean(axis=0)

    stats = {}

    # Performance by subject model and judge.
    for m, model in enumerate(MODELS):
        for j, judge in enumerate(JUDGES):
            for k, metric in enumerate(METRICS):
                stats[(model, judge, metric)] = (
                    averages[m, j, k]
                )

    # Paired model differences: 8B minus 4B.
    for j, judge in enumerate(JUDGES):
        for k, metric in enumerate(METRICS):
            stats[
                ("8b_minus_4b", judge, metric)
            ] = (
                averages[1, j, k]
                - averages[0, j, k]
            )

    # Paired judge differences: Mistral minus Phi.
    for m, model in enumerate(MODELS):
        for k, metric in enumerate(METRICS):
            stats[
                (model, "mistral_minus_phi", metric)
            ] = (
                averages[m, 1, k]
                - averages[m, 0, k]
            )

    # Inter-judge agreement.
    sampled_ratings = ratings[indices]

    groups = [
        (model, sampled_ratings[:, m])
        for m, model in enumerate(MODELS)
    ]

    groups.append(("combined", sampled_ratings))

    for name, group in groups:

        phi = group[..., 0].reshape(-1)
        mistral = group[..., 1].reshape(-1)

        stats[(name, "agreement", "exact_agreement")] = (
            np.mean(phi == mistral)
        )

        stats[
            (name, "agreement", "linear_weighted_kappa")
        ] = cohen_kappa_score(
            phi,
            mistral,
            labels=LABELS,
            weights="linear",
        )

        stats[
            (name, "agreement", "quadratic_weighted_kappa")
        ] = cohen_kappa_score(
            phi,
            mistral,
            labels=LABELS,
            weights="quadratic",
        )

    return stats


def run(replicates=10000, seed=2026):

    if replicates < 100:
        raise ValueError(
            "Use at least 100 bootstrap replicates."
        )

    df = load_data()

    tiers, values, ratings = prepare_arrays(df)

    n_families = len(tiers)

    tier_indices = {
        tier: np.flatnonzero(tiers == tier)
        for tier in TIERS
    }

    for tier, indices in tier_indices.items():
        assert len(indices) == 4, (
            f"{tier} does not contain four families"
        )

    # Point estimates from the original sample.
    estimates = calculate_statistics(
        values,
        ratings,
        np.arange(n_families),
    )

    keys = list(estimates)

    distributions = np.zeros(
        (replicates, len(keys))
    )

    rng = np.random.default_rng(seed)

    print("Starting extended bootstrap...")
    print(f"Families: {n_families}")
    print(f"Replicates: {replicates}")
    print(f"Seed: {seed}")

    for b in range(replicates):

        # Sample families within each severity tier.
        # The same draw is used for every model and judge.
        selected = np.concatenate([
            rng.choice(
                indices,
                size=len(indices),
                replace=True,
            )
            for indices in tier_indices.values()
        ])

        stats = calculate_statistics(
            values,
            ratings,
            selected,
        )

        distributions[b] = [
            stats[key] for key in keys
        ]

        if (b + 1) % 1000 == 0:
            print(f"Completed {b + 1}/{replicates}")

    rows = []

    for k, key in enumerate(keys):

        group, judge, metric = key

        samples = distributions[:, k]
        valid = samples[np.isfinite(samples)]

        if len(valid):
            lower, upper = np.percentile(
                valid, [2.5, 97.5]
            )
        else:
            lower, upper = np.nan, np.nan

        rows.append({
            "group": group,
            "judge": judge,
            "metric": metric,
            "estimate": estimates[key],
            "ci_lower": lower,
            "ci_upper": upper,
            "bootstrap_replicates": replicates,
            "valid_replicates": len(valid),
            "seed": seed,
            "n_families": n_families,
            "resampling_unit": "matched_family",
            "stratification": "severity_tier",
        })

    results = pd.DataFrame(rows)

    output = TABLES / "m4_extended_bootstrap.csv"

    results.to_csv(output, index=False)

    display_columns = [
        "group",
        "judge",
        "metric",
        "estimate",
        "ci_lower",
        "ci_upper",
    ]

    print("\nBAND ACCURACY CONFIDENCE INTERVALS")

    print(
        results[
            results["metric"] == "band_accuracy"
        ][display_columns].round(4).to_string(
            index=False
        )
    )

    print("\nCUE-CONDITION ACCURACY GAPS")

    print(
        results[
            (results["metric"] == "cue_accuracy_gap")
            & results["group"].isin(MODELS)
            & results["judge"].isin(JUDGES)
        ][display_columns].round(4).to_string(
            index=False
        )
    )

    print("\nINTER-JUDGE AGREEMENT CONFIDENCE INTERVALS")

    print(
        results[
            results["judge"] == "agreement"
        ][display_columns].round(4).to_string(
            index=False
        )
    )

    print(f"\nSaved {len(results)} estimates to:")
    print(output)


def main():

    parser = argparse.ArgumentParser(
        description=__doc__
    )

    parser.add_argument(
        "--replicates",
        type=int,
        default=10000,
    )

    parser.add_argument(
        "--seed",
        type=int,
        default=2026,
    )

    args = parser.parse_args()

    run(args.replicates, args.seed)


if __name__ == "__main__":
    main()
