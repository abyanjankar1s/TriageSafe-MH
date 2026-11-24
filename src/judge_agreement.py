
"""
TriageSafe-MH: Inter-judge agreement analysis.

Compares independent Phi and Mistral escalation
judgments for identical subject-model responses.
"""

from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import (
    cohen_kappa_score,
    confusion_matrix,
)

ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "results" / "processed"
TABLES = ROOT / "results" / "tables"

TABLES.mkdir(parents=True, exist_ok=True)

MODELS = ["qwen3_4b", "qwen3_8b"]

LABELS = ["E0", "E1", "E2", "E3", "E4"]

LABEL_MAP = {
    label: index
    for index, label in enumerate(LABELS)
}


def load_paired_judgments(model):
    """Match both judges on identical response IDs."""

    phi = pd.read_json(
        PROCESSED / f"{model}_phi35_seed101.jsonl",
        lines=True,
    )

    mistral = pd.read_json(
        PROCESSED / f"{model}_mistral_complete_seed101.jsonl",
        lines=True,
    )

    # Validate input records before merging.
    assert len(phi) == len(mistral) == 40
    assert phi["item_id"].is_unique
    assert mistral["item_id"].is_unique
    assert set(phi["item_id"]) == set(mistral["item_id"])

    assert phi["escalation_level"].isin(LABELS).all()
    assert mistral["escalation_level"].isin(LABELS).all()

    paired = phi[
        [
            "item_id",
            "family_id",
            "tier",
            "cue_condition",
            "subject_seed",
            "escalation_level",
        ]
    ].merge(
        mistral[
            [
                "item_id",
                "family_id",
                "tier",
                "cue_condition",
                "subject_seed",
                "escalation_level",
                "recovery_run",
            ]
        ],
        on=[
            "item_id",
            "family_id",
            "tier",
            "cue_condition",
            "subject_seed",
        ],
        suffixes=("_phi", "_mistral"),
        validate="one_to_one",
    )

    assert len(paired) == 40

    paired["model"] = model

    # Convert ordinal escalation labels to integers.
    paired["phi_score"] = paired[
        "escalation_level_phi"
    ].map(LABEL_MAP)

    paired["mistral_score"] = paired[
        "escalation_level_mistral"
    ].map(LABEL_MAP)

    # Positive difference means Phi assigns higher escalation.
    paired["difference"] = (
        paired["phi_score"] - paired["mistral_score"]
    )

    paired["absolute_difference"] = (
        paired["difference"].abs()
    )

    paired["exact_agreement"] = (
        paired["difference"] == 0
    )

    return paired


def calculate_agreement(df, name):
    """Calculate ordinal inter-judge agreement metrics."""

    phi = df["phi_score"]
    mistral = df["mistral_score"]

    return {
        "group": name,
        "n": len(df),

        "exact_agreement": (
            df["exact_agreement"].mean()
        ),

        "unweighted_kappa": cohen_kappa_score(
            phi, mistral, labels=list(range(5))
        ),

        "linear_weighted_kappa": cohen_kappa_score(
            phi,
            mistral,
            labels=list(range(5)),
            weights="linear",
        ),

        "quadratic_weighted_kappa": cohen_kappa_score(
            phi,
            mistral,
            labels=list(range(5)),
            weights="quadratic",
        ),

        "mean_absolute_disagreement": (
            df["absolute_difference"].mean()
        ),

        "mean_signed_disagreement": (
            df["difference"].mean()
        ),

        "within_one_level": (
            df["absolute_difference"] <= 1
        ).mean(),

        "phi_higher": (
            df["difference"] > 0
        ).mean(),

        "mistral_higher": (
            df["difference"] < 0
        ).mean(),

        "large_disagreement": (
            df["absolute_difference"] >= 2
        ).mean(),
    }


def main():
    # Pair judgments separately for each subject model.
    paired = pd.concat(
        [
            load_paired_judgments(model)
            for model in MODELS
        ],
        ignore_index=True,
    )

    assert len(paired) == 80

    results = []

    for model, group in paired.groupby("model"):
        results.append(
            calculate_agreement(group, model)
        )

    # Combined descriptive agreement.
    results.append(
        calculate_agreement(paired, "combined")
    )

    summary = pd.DataFrame(results)

    print("\nINTER-JUDGE AGREEMENT")
    print("=" * 70)
    print(summary.round(4).to_string(index=False))

    summary.to_csv(
        TABLES / "m4_interjudge_agreement.csv",
        index=False,
    )

    paired.to_csv(
        TABLES / "m4_paired_judgments.csv",
        index=False,
    )

    # Generate combined disagreement matrix.
    matrix = confusion_matrix(
        paired["phi_score"],
        paired["mistral_score"],
        labels=list(range(5)),
    )

    matrix_df = pd.DataFrame(
        matrix,
        index=LABELS,
        columns=LABELS,
    )

    matrix_df.index.name = "Phi"
    matrix_df.columns.name = "Mistral"

    print("\nJUDGE DISAGREEMENT MATRIX")
    print("Rows: Phi | Columns: Mistral")
    print(matrix_df)

    matrix_df.to_csv(
        TABLES / "m4_judge_disagreement_matrix.csv"
    )

    # Save all disagreements for later human annotation.
    disagreements = paired[
        ~paired["exact_agreement"]
    ].sort_values(
        "absolute_difference",
        ascending=False,
    )

    disagreements.to_csv(
        TABLES / "m4_judge_disagreements.csv",
        index=False,
    )

    print("\nTotal paired judgments:", len(paired))
    print("Exact matches:", paired["exact_agreement"].sum())
    print("Disagreements:", len(disagreements))
    # Sensitivity analysis excluding repaired judgments.
    complete_cases = paired[
        paired["recovery_run"] == False
    ].copy()

    assert len(complete_cases) == 77

    sensitivity_results = []

    for name, group in [
        ("qwen3_4b", complete_cases[
            complete_cases["model"] == "qwen3_4b"
        ]),
        ("qwen3_8b", complete_cases[
            complete_cases["model"] == "qwen3_8b"
        ]),
        ("combined", complete_cases),
    ]:
        sensitivity_results.append(
            calculate_agreement(group, name)
        )

    sensitivity = pd.DataFrame(sensitivity_results)

    print("\nCOMPLETE-CASE SENSITIVITY ANALYSIS")
    print("=" * 70)
    print(sensitivity.round(4).to_string(index=False))

    sensitivity.to_csv(
        TABLES / "m4_interjudge_sensitivity.csv",
        index=False,
    )
    print("\nAnalysis files saved successfully.")


if __name__ == "__main__":
    main()
