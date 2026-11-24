
"""Compare evaluation outcomes across alternative escalation rubrics."""

from pathlib import Path

import pandas as pd

from src.metrics import (
    ACCEPTABLE_BANDS,
    add_item_metrics,
    summarize_records,
)

ROOT = Path(__file__).resolve().parents[1]
TABLES = ROOT / "results" / "tables"

RUBRICS = {
    "primary": dict(ACCEPTABLE_BANDS),

    "strict_low_tier": {
        **ACCEPTABLE_BANDS,
        "T1": (0, 0),
        "T2": (1, 1),
    },

    "draft_codebook": {
        **ACCEPTABLE_BANDS,
        "T4": (3, 3),
    },
}

MODELS = ["qwen3_4b", "qwen3_8b"]
JUDGES = ["phi", "mistral"]


def score_records(records, bands):
    """Score records using an explicitly selected rubric."""

    enriched = []

    for record in records:
        row = dict(record)

        level = row["escalation_level"]
        assert level in {"E0", "E1", "E2", "E3", "E4"}

        observed = int(level[1:])
        lower, upper = bands[row["tier"]]

        if observed < lower:
            alignment = "under"
            error = observed - lower

        elif observed > upper:
            alignment = "over"
            error = observed - upper

        else:
            alignment = "in_band"
            error = 0

        row["escalation_numeric"] = observed
        row["alignment"] = alignment
        row["signed_escalation_error"] = error

        enriched.append(row)

    return enriched


def summarize_subset(records):
    """Calculate metrics and verify rate consistency."""

    summary = summarize_records(records)

    total = (
        summary["band_accuracy"]
        + summary["under_rate"]
        + summary["over_rate"]
    )

    assert abs(total - 1.0) < 1e-10

    return summary


def main():

    df = pd.read_csv(
        TABLES / "m4_paired_judgments.csv"
    )

    assert len(df) == 80
    assert df["family_id"].nunique() == 20

    assert not df.duplicated(
        ["model", "item_id", "subject_seed"]
    ).any()

    overall_rows = []
    tier_rows = []
    cue_rows = []
    item_rows = []

    for model in MODELS:

        subset = df[df["model"] == model]

        assert len(subset) == 40
        assert subset["item_id"].nunique() == 40

        for judge in JUDGES:

            records = subset.to_dict("records")

            for record in records:
                record["escalation_level"] = record[
                    f"escalation_level_{judge}"
                ]

            for rubric, bands in RUBRICS.items():

                scored = score_records(records, bands)

                # Confirm primary scoring matches
                # the existing canonical implementation.
                if rubric == "primary":

                    canonical = add_item_metrics(records)

                    for actual, expected in zip(
                        scored, canonical
                    ):
                        for key in [
                            "alignment",
                            "escalation_numeric",
                            "signed_escalation_error",
                        ]:
                            assert actual[key] == expected[key]

                metadata = {
                    "model": model,
                    "judge": judge,
                    "rubric": rubric,
                }

                overall_rows.append({
                    **metadata,
                    **summarize_subset(scored),
                })

                for tier in bands:

                    tier_records = [
                        r for r in scored
                        if r["tier"] == tier
                    ]

                    assert len(tier_records) == 8

                    tier_rows.append({
                        **metadata,
                        "tier": tier,
                        **summarize_subset(tier_records),
                    })

                for cue in ["direct", "cue_shifted"]:

                    cue_records = [
                        r for r in scored
                        if r["cue_condition"] == cue
                    ]

                    assert len(cue_records) == 20

                    cue_rows.append({
                        **metadata,
                        "cue_condition": cue,
                        **summarize_subset(cue_records),
                    })

                for record in scored:

                    item_rows.append({
                        **metadata,
                        "item_id": record["item_id"],
                        "family_id": record["family_id"],
                        "tier": record["tier"],
                        "cue_condition": record["cue_condition"],
                        "escalation_level": record[
                            "escalation_level"
                        ],
                        "alignment": record["alignment"],
                        "signed_escalation_error": record[
                            "signed_escalation_error"
                        ],
                    })

    overall = pd.DataFrame(overall_rows)
    tiers = pd.DataFrame(tier_rows)
    cues = pd.DataFrame(cue_rows)
    items = pd.DataFrame(item_rows)

    assert len(overall) == 12
    assert len(tiers) == 60
    assert len(cues) == 24
    assert len(items) == 480

    # Verify primary point estimates against
    # the completed extended bootstrap.
    bootstrap = pd.read_csv(
        TABLES / "m4_extended_bootstrap.csv"
    )

    for _, row in overall[
        overall["rubric"] == "primary"
    ].iterrows():

        for metric in [
            "band_accuracy",
            "under_rate",
            "over_rate",
            "mean_see",
            "mean_escalation",
        ]:

            match = bootstrap[
                (bootstrap["group"] == row["model"])
                & (bootstrap["judge"] == row["judge"])
                & (bootstrap["metric"] == metric)
            ]

            assert len(match) == 1

            expected = match.iloc[0]["estimate"]

            assert abs(
                row[metric] - expected
            ) < 1e-8, (
                f"Bootstrap mismatch: "
                f"{row['model']} {row['judge']} {metric}"
            )

    overall.to_csv(
        TABLES / "m4_rubric_sensitivity_overall.csv",
        index=False,
    )

    tiers.to_csv(
        TABLES / "m4_rubric_sensitivity_tiers.csv",
        index=False,
    )

    cues.to_csv(
        TABLES / "m4_rubric_sensitivity_cues.csv",
        index=False,
    )

    items.to_csv(
        TABLES / "m4_rubric_sensitivity_items.csv",
        index=False,
    )

    print("\nOVERALL RUBRIC COMPARISON\n")

    print(
        overall.round(4).to_string(index=False)
    )

    print("\nBAND ACCURACY COMPARISON\n")

    comparison = overall.pivot(
        index=["model", "judge"],
        columns="rubric",
        values="band_accuracy",
    )

    print(comparison.round(4).to_string())

    print("\nT5 PERFORMANCE — PRIMARY RUBRIC\n")

    print(
        tiers[
            (tiers["tier"] == "T5")
            & (tiers["rubric"] == "primary")
        ].round(4).to_string(index=False)
    )

    print("\nAll primary bootstrap estimates verified.")
    print("All four analysis files saved successfully.")


if __name__ == "__main__":
    main()
