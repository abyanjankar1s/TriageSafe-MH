"""Validate the TriageSafe-MH development scenario plan."""

import csv
import sys
from collections import Counter
from pathlib import Path


VALID_TIERS = {"T1", "T2", "T3", "T4", "T5"}

VALID_AGE_GROUPS = {
    "adult_18_24",
    "adult_25_34",
    "adult_35_49",
    "adult_50_64",
    "adult_65_plus",
}

VALID_GENDERS = {
    "woman",
    "man",
    "nonbinary",
    "unspecified",
}

VALID_AUTHORS = {
    "human",
    "ai_assisted",
}

VALID_REVIEW_STATUSES = {
    "draft",
    "reviewed",
    "approved",
}

REQUIRED_FIELDS = {
    "family_id",
    "tier",
    "persona_age_group",
    "persona_gender",
    "context",
    "direct_cue_type",
    "shifted_cue_type",
    "scenario_concept",
    "source_basis",
    "author",
    "review_status",
}

EXPECTED_FAMILIES_PER_TIER = 4
EXPECTED_TOTAL_FAMILIES = 20


def load_plan(path):
    """Load scenario-plan CSV records."""
    with open(path, "r", encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)
        return list(reader), reader.fieldnames


def validate_plan(records, fieldnames):
    """Validate structure and balance of the scenario plan."""
    errors = []

    if fieldnames is None:
        return ["CSV has no header."]

    missing_fields = REQUIRED_FIELDS - set(fieldnames)

    if missing_fields:
        errors.append(
            "Missing required columns: "
            + ", ".join(sorted(missing_fields))
        )

    if len(records) != EXPECTED_TOTAL_FAMILIES:
        errors.append(
            f"Expected {EXPECTED_TOTAL_FAMILIES} families, "
            f"found {len(records)}."
        )

    family_ids = [
        record.get("family_id", "").strip()
        for record in records
    ]

    duplicates = [
        family_id
        for family_id, count in Counter(family_ids).items()
        if family_id and count > 1
    ]

    if duplicates:
        errors.append(
            "Duplicate family IDs: "
            + ", ".join(sorted(duplicates))
        )

    tier_counts = Counter()

    for row_number, record in enumerate(records, start=2):
        family_id = record.get("family_id", "").strip()
        tier = record.get("tier", "").strip()

        if tier not in VALID_TIERS:
            errors.append(
                f"Row {row_number}: invalid tier '{tier}'."
            )
        else:
            tier_counts[tier] += 1

        # Family ID must begin with its assigned tier.
        if family_id and tier in VALID_TIERS:
            if not family_id.startswith(f"{tier}_"):
                errors.append(
                    f"Row {row_number}: family_id '{family_id}' "
                    f"does not match tier '{tier}'."
                )

        age_group = record.get("persona_age_group", "").strip()

        if age_group not in VALID_AGE_GROUPS:
            errors.append(
                f"Row {row_number}: invalid persona_age_group "
                f"'{age_group}'."
            )

        gender = record.get("persona_gender", "").strip()

        if gender not in VALID_GENDERS:
            errors.append(
                f"Row {row_number}: invalid persona_gender "
                f"'{gender}'."
            )

        author = record.get("author", "").strip()

        if author not in VALID_AUTHORS:
            errors.append(
                f"Row {row_number}: invalid author '{author}'."
            )

        review_status = record.get("review_status", "").strip()

        if review_status not in VALID_REVIEW_STATUSES:
            errors.append(
                f"Row {row_number}: invalid review_status "
                f"'{review_status}'."
            )

        # These fields must contain actual design information.
        nonempty_fields = [
            "context",
            "direct_cue_type",
            "shifted_cue_type",
            "scenario_concept",
            "source_basis",
        ]

        for field in nonempty_fields:
            value = record.get(field, "").strip()

            if not value:
                errors.append(
                    f"Row {row_number}: '{field}' cannot be empty."
                )

    # Require exactly four families in every tier.
    for tier in sorted(VALID_TIERS):
        count = tier_counts[tier]

        if count != EXPECTED_FAMILIES_PER_TIER:
            errors.append(
                f"{tier}: expected "
                f"{EXPECTED_FAMILIES_PER_TIER} families, "
                f"found {count}."
            )

    return errors


def main():
    if len(sys.argv) > 1:
        path = Path(sys.argv[1])
    else:
        path = Path(
            "data/development/scenario_plan.csv"
        )

    if not path.exists():
        print(f"ERROR: file not found: {path}")
        sys.exit(1)

    records, fieldnames = load_plan(path)
    errors = validate_plan(records, fieldnames)

    print("TriageSafe-MH Scenario Plan Validator")
    print("=" * 42)
    print(f"File: {path}")
    print(f"Families: {len(records)}")

    tier_counts = Counter(
        record.get("tier", "").strip()
        for record in records
    )

    for tier in sorted(VALID_TIERS):
        print(f"{tier}: {tier_counts[tier]} families")

    print()

    if errors:
        print("VALIDATION FAILED")

        for error in errors:
            print(f"- {error}")

        sys.exit(1)

    print("VALIDATION PASSED")
    print(
        "20 unique families with 4 families "
        "per tier."
    )


if __name__ == "__main__":
    main()