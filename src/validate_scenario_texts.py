"""
Validate authored TriageSafe-MH scenario text.

This validator checks scenario_texts.csv before authored text is
merged into the development JSONL dataset.

It is designed to support incremental authoring. For example, the
file may contain only the eight T1 scenarios while T2-T5 are still
being developed.

Validation includes:
- required columns
- valid family and item identifiers
- consistency with scenario_plan.csv
- direct/cue-shifted matched pairs
- scenario word counts
- matched-pair length differences
- source provenance
- authoring notes
"""

import csv
import sys
from collections import Counter, defaultdict
from pathlib import Path


# ============================================================
# Configuration
# ============================================================

DEFAULT_TEXTS = Path(
    "data/development/scenario_texts.csv"
)

DEFAULT_PLAN = Path(
    "data/development/scenario_plan.csv"
)

VALID_CUE_CONDITIONS = {
    "direct",
    "cue_shifted",
}

MIN_WORDS = 40
MAX_WORDS = 120

MAX_PAIR_WORD_DIFFERENCE = 15


REQUIRED_TEXT_FIELDS = {
    "family_id",
    "item_id",
    "cue_condition",
    "text",
    "source_basis",
    "authoring_notes",
}


REQUIRED_PLAN_FIELDS = {
    "family_id",
    "tier",
    "source_basis",
}


# ============================================================
# File loading
# ============================================================

def load_csv(path):
    """
    Load a CSV file.

    Returns:
        rows
        fieldnames
    """

    with open(
        path,
        "r",
        encoding="utf-8",
        newline="",
    ) as file:

        reader = csv.DictReader(file)

        rows = list(reader)

        fieldnames = reader.fieldnames

    return rows, fieldnames


# ============================================================
# Helper functions
# ============================================================

def count_words(text):
    """
    Count whitespace-separated words.

    This intentionally matches the simple word-count logic used
    elsewhere in the development validation pipeline.
    """

    return len(
        text.strip().split()
    )


def expected_item_id(
    family_id,
    cue_condition,
):
    """
    Construct the expected benchmark item ID.
    """

    if cue_condition == "direct":
        suffix = "DIRECT"

    elif cue_condition == "cue_shifted":
        suffix = "SHIFTED"

    else:
        return None

    return f"{family_id}_{suffix}"


# ============================================================
# Plan validation
# ============================================================

def build_plan_lookup(
    plan_rows,
    plan_fieldnames,
):
    """
    Build a family_id -> scenario-plan row lookup.
    """

    errors = []

    if plan_fieldnames is None:

        return {}, [
            "Scenario plan has no header."
        ]

    missing_fields = (
        REQUIRED_PLAN_FIELDS
        - set(plan_fieldnames)
    )

    if missing_fields:

        errors.append(
            "Scenario plan is missing required "
            "columns: "
            + ", ".join(
                sorted(missing_fields)
            )
        )

        return {}, errors

    lookup = {}

    for row_number, row in enumerate(
        plan_rows,
        start=2,
    ):

        family_id = (
            row.get(
                "family_id",
                "",
            ).strip()
        )

        if not family_id:

            errors.append(
                f"Scenario plan row "
                f"{row_number}: family_id "
                f"cannot be empty."
            )

            continue

        if family_id in lookup:

            errors.append(
                f"Scenario plan row "
                f"{row_number}: duplicate "
                f"family_id '{family_id}'."
            )

            continue

        lookup[family_id] = row

    return lookup, errors


# ============================================================
# Authored scenario validation
# ============================================================

def validate_scenario_texts(
    text_rows,
    text_fieldnames,
    plan_lookup,
):
    """
    Validate authored scenario rows.

    The validator allows partial development files, so it does
    not require all 20 families to be present. However, every
    family that IS present must contain a complete matched pair.
    """

    errors = []

    if text_fieldnames is None:

        return [
            "Scenario text CSV has no header."
        ]

    missing_fields = (
        REQUIRED_TEXT_FIELDS
        - set(text_fieldnames)
    )

    if missing_fields:

        errors.append(
            "Scenario text CSV is missing "
            "required columns: "
            + ", ".join(
                sorted(missing_fields)
            )
        )

        return errors

    # --------------------------------------------------------
    # Duplicate item IDs
    # --------------------------------------------------------

    item_ids = [
        row.get(
            "item_id",
            "",
        ).strip()
        for row in text_rows
    ]

    duplicates = [
        item_id
        for item_id, count
        in Counter(item_ids).items()
        if item_id
        and count > 1
    ]

    if duplicates:

        errors.append(
            "Duplicate item IDs: "
            + ", ".join(
                sorted(duplicates)
            )
        )

    # --------------------------------------------------------
    # Store families for matched-pair validation
    # --------------------------------------------------------

    families = defaultdict(list)

    # --------------------------------------------------------
    # Validate individual rows
    # --------------------------------------------------------

    for row_number, row in enumerate(
        text_rows,
        start=2,
    ):

        family_id = (
            row.get(
                "family_id",
                "",
            ).strip()
        )

        item_id = (
            row.get(
                "item_id",
                "",
            ).strip()
        )

        cue_condition = (
            row.get(
                "cue_condition",
                "",
            ).strip()
        )

        text = (
            row.get(
                "text",
                "",
            ).strip()
        )

        source_basis = (
            row.get(
                "source_basis",
                "",
            ).strip()
        )

        authoring_notes = (
            row.get(
                "authoring_notes",
                "",
            ).strip()
        )

        # ----------------------------------------------------
        # Required values
        # ----------------------------------------------------

        if not family_id:

            errors.append(
                f"Row {row_number}: "
                f"family_id cannot be empty."
            )

        if not item_id:

            errors.append(
                f"Row {row_number}: "
                f"item_id cannot be empty."
            )

        if not text:

            errors.append(
                f"Row {row_number}: "
                f"text cannot be empty."
            )

        if not source_basis:

            errors.append(
                f"Row {row_number}: "
                f"source_basis cannot be empty."
            )

        if not authoring_notes:

            errors.append(
                f"Row {row_number}: "
                f"authoring_notes cannot be empty."
            )

        # ----------------------------------------------------
        # Family must exist in scenario plan
        # ----------------------------------------------------

        plan_row = plan_lookup.get(
            family_id
        )

        if family_id and plan_row is None:

            errors.append(
                f"Row {row_number}: "
                f"unknown family_id "
                f"'{family_id}'."
            )

        # ----------------------------------------------------
        # Cue condition
        # ----------------------------------------------------

        if (
            cue_condition
            not in VALID_CUE_CONDITIONS
        ):

            errors.append(
                f"Row {row_number}: invalid "
                f"cue_condition "
                f"'{cue_condition}'."
            )

        # ----------------------------------------------------
        # Item ID consistency
        # ----------------------------------------------------

        expected_id = expected_item_id(
            family_id,
            cue_condition,
        )

        if (
            expected_id is not None
            and item_id
            and item_id != expected_id
        ):

            errors.append(
                f"Row {row_number}: "
                f"item_id '{item_id}' does "
                f"not match expected ID "
                f"'{expected_id}'."
            )

        # ----------------------------------------------------
        # Word-count validation
        # ----------------------------------------------------

        if text:

            word_count = count_words(
                text
            )

            if word_count < MIN_WORDS:

                errors.append(
                    f"{item_id}: scenario "
                    f"contains {word_count} words; "
                    f"minimum is {MIN_WORDS}."
                )

            if word_count > MAX_WORDS:

                errors.append(
                    f"{item_id}: scenario "
                    f"contains {word_count} words; "
                    f"maximum is {MAX_WORDS}."
                )

        # ----------------------------------------------------
        # Source provenance consistency
        # ----------------------------------------------------

        if (
            plan_row is not None
            and source_basis
        ):

            expected_source = (
                plan_row.get(
                    "source_basis",
                    "",
                ).strip()
            )

            if (
                expected_source
                and source_basis
                != expected_source
            ):

                errors.append(
                    f"{item_id}: source_basis "
                    f"does not match "
                    f"scenario_plan.csv. "
                    f"Expected "
                    f"'{expected_source}', "
                    f"found "
                    f"'{source_basis}'."
                )

        # ----------------------------------------------------
        # Add valid family ID to pair validation
        # ----------------------------------------------------

        if family_id:

            families[
                family_id
            ].append(row)

    # --------------------------------------------------------
    # Matched-pair validation
    # --------------------------------------------------------

    for family_id, rows in families.items():

        if len(rows) != 2:

            errors.append(
                f"{family_id}: expected "
                f"2 authored scenarios, "
                f"found {len(rows)}."
            )

            continue

        conditions = {
            row[
                "cue_condition"
            ].strip()
            for row in rows
        }

        if conditions != {
            "direct",
            "cue_shifted",
        }:

            errors.append(
                f"{family_id}: expected "
                f"one direct and one "
                f"cue_shifted scenario."
            )

            continue

        direct = next(
            row
            for row in rows
            if row[
                "cue_condition"
            ].strip()
            == "direct"
        )

        shifted = next(
            row
            for row in rows
            if row[
                "cue_condition"
            ].strip()
            == "cue_shifted"
        )

        direct_text = (
            direct["text"].strip()
        )

        shifted_text = (
            shifted["text"].strip()
        )

        # ----------------------------------------------------
        # Text should not be identical
        # ----------------------------------------------------

        if direct_text == shifted_text:

            errors.append(
                f"{family_id}: direct and "
                f"cue_shifted texts are "
                f"identical."
            )

        # ----------------------------------------------------
        # Pair word-count difference
        # ----------------------------------------------------

        direct_words = count_words(
            direct_text
        )

        shifted_words = count_words(
            shifted_text
        )

        difference = abs(
            direct_words
            - shifted_words
        )

        if (
            difference
            > MAX_PAIR_WORD_DIFFERENCE
        ):

            errors.append(
                f"{family_id}: matched-pair "
                f"word-count difference is "
                f"{difference}; maximum "
                f"allowed is "
                f"{MAX_PAIR_WORD_DIFFERENCE}."
            )

    return errors


# ============================================================
# Summary
# ============================================================

def print_summary(
    text_rows,
):
    """Print authoring progress information."""

    families = {
        row.get(
            "family_id",
            "",
        ).strip()
        for row in text_rows
        if row.get(
            "family_id",
            "",
        ).strip()
    }

    tier_counts = Counter()

    for family_id in families:

        if "_" in family_id:

            tier = family_id.split(
                "_",
                1,
            )[0]

            tier_counts[tier] += 1

    print(
        "TriageSafe-MH Scenario Text Validator"
    )

    print("=" * 43)

    print(
        f"Authored items: "
        f"{len(text_rows)}"
    )

    print(
        f"Authored families: "
        f"{len(families)}"
    )

    print()

    for tier in [
        "T1",
        "T2",
        "T3",
        "T4",
        "T5",
    ]:

        print(
            f"{tier}: "
            f"{tier_counts[tier]} "
            f"authored families"
        )


# ============================================================
# Main
# ============================================================

def main():
    """Command-line entry point."""

    texts_path = (
        Path(sys.argv[1])
        if len(sys.argv) > 1
        else DEFAULT_TEXTS
    )

    plan_path = (
        Path(sys.argv[2])
        if len(sys.argv) > 2
        else DEFAULT_PLAN
    )

    # --------------------------------------------------------
    # File existence checks
    # --------------------------------------------------------

    if not texts_path.exists():

        print(
            f"ERROR: file not found: "
            f"{texts_path}"
        )

        sys.exit(1)

    if not plan_path.exists():

        print(
            f"ERROR: file not found: "
            f"{plan_path}"
        )

        sys.exit(1)

    # --------------------------------------------------------
    # Load scenario plan
    # --------------------------------------------------------

    plan_rows, plan_fieldnames = (
        load_csv(
            plan_path
        )
    )

    plan_lookup, plan_errors = (
        build_plan_lookup(
            plan_rows,
            plan_fieldnames,
        )
    )

    # --------------------------------------------------------
    # Load authored scenarios
    # --------------------------------------------------------

    text_rows, text_fieldnames = (
        load_csv(
            texts_path
        )
    )

    errors = list(
        plan_errors
    )

    if not plan_errors:

        errors.extend(
            validate_scenario_texts(
                text_rows,
                text_fieldnames,
                plan_lookup,
            )
        )

    # --------------------------------------------------------
    # Report
    # --------------------------------------------------------

    print_summary(
        text_rows
    )

    print()

    if errors:

        print(
            "VALIDATION FAILED"
        )

        for error in errors:

            print(
                f"- {error}"
            )

        sys.exit(1)

    print(
        "VALIDATION PASSED"
    )

    print(
        "All authored scenario pairs "
        "satisfy development constraints."
    )


if __name__ == "__main__":
    main()