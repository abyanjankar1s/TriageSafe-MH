"""
Create blinded human-review materials for the TriageSafe-MH
development dataset.

This script:
1. Loads authored scenarios from scenario_texts.csv.
2. Randomizes scenario order using a fixed seed.
3. Assigns anonymous review IDs.
4. Creates a review sheet that contains no intended tier,
   family ID, cue condition, or source information.
5. Creates a private key mapping review IDs back to the
   original benchmark metadata.

IMPORTANT:
- Give blind_review_sheet.csv to human raters.
- Do NOT give blind_review_key.csv to human raters.
"""

import argparse
import csv
import random
from pathlib import Path


DEFAULT_INPUT = Path("data/development/scenario_texts.csv")

DEFAULT_REVIEW_OUTPUT = Path(
    "data/development/blind_review_sheet.csv"
)

DEFAULT_KEY_OUTPUT = Path(
    "data/development/blind_review_key.csv"
)

DEFAULT_SEED = 4242

VALID_TIERS = {"T1", "T2", "T3", "T4", "T5"}


def load_scenarios(path: Path):
    """Load authored scenario rows from CSV."""

    if not path.exists():
        raise FileNotFoundError(f"Scenario file not found: {path}")

    with path.open("r", encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)
        rows = list(reader)

    required_fields = {
        "family_id",
        "item_id",
        "cue_condition",
        "text",
        "source_basis",
        "authoring_notes",
    }

    if reader.fieldnames is None:
        raise ValueError("Input CSV does not contain a header.")

    missing = required_fields - set(reader.fieldnames)

    if missing:
        raise ValueError(
            "Input CSV is missing required fields: "
            + ", ".join(sorted(missing))
        )

    if not rows:
        raise ValueError("No scenarios found in input CSV.")

    return rows


def infer_tier(family_id: str) -> str:
    """
    Infer intended tier from family ID.

    Example:
        T3_F002 -> T3
    """

    tier = family_id.split("_")[0]

    if tier not in VALID_TIERS:
        raise ValueError(
            f"Could not infer valid tier from family_id: {family_id}"
        )

    return tier


def validate_scenarios(rows):
    """Perform basic checks before creating blinded materials."""

    item_ids = set()

    for row in rows:
        item_id = row["item_id"].strip()
        family_id = row["family_id"].strip()
        text = row["text"].strip()

        if not item_id:
            raise ValueError("Found scenario with empty item_id.")

        if item_id in item_ids:
            raise ValueError(f"Duplicate item_id found: {item_id}")

        item_ids.add(item_id)

        if not family_id:
            raise ValueError(
                f"Scenario {item_id} has empty family_id."
            )

        infer_tier(family_id)

        if not text:
            raise ValueError(
                f"Scenario {item_id} has empty text."
            )


def create_blinded_rows(rows, seed: int):
    """
    Randomize scenarios and create:
    1. blinded rater rows
    2. private key rows
    """

    shuffled = [dict(row) for row in rows]

    rng = random.Random(seed)
    rng.shuffle(shuffled)

    review_rows = []
    key_rows = []

    for index, row in enumerate(shuffled, start=1):

        review_id = f"REV_{index:03d}"

        intended_tier = infer_tier(row["family_id"])

        # Public row for human annotation.
        review_rows.append(
            {
                "review_id": review_id,
                "scenario_text": row["text"].strip(),
                "rater_tier": "",
                "lower_escalation": "",
                "upper_escalation": "",
                "comments": "",
            }
        )

        # Private mapping. Never provide this file to raters.
        key_rows.append(
            {
                "review_id": review_id,
                "item_id": row["item_id"].strip(),
                "family_id": row["family_id"].strip(),
                "intended_tier": intended_tier,
                "cue_condition": row["cue_condition"].strip(),
                "source_basis": row["source_basis"].strip(),
            }
        )

    return review_rows, key_rows


def write_csv(path: Path, rows, fieldnames):
    """Write rows to a CSV file."""

    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames,
        )

        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Create randomized blind human-review materials "
            "for TriageSafe-MH."
        )
    )

    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_INPUT,
        help="Path to scenario_texts.csv",
    )

    parser.add_argument(
        "--review-output",
        type=Path,
        default=DEFAULT_REVIEW_OUTPUT,
        help="Output path for blinded review sheet",
    )

    parser.add_argument(
        "--key-output",
        type=Path,
        default=DEFAULT_KEY_OUTPUT,
        help="Output path for private review key",
    )

    parser.add_argument(
        "--seed",
        type=int,
        default=DEFAULT_SEED,
        help="Randomization seed",
    )

    args = parser.parse_args()

    rows = load_scenarios(args.input)

    validate_scenarios(rows)

    review_rows, key_rows = create_blinded_rows(
        rows,
        seed=args.seed,
    )

    review_fields = [
        "review_id",
        "scenario_text",
        "rater_tier",
        "lower_escalation",
        "upper_escalation",
        "comments",
    ]

    key_fields = [
        "review_id",
        "item_id",
        "family_id",
        "intended_tier",
        "cue_condition",
        "source_basis",
    ]

    write_csv(
        args.review_output,
        review_rows,
        review_fields,
    )

    write_csv(
        args.key_output,
        key_rows,
        key_fields,
    )

    print("TriageSafe-MH Blind Review Generator")
    print("=" * 42)
    print(f"Input scenarios: {len(rows)}")
    print(f"Randomization seed: {args.seed}")
    print()
    print(f"Rater sheet: {args.review_output}")
    print(f"Private key: {args.key_output}")
    print()
    print(
        "IMPORTANT: Give raters only the rater sheet. "
        "Keep the private key hidden."
    )


if __name__ == "__main__":
    main()