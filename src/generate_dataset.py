"""
TriageSafe-MH Dataset Skeleton Generator

Creates the structured JSONL skeleton used to author the
TriageSafe-MH development benchmark.

Development design:
    5 risk tiers
    x 4 scenario families per tier
    x 2 cue conditions
    = 40 original benchmark items

This script does NOT:
- generate scenario text
- assign human ratings
- assign final acceptable escalation bands
- generate model responses

Those steps occur later in the research pipeline.
"""

import argparse
import json
from pathlib import Path


RISK_TIERS = ["T1", "T2", "T3", "T4", "T5"]

CUE_CONDITIONS = [
    "direct",
    "cue_shifted",
]

DEFAULT_FAMILIES_PER_TIER = 4

DEFAULT_OUTPUT = Path(
    "data/development/development_skeleton.jsonl"
)


def create_record(
    tier,
    family_number,
    cue_condition,
    split="development",
):
    """
    Create one empty benchmark record.

    Parameters
    ----------
    tier : str
        Risk tier (T1-T5).

    family_number : int
        Scenario family number within the tier.

    cue_condition : str
        Either 'direct' or 'cue_shifted'.

    split : str
        Dataset split.

    Returns
    -------
    dict
        Benchmark item record.
    """

    family_id = f"{tier}_F{family_number:03d}"

    cue_label = (
        "DIRECT"
        if cue_condition == "direct"
        else "SHIFTED"
    )

    item_id = f"{family_id}_{cue_label}"

    return {
    "family_id": family_id,
    "item_id": item_id,
    "tier": tier,
    "cue_condition": cue_condition,
    "variant": "original",
    "split": split,

    # Scenario-design metadata.
    # These are assigned during controlled scenario planning.
    "persona_age_group": None,
    "persona_gender": None,
    "context": None,
    "cue_type": None,
    "author": None,
    "review_status": "draft",

    # Scenario text is authored separately.
    "text": "",

    # Independent human annotations.
    "rater_a_tier": None,
    "rater_b_tier": None,

    "rater_a_lower": None,
    "rater_a_upper": None,

    "rater_b_lower": None,
    "rater_b_upper": None,

    # Final consensus/adjudicated band.
    "final_lower": None,
    "final_upper": None,

    "adjudicated": False,
    "notes": None,
}


def generate_dataset(
    families_per_tier=DEFAULT_FAMILIES_PER_TIER,
):
    """
    Generate the complete development dataset skeleton.

    Returns
    -------
    list[dict]
        Generated benchmark records.
    """

    records = []

    for tier in RISK_TIERS:

        for family_number in range(
            1,
            families_per_tier + 1,
        ):

            for cue_condition in CUE_CONDITIONS:

                record = create_record(
                    tier=tier,
                    family_number=family_number,
                    cue_condition=cue_condition,
                )

                records.append(record)

    return records


def validate_generation_counts(
    records,
    families_per_tier,
):
    """
    Confirm that the generator created the expected
    number of records.
    """

    expected_families = (
        len(RISK_TIERS)
        * families_per_tier
    )

    expected_items = (
        expected_families
        * len(CUE_CONDITIONS)
    )

    actual_items = len(records)

    actual_families = len(
        {
            record["family_id"]
            for record in records
        }
    )

    if actual_items != expected_items:
        raise ValueError(
            "Incorrect item count: "
            f"expected {expected_items}, "
            f"generated {actual_items}"
        )

    if actual_families != expected_families:
        raise ValueError(
            "Incorrect family count: "
            f"expected {expected_families}, "
            f"generated {actual_families}"
        )

    return expected_families, expected_items


def write_jsonl(records, output_path):
    """
    Write benchmark records to JSONL.
    """

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with open(
        output_path,
        "w",
        encoding="utf-8",
    ) as file:

        for record in records:

            file.write(
                json.dumps(
                    record,
                    ensure_ascii=False,
                )
                + "\n"
            )


def print_summary(
    records,
    families_per_tier,
    output_path,
):
    """
    Print a concise generation summary.
    """

    total_families = len(
        {
            record["family_id"]
            for record in records
        }
    )

    print("TriageSafe-MH Dataset Generator")
    print("=" * 40)

    print(
        f"Risk tiers: {len(RISK_TIERS)}"
    )

    print(
        "Families per tier: "
        f"{families_per_tier}"
    )

    print(
        f"Total families: {total_families}"
    )

    print(
        f"Total items: {len(records)}"
    )

    print(
        f"Output: {output_path}"
    )

    print(
        "\nNOTE: Scenario text and human "
        "annotations are intentionally empty."
    )


def main():

    parser = argparse.ArgumentParser(
        description=(
            "Generate the TriageSafe-MH "
            "development dataset skeleton."
        )
    )

    parser.add_argument(
        "--families-per-tier",
        type=int,
        default=DEFAULT_FAMILIES_PER_TIER,
        help=(
            "Number of scenario families "
            "to generate per risk tier."
        ),
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="Output JSONL file.",
    )

    args = parser.parse_args()

    if args.families_per_tier < 1:
        parser.error(
            "--families-per-tier must be at least 1"
        )

    records = generate_dataset(
        families_per_tier=args.families_per_tier
    )

    validate_generation_counts(
        records,
        args.families_per_tier,
    )

    write_jsonl(
        records,
        args.output,
    )

    print_summary(
        records,
        args.families_per_tier,
        args.output,
    )


if __name__ == "__main__":
    main()