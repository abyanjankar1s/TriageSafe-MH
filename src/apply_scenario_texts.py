"""
Apply authored scenario text to the TriageSafe-MH development skeleton.

The script reads candidate scenario text from scenario_texts.csv and
inserts it into matching records in development_skeleton.jsonl.

This keeps dataset generation separate from scenario authoring and
provides a reproducible record of authored benchmark content.
"""

import argparse
import csv
import json
from pathlib import Path


DEFAULT_TEXTS = Path(
    "data/development/scenario_texts.csv"
)

DEFAULT_INPUT = Path(
    "data/development/development_skeleton.jsonl"
)

DEFAULT_OUTPUT = Path(
    "data/development/development_dataset.jsonl"
)


# ============================================================
# File loading
# ============================================================

def load_scenario_texts(path):
    """Load authored scenario texts keyed by item_id."""

    with open(
        path,
        "r",
        encoding="utf-8",
        newline="",
    ) as file:
        reader = csv.DictReader(file)
        rows = list(reader)

    texts = {}

    for row in rows:
        item_id = row["item_id"].strip()

        if item_id in texts:
            raise ValueError(
                f"Duplicate authored item_id: {item_id}"
            )

        texts[item_id] = row

    return texts


def load_jsonl(path):
    """Load JSONL benchmark records."""

    records = []

    with open(
        path,
        "r",
        encoding="utf-8",
    ) as file:

        for line_number, line in enumerate(
            file,
            start=1,
        ):
            line = line.strip()

            if not line:
                continue

            try:
                records.append(
                    json.loads(line)
                )

            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"Invalid JSON on line "
                    f"{line_number}: {exc}"
                ) from exc

    return records


# ============================================================
# Scenario application
# ============================================================

def apply_scenario_texts(
    records,
    authored_texts,
):
    """
    Apply authored text to matching skeleton records.

    Metadata is checked before text is inserted so that an
    authored row cannot accidentally be assigned to the wrong
    family or cue condition.
    """

    record_ids = {
        record["item_id"]
        for record in records
    }

    unknown_ids = (
        set(authored_texts)
        - record_ids
    )

    if unknown_ids:
        raise ValueError(
            "Authored scenario IDs not found in "
            "the development skeleton: "
            + ", ".join(
                sorted(unknown_ids)
            )
        )

    updated_records = []
    applied_count = 0

    for record in records:

        item_id = record["item_id"]

        if item_id not in authored_texts:
            updated_records.append(record)
            continue

        authored = authored_texts[item_id]

        # --------------------------------------------
        # Verify matched metadata
        # --------------------------------------------

        if (
            authored["family_id"].strip()
            != record["family_id"]
        ):
            raise ValueError(
                f"{item_id}: family_id mismatch."
            )

        if (
            authored["cue_condition"].strip()
            != record["cue_condition"]
        ):
            raise ValueError(
                f"{item_id}: cue_condition mismatch."
            )

        # --------------------------------------------
        # Apply scenario text
        # --------------------------------------------

        text = authored["text"].strip()

        if not text:
            raise ValueError(
                f"{item_id}: authored text is empty."
            )

        updated = record.copy()

        updated["text"] = text

        updated_records.append(updated)

        applied_count += 1

    return updated_records, applied_count


# ============================================================
# Output
# ============================================================

def write_jsonl(records, path):
    """Write records to JSONL."""

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with open(
        path,
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
# CLI
# ============================================================

def main():
    """Command-line entry point."""

    parser = argparse.ArgumentParser(
        description=(
            "Apply authored TriageSafe-MH "
            "scenario text to the development "
            "dataset skeleton."
        )
    )

    parser.add_argument(
        "--texts",
        type=Path,
        default=DEFAULT_TEXTS,
    )

    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_INPUT,
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
    )

    args = parser.parse_args()

    authored_texts = (
        load_scenario_texts(
            args.texts
        )
    )

    records = load_jsonl(
        args.input
    )

    updated_records, applied_count = (
        apply_scenario_texts(
            records,
            authored_texts,
        )
    )

    write_jsonl(
        updated_records,
        args.output,
    )

    print(
        "TriageSafe-MH Scenario Text Application"
    )
    print("=" * 44)

    print(
        f"Skeleton records: {len(records)}"
    )

    print(
        f"Authored scenarios available: "
        f"{len(authored_texts)}"
    )

    print(
        f"Scenario texts applied: "
        f"{applied_count}"
    )

    remaining = sum(
        1
        for record in updated_records
        if not record["text"].strip()
    )

    print(
        f"Scenarios still awaiting text: "
        f"{remaining}"
    )

    print(
        f"Output: {args.output}"
    )


if __name__ == "__main__":
    main()