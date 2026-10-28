"""
TriageSafe-MH Dataset Validator

Validates benchmark JSONL files before model experiments are run.

Checks:
- Required fields
- Unique item IDs
- Valid risk tiers
- Valid cue conditions
- Valid dataset splits
- Valid variants
- Scenario word count
- Escalation-band ranges
- Direct/cue-shifted pair completeness
- Pair tier consistency
- Pair word-count difference
"""

import argparse
import json
from collections import defaultdict
from pathlib import Path


VALID_TIERS = {"T1", "T2", "T3", "T4", "T5"}
VALID_CUES = {"direct", "cue_shifted"}
VALID_VARIANTS = {"original", "paraphrase"}
VALID_SPLITS = {"development", "test", "heldout"}

MIN_WORDS = 40
MAX_WORDS = 120
MAX_PAIR_WORD_DIFFERENCE = 15

REQUIRED_FIELDS = {
    "family_id",
    "item_id",
    "tier",
    "cue_condition",
    "variant",
    "split",
    "text",
    "rater_a_tier",
    "rater_b_tier",
    "rater_a_lower",
    "rater_a_upper",
    "rater_b_lower",
    "rater_b_upper",
    "final_lower",
    "final_upper",
    "adjudicated",
    "notes",
}


def count_words(text):
    """Return the number of whitespace-separated words in text."""
    return len(text.split())


def load_jsonl(path):
    """Load records from a JSONL file."""
    records = []

    with open(path, "r", encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            line = line.strip()

            if not line:
                continue

            try:
                record = json.loads(line)
                record["_line_number"] = line_number
                records.append(record)

            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"Invalid JSON on line {line_number}: {exc}"
                ) from exc

    return records


def validate_required_fields(record):
    """Check that every required field exists."""
    errors = []

    missing = REQUIRED_FIELDS - set(record.keys())

    if missing:
        errors.append(
            f"Missing required fields: {sorted(missing)}"
        )

    return errors


def validate_record(record):
    """Validate one benchmark record."""
    errors = []

    item_id = record.get("item_id", "<missing item_id>")

    if record.get("tier") not in VALID_TIERS:
        errors.append(
            f"{item_id}: invalid tier '{record.get('tier')}'"
        )

    if record.get("cue_condition") not in VALID_CUES:
        errors.append(
            f"{item_id}: invalid cue condition "
            f"'{record.get('cue_condition')}'"
        )

    if record.get("variant") not in VALID_VARIANTS:
        errors.append(
            f"{item_id}: invalid variant '{record.get('variant')}'"
        )

    if record.get("split") not in VALID_SPLITS:
        errors.append(
            f"{item_id}: invalid split '{record.get('split')}'"
        )

    text = record.get("text")

    if not isinstance(text, str) or not text.strip():
        errors.append(f"{item_id}: text must be a non-empty string")
    else:
        word_count = count_words(text)

        if word_count < MIN_WORDS:
            errors.append(
                f"{item_id}: scenario too short "
                f"({word_count} words; minimum {MIN_WORDS})"
            )

        if word_count > MAX_WORDS:
            errors.append(
                f"{item_id}: scenario too long "
                f"({word_count} words; maximum {MAX_WORDS})"
            )

    validate_optional_tier(
        record.get("rater_a_tier"),
        "rater_a_tier",
        item_id,
        errors,
    )

    validate_optional_tier(
        record.get("rater_b_tier"),
        "rater_b_tier",
        item_id,
        errors,
    )

    validate_band(
        record.get("rater_a_lower"),
        record.get("rater_a_upper"),
        "rater_a",
        item_id,
        errors,
    )

    validate_band(
        record.get("rater_b_lower"),
        record.get("rater_b_upper"),
        "rater_b",
        item_id,
        errors,
    )

    validate_band(
        record.get("final_lower"),
        record.get("final_upper"),
        "final",
        item_id,
        errors,
    )

    if not isinstance(record.get("adjudicated"), bool):
        errors.append(
            f"{item_id}: adjudicated must be true or false"
        )

    return errors


def validate_optional_tier(value, field_name, item_id, errors):
    """Validate a nullable human-rater tier."""
    if value is not None and value not in VALID_TIERS:
        errors.append(
            f"{item_id}: {field_name} must be null or one of "
            f"{sorted(VALID_TIERS)}"
        )


def validate_band(lower, upper, prefix, item_id, errors):
    """
    Validate a nullable escalation band.

    Both values must either be null or integers from 0 through 4.
    """
    if lower is None and upper is None:
        return

    if lower is None or upper is None:
        errors.append(
            f"{item_id}: {prefix} band must contain both "
            "lower and upper values or both must be null"
        )
        return

    if not isinstance(lower, int) or not isinstance(upper, int):
        errors.append(
            f"{item_id}: {prefix} band values must be integers"
        )
        return

    if not 0 <= lower <= 4 or not 0 <= upper <= 4:
        errors.append(
            f"{item_id}: {prefix} band must be between E0 and E4"
        )

    if lower > upper:
        errors.append(
            f"{item_id}: {prefix} lower band cannot exceed upper band"
        )


def validate_unique_ids(records):
    """Check that item IDs are unique."""
    errors = []
    seen = set()

    for record in records:
        item_id = record.get("item_id")

        if item_id in seen:
            errors.append(f"Duplicate item_id: {item_id}")
        else:
            seen.add(item_id)

    return errors


def validate_pairs(records):
    """
    Validate direct/cue-shifted pairs.

    Pair checks are performed separately for each family and variant,
    so original and paraphrase records are not mixed together.
    """
    errors = []
    groups = defaultdict(list)

    for record in records:
        key = (
            record.get("family_id"),
            record.get("variant"),
        )
        groups[key].append(record)

    for (family_id, variant), group in groups.items():

        cue_map = {}

        for record in group:
            cue = record.get("cue_condition")

            if cue in cue_map:
                errors.append(
                    f"{family_id} ({variant}): duplicate "
                    f"cue condition '{cue}'"
                )
            else:
                cue_map[cue] = record

        if "direct" not in cue_map:
            errors.append(
                f"{family_id} ({variant}): missing direct item"
            )

        if "cue_shifted" not in cue_map:
            errors.append(
                f"{family_id} ({variant}): missing cue-shifted item"
            )

        if "direct" not in cue_map or "cue_shifted" not in cue_map:
            continue

        direct = cue_map["direct"]
        shifted = cue_map["cue_shifted"]

        if direct.get("tier") != shifted.get("tier"):
            errors.append(
                f"{family_id} ({variant}): pair tier mismatch "
                f"({direct.get('tier')} vs {shifted.get('tier')})"
            )

        if direct.get("split") != shifted.get("split"):
            errors.append(
                f"{family_id} ({variant}): pair split mismatch "
                f"({direct.get('split')} vs {shifted.get('split')})"
            )

        direct_text = direct.get("text")
        shifted_text = shifted.get("text")

        if isinstance(direct_text, str) and isinstance(shifted_text, str):
            difference = abs(
                count_words(direct_text)
                - count_words(shifted_text)
            )

            if difference > MAX_PAIR_WORD_DIFFERENCE:
                errors.append(
                    f"{family_id} ({variant}): pair word-count "
                    f"difference is {difference}; maximum is "
                    f"{MAX_PAIR_WORD_DIFFERENCE}"
                )

    return errors


def validate_dataset(records):
    """Run all dataset-level validation checks."""
    errors = []

    for record in records:
        line_number = record.get("_line_number", "?")

        required_errors = validate_required_fields(record)

        for error in required_errors:
            errors.append(f"Line {line_number}: {error}")

        if not required_errors:
            errors.extend(validate_record(record))

    errors.extend(validate_unique_ids(records))
    errors.extend(validate_pairs(records))

    return errors


def main():
    parser = argparse.ArgumentParser(
        description="Validate a TriageSafe-MH JSONL benchmark file."
    )

    parser.add_argument(
        "dataset",
        type=Path,
        help="Path to the JSONL dataset file",
    )

    args = parser.parse_args()

    if not args.dataset.exists():
        raise FileNotFoundError(
            f"Dataset not found: {args.dataset}"
        )

    records = load_jsonl(args.dataset)

    print("TriageSafe-MH Dataset Validator")
    print("=" * 40)
    print(f"Dataset: {args.dataset}")
    print(f"Records loaded: {len(records)}")

    errors = validate_dataset(records)

    if errors:
        print(f"\nValidation FAILED with {len(errors)} error(s):\n")

        for error in errors:
            print(f"  - {error}")

        raise SystemExit(1)

    print("\nValidation PASSED")
    print("No dataset errors detected.")


if __name__ == "__main__":
    main()