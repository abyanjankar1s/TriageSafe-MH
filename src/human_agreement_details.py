"""Generate supplementary human agreement statistics."""

from pathlib import Path
from itertools import combinations

import pandas as pd
from sklearn.metrics import cohen_kappa_score, confusion_matrix

INPUT = Path(
    "data/human_validation/completed/m4_human_reference.csv"
)
OUTPUT = Path("results/tables")

LEVELS = ["E0", "E1", "E2", "E3", "E4"]

COLUMNS = {
    "rater_a": "human_escalation_level_a",
    "rater_b": "human_escalation_level_b",
    "phi": "escalation_level_phi",
    "mistral": "escalation_level_mistral",
    "reference": "reference",
}


def main():
    df = pd.read_csv(INPUT)
    OUTPUT.mkdir(parents=True, exist_ok=True)

    assert len(df) == 80
    assert df.annotation_id.is_unique

    summaries = []
    matrices = []

    for first, second in combinations(COLUMNS, 2):
        a = df[COLUMNS[first]]
        b = df[COLUMNS[second]]

        assert a.isin(LEVELS).all()
        assert b.isin(LEVELS).all()

        summaries.append({
            "first": first,
            "second": second,
            "n": len(df),
            "exact_agreement": (a == b).mean(),
            "unweighted_kappa": cohen_kappa_score(
                a, b, labels=LEVELS
            ),
            "linear_weighted_kappa": cohen_kappa_score(
                a, b, labels=LEVELS, weights="linear"
            ),
            "quadratic_weighted_kappa": cohen_kappa_score(
                a, b, labels=LEVELS, weights="quadratic"
            ),
        })

        matrix = confusion_matrix(a, b, labels=LEVELS)

        for i, row_level in enumerate(LEVELS):
            for j, column_level in enumerate(LEVELS):
                matrices.append({
                    "first": first,
                    "second": second,
                    "first_level": row_level,
                    "second_level": column_level,
                    "count": matrix[i, j],
                })

    summary = pd.DataFrame(summaries)

    summary.to_csv(
        OUTPUT / "m4_human_agreement_details.csv",
        index=False,
    )

    pd.DataFrame(matrices).to_csv(
        OUTPUT / "m4_human_confusion_matrices.csv",
        index=False,
    )

    print(summary.to_string(index=False))
    print("\nSupplementary agreement analysis completed.")


if __name__ == "__main__":
    main()
