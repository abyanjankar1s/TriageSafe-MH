"""
Generate the TriageSafe-MH development dataset skeleton.

The generator reads the validated, source-grounded scenario plan and
creates two benchmark items for every scenario family:

1. direct
2. cue_shifted

Scenario text and human annotations are intentionally left empty.
"""

import argparse
import csv
import json
from collections import Counter
from pathlib import Path


# ============================================================
# Configuration
# ============================================================

RISK_TIERS = ["T1", "T2", "T3", "T4", "T5"]

CUE_CONDITIONS = [
    "direct",
    "cue_shifted",
]

DEFAULT_PLAN = Path(
    "data/development/scenario_plan.csv"
)

DEFAULT_OUTPUT = Path(
    "data/development/development_skeleton.jsonl"
)

EXPECTED_FAMILIES = 20
EXPECTED_ITEMS = 40


# ============================================================
# Scenario plan loading
# ============================================================

def load_scenario_plan(plan_path=DEFAULT_PLAN):
    """
    Load the source-grounded development scenario plan.

    Each CSV row represents one scenario family.
    """

    with open(
        plan_path,
        "r",
        encoding="utf-8",
        newline="",
    ) as file:
        reader = csv.DictReader(file)
        return list(reader)


# ============================================================
# Record creation
# ============================================================

def create_record(
    plan_row,
    cue_condition,
    split="development",
):
    """
    Create one benchmark item from a scenario-plan family.

    The direct and cue-shifted records inherit the same persona,
    context, tier, and source-grounded scenario concept.

    Only the cue type changes between the matched pair.
    """

    family_id = plan_row["family_id"]
    tier = plan_row["tier"]

    if cue_condition not in CUE_CONDITIONS:
        raise ValueError(
            f"Invalid cue condition: {cue_condition}"
        )

    suffix = (
        "DIRECT"
        if cue_condition == "direct"
        else "SHIFTED"
    )

    item_id = f"{family_id}_{suffix}"

    cue_type = (
        plan_row["direct_cue_type"]
        if cue_condition == "direct"
        else plan_row["shifted_cue_type"]
    )

    return {
        "family_id": family_id,
        "item_id": item_id,
        "tier": tier,
        "cue_condition": cue_condition,
        "variant": "original",
        "split": split,

        # ----------------------------------------------------
        # Source-grounded scenario metadata
        # ----------------------------------------------------

        "persona_age_group": plan_row[
            "persona_age_group"
        ],

        "persona_gender": plan_row[
            "persona_gender"
        ],

        "context": plan_row["context"],

        "cue_type": cue_type,

        "author": plan_row["author"],

        "review_status": plan_row[
            "review_status"
        ],

        # ----------------------------------------------------
        # Scenario text
        # ----------------------------------------------------

        # Scenario text is authored after the family plan
        # has been validated.
        "text": "",

        # ----------------------------------------------------
        # Independent human annotations
        # ----------------------------------------------------

        "rater_a_tier": None,
        "rater_b_tier": None,

        "rater_a_lower": None,
        "rater_a_upper": None,

        "rater_b_lower": None,
        "rater_b_upper": None,

        # ----------------------------------------------------
        # Final consensus / adjudication
        # ----------------------------------------------------

        "final_lower": None,
        "final_upper": None,

        "adjudicated": False,

        # ----------------------------------------------------
        # Design provenance
        # ----------------------------------------------------

        "notes": (
            f"Scenario concept: "
            f"{plan_row['scenario_concept']} | "
            f"Source basis: "
            f"{plan_row['source_basis']}"
        ),
    }


# ============================================================
# Dataset generation
# ============================================================

def generate_dataset(plan_path=DEFAULT_PLAN):
    """
    Generate paired development records from the scenario plan.

    Every scenario family produces:

        FAMILY_DIRECT
        FAMILY_SHIFTED

    With 20 families, this produces 40 benchmark items.
    """

    plan_rows = load_scenario_plan(plan_path)

    records = []

    for plan_row in plan_rows:

        for cue_condition in CUE_CONDITIONS:

            record = create_record(
                plan_row=plan_row,
                cue_condition=cue_condition,
                split="development",
            )

            records.append(record)

    return records


# ============================================================
# Generation validation
# ============================================================

def validate_generation_counts(records):
    """
    Validate the expected development dataset size.

    Expected:
        20 unique families
        40 total items
        4 families per tier
        8 items per tier
    """

    family_ids = {
        record["family_id"]
        for record in records
    }

    if len(family_ids) != EXPECTED_FAMILIES:
        raise ValueError(
            f"Expected {EXPECTED_FAMILIES} families, "
            f"found {len(family_ids)}."
        )

    if len(records) != EXPECTED_ITEMS:
        raise ValueError(
            f"Expected {EXPECTED_ITEMS} items, "
            f"found {len(records)}."
        )

    tier_item_counts = Counter(
        record["tier"]
        for record in records
    )

    family_tiers = {}

    for record in records:
        family_tiers[
            record["family_id"]
        ] = record["tier"]

    tier_family_counts = Counter(
        family_tiers.values()
    )

    for tier in RISK_TIERS:

        if tier_family_counts[tier] != 4:
            raise ValueError(
                f"{tier}: expected 4 families, "
                f"found "
                f"{tier_family_counts[tier]}."
            )

        if tier_item_counts[tier] != 8:
            raise ValueError(
                f"{tier}: expected 8 items, "
                f"found "
                f"{tier_item_counts[tier]}."
            )

    return (
        len(family_ids),
        len(records),
    )


# ============================================================
# JSONL writing
# ============================================================

def write_jsonl(
    records,
    output_path=DEFAULT_OUTPUT,
):
    """Write benchmark records to a JSONL file."""

    output_path = Path(output_path)

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


# ============================================================
# Summary
# ============================================================

def print_summary(
    records,
    output_path,
):
    """Print a summary of the generated dataset."""

    family_ids = {
        record["family_id"]
        for record in records
    }

    tier_counts = Counter(
        record["tier"]
        for record in records
    )

    print(
        "TriageSafe-MH Dataset Generator"
    )

    print("=" * 40)

    print(
        f"Scenario families: "
        f"{len(family_ids)}"
    )

    print(
        f"Total items: "
        f"{len(records)}"
    )

    print()

    for tier in RISK_TIERS:

        print(
            f"{tier}: "
            f"{tier_counts[tier]} items"
        )

    print()

    print(
        f"Scenario plan: {DEFAULT_PLAN}"
    )

    print(
        f"Output: {output_path}"
    )

    print()

    print(
        "NOTE: Scenario text and human "
        "annotations are intentionally empty."
    )


# ============================================================
# Command-line interface
# ============================================================

def main():
    """Command-line entry point."""

    parser = argparse.ArgumentParser(
        description=(
            "Generate the TriageSafe-MH "
            "development dataset skeleton."
        )
    )

    parser.add_argument(
        "--plan",
        type=Path,
        default=DEFAULT_PLAN,
        help=(
            "Path to the scenario-plan CSV."
        ),
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=(
            "Path for the generated JSONL file."
        ),
    )

    args = parser.parse_args()

    # Generate records from the scenario plan.
    records = generate_dataset(
        plan_path=args.plan
    )

    # Confirm expected benchmark structure.
    validate_generation_counts(
        records
    )

    # Write JSONL.
    write_jsonl(
        records,
        args.output,
    )

    # Print generation summary.
    print_summary(
        records,
        args.output,
    )


if __name__ == "__main__":
    main()