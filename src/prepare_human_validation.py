
"""
Prepare blinded human annotation sheets for TriageSafe-MH M4.

The script:
1. Loads the 80 existing generated responses.
2. Validates response completeness and metadata.
3. Assigns anonymous response identifiers.
4. Generates independently randomized annotation sheets.
5. Saves a separate response mapping key.

No automated judge predictions are exposed to human raters.

Run from the repository root:

    python -m src.prepare_human_validation
"""

import argparse
import csv
import json
import random

from collections import Counter
from pathlib import Path


# Repository paths
ROOT = Path(__file__).resolve().parents[1]

RAW_DIR = ROOT / "results" / "raw"

OUTPUT_DIR = ROOT / "data" / "human_validation"

PAIRED_PATH = (
    ROOT / "results" / "tables"
    / "m4_paired_judgments.csv"
)


# Experimental configuration
MODELS = [
    "qwen3_4b",
    "qwen3_8b",
]

TIERS = [
    "T1",
    "T2",
    "T3",
    "T4",
    "T5",
]

CUE_CONDITIONS = [
    "direct",
    "cue_shifted",
]

SUBJECT_SEED = 101

RANDOMIZATION_SEED = 2026

EXPECTED_RESPONSES = 80


# Fields visible to human raters
ANNOTATION_FIELDS = [
    "annotation_id",
    "scenario_text",
    "response",
    "human_escalation_level",
    "confidence",
    "rationale",
    "ambiguity_notes",
]


# Private mapping fields
KEY_FIELDS = [
    "annotation_id",
    "model",
    "item_id",
    "family_id",
    "tier",
    "cue_condition",
    "subject_seed",
]


def require(condition, message):
    """Raise an error when a validation condition fails."""

    if not condition:
        raise ValueError(message)


def load_jsonl(path):
    """Load records from a JSON Lines file."""

    with path.open(
        "r",
        encoding="utf-8",
    ) as file:

        return [
            json.loads(line)
            for line in file
            if line.strip()
        ]


def load_responses():
    """Load and validate both subject-model response files."""

    all_records = []

    model_item_ids = {}

    required_fields = {
        "item_id",
        "family_id",
        "tier",
        "cue_condition",
        "model_key",
        "seed",
        "scenario_text",
        "response",
    }

    for model in MODELS:

        path = (
            RAW_DIR
            / f"{model}_seed{SUBJECT_SEED}.jsonl"
        )

        require(
            path.exists(),
            f"Missing input file: {path}",
        )

        records = load_jsonl(path)

        require(
            len(records) == 40,
            f"{model}: expected 40 responses.",
        )

        ids = set()

        for record in records:

            missing = (
                required_fields - record.keys()
            )

            require(
                not missing,
                f"Missing fields: {missing}",
            )

            require(
                record["model_key"] == model,
                "Incorrect model metadata.",
            )

            require(
                record["seed"] == SUBJECT_SEED,
                "Unexpected generation seed.",
            )

            require(
                record["tier"] in TIERS,
                "Invalid risk tier.",
            )

            require(
                record["cue_condition"]
                in CUE_CONDITIONS,
                "Invalid cue condition.",
            )

            require(
                isinstance(record["response"], str)
                and record["response"].strip(),
                "Empty or invalid response.",
            )

            require(
                isinstance(record["scenario_text"], str)
                and record["scenario_text"].strip(),
                "Empty or invalid scenario.",
            )

            require(
                record["item_id"] not in ids,
                f"Duplicate item: {record['item_id']}",
            )

            ids.add(record["item_id"])

            all_records.append(record)

        model_item_ids[model] = ids

        print(
            f"{model}: "
            f"{len(records)} validated responses"
        )

    require(
        model_item_ids[MODELS[0]]
        == model_item_ids[MODELS[1]],
        "Subject models have different scenario sets.",
    )

    require(
        len(all_records) == EXPECTED_RESPONSES,
        "Unexpected total response count.",
    )

    # Verify matched scenario metadata across models.
    reference = {
        r["item_id"]: r
        for r in all_records
        if r["model_key"] == MODELS[0]
    }

    for record in all_records:

        original = reference[record["item_id"]]

        for field in [
            "family_id",
            "tier",
            "cue_condition",
            "scenario_text",
        ]:

            require(
                record[field] == original[field],
                f"Scenario mismatch: "
                f"{record['item_id']} / {field}",
            )

    return all_records


def validate_balance(records):
    """Verify the expected experimental balance."""

    model_counts = Counter(
        r["model_key"] for r in records
    )

    tier_counts = Counter(
        r["tier"] for r in records
    )

    cue_counts = Counter(
        r["cue_condition"] for r in records
    )

    family_counts = Counter(
        r["family_id"] for r in records
    )

    require(
        model_counts == {
            model: 40 for model in MODELS
        },
        "Unexpected model distribution.",
    )

    require(
        tier_counts == {
            tier: 16 for tier in TIERS
        },
        "Unexpected tier distribution.",
    )

    require(
        cue_counts == {
            cue: 40 for cue in CUE_CONDITIONS
        },
        "Unexpected cue distribution.",
    )

    require(
        len(family_counts) == 20,
        "Expected 20 scenario families.",
    )

    require(
        all(
            count == 4
            for count in family_counts.values()
        ),
        "Expected four responses per family.",
    )

    # Verify the complete crossed design.
    cell_counts = Counter(
        (
            r["model_key"],
            r["tier"],
            r["cue_condition"],
        )
        for r in records
    )

    for model in MODELS:
        for tier in TIERS:
            for cue in CUE_CONDITIONS:

                require(
                    cell_counts[(model, tier, cue)]
                    == 4,
                    "Unbalanced experimental cell.",
                )

    print("\nEXPERIMENTAL BALANCE")

    print("Models:", dict(model_counts))

    print("Tiers:", dict(tier_counts))

    print("Cue conditions:", dict(cue_counts))

    print("Scenario families:", len(family_counts))


def validate_paired_coverage(records):
    """Verify that every response has paired judge results."""

    require(
        PAIRED_PATH.exists(),
        "Missing paired judgment file.",
    )

    with PAIRED_PATH.open(
        "r",
        encoding="utf-8",
        newline="",
    ) as file:

        paired = list(csv.DictReader(file))

    raw_keys = {
        (
            r["model_key"],
            r["item_id"],
            int(r["seed"]),
        )
        for r in records
    }

    paired_keys = {
        (
            r["model"],
            r["item_id"],
            int(r["subject_seed"]),
        )
        for r in paired
    }

    require(
        len(paired) == EXPECTED_RESPONSES,
        "Unexpected paired judgment count.",
    )

    require(
        len(paired_keys) == len(paired),
        "Duplicate paired judgment records.",
    )

    require(
        raw_keys == paired_keys,
        "Raw and paired judgment coverage differs.",
    )

    valid_levels = {
        "E0", "E1", "E2", "E3", "E4"
    }

    for record in paired:

        require(
            record["escalation_level_phi"]
            in valid_levels,
            "Invalid Phi judgment.",
        )

        require(
            record["escalation_level_mistral"]
            in valid_levels,
            "Invalid Mistral judgment.",
        )

    print(
        "\nAll 80 responses have paired "
        "automated judgments."
    )


def prepare_annotations(records, seed):
    """Assign anonymous IDs and create annotation records."""

    # Sort before randomization to ensure reproducibility.
    shuffled = sorted(
        records,
        key=lambda r: (
            r["model_key"],
            r["item_id"],
        ),
    )

    random.Random(seed).shuffle(shuffled)

    annotations = []

    mapping_key = []

    for index, record in enumerate(
        shuffled,
        start=1,
    ):

        annotation_id = f"HV_{index:03d}"

        annotations.append({
            "annotation_id": annotation_id,
            "scenario_text": record["scenario_text"],
            "response": record["response"],
            "human_escalation_level": "",
            "confidence": "",
            "rationale": "",
            "ambiguity_notes": "",
        })

        mapping_key.append({
            "annotation_id": annotation_id,
            "model": record["model_key"],
            "item_id": record["item_id"],
            "family_id": record["family_id"],
            "tier": record["tier"],
            "cue_condition": record["cue_condition"],
            "subject_seed": record["seed"],
        })

    # Independent reproducible ordering for each rater.
    rater_a = [
        row.copy() for row in annotations
    ]

    rater_b = [
        row.copy() for row in annotations
    ]

    random.Random(seed + 1).shuffle(rater_a)

    random.Random(seed + 2).shuffle(rater_b)

    return rater_a, rater_b, mapping_key


def validate_annotation_sheets(
    rater_a,
    rater_b,
    mapping_key,
):
    """Check annotation completeness and metadata blinding."""

    expected_ids = {
        row["annotation_id"]
        for row in mapping_key
    }

    require(
        len(mapping_key) == EXPECTED_RESPONSES,
        "Unexpected annotation key length.",
    )

    require(
        len(expected_ids) == EXPECTED_RESPONSES,
        "Duplicate anonymous identifiers.",
    )

    for name, sheet in [
        ("Rater A", rater_a),
        ("Rater B", rater_b),
    ]:

        require(
            len(sheet) == EXPECTED_RESPONSES,
            f"{name}: incorrect response count.",
        )

        require(
            {
                row["annotation_id"]
                for row in sheet
            } == expected_ids,
            f"{name}: incorrect identifier coverage.",
        )

        for row in sheet:

            require(
                set(row.keys())
                == set(ANNOTATION_FIELDS),
                f"{name}: unexpected annotation fields.",
            )

            for field in [
                "human_escalation_level",
                "confidence",
                "rationale",
                "ambiguity_notes",
            ]:

                require(
                    row[field] == "",
                    "Annotation fields must be blank.",
                )

    # Verify both raters receive identical content.
    a_by_id = {
        row["annotation_id"]: row
        for row in rater_a
    }

    b_by_id = {
        row["annotation_id"]: row
        for row in rater_b
    }

    require(
        a_by_id == b_by_id,
        "Raters received different response content.",
    )

    require(
        [
            row["annotation_id"]
            for row in rater_a
        ] != [
            row["annotation_id"]
            for row in rater_b
        ],
        "Annotation order should differ.",
    )

    print("\nAnnotation sheet validation passed.")


def write_csv(path, records, fields):
    """Write a CSV file with explicit column ordering."""

    # Exclusive creation prevents accidental overwriting.
    with path.open(
        "x",
        encoding="utf-8-sig",
        newline="",
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=fields,
        )

        writer.writeheader()

        writer.writerows(records)

    print(f"Saved: {path.relative_to(ROOT)}")


def main(seed=RANDOMIZATION_SEED):
    """Execute the annotation preparation pipeline."""

    print("TRIAGESAFE-MH HUMAN VALIDATION")
    print("=" * 45)

    records = load_responses()

    validate_balance(records)

    validate_paired_coverage(records)

    rater_a, rater_b, mapping_key = (
        prepare_annotations(records, seed)
    )

    validate_annotation_sheets(
        rater_a,
        rater_b,
        mapping_key,
    )

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    outputs = [
        (
            OUTPUT_DIR / "annotation_rater_a.csv",
            rater_a,
            ANNOTATION_FIELDS,
        ),
        (
            OUTPUT_DIR / "annotation_rater_b.csv",
            rater_b,
            ANNOTATION_FIELDS,
        ),
        (
            OUTPUT_DIR / "annotation_key.csv",
            mapping_key,
            KEY_FIELDS,
        ),
    ]

    # Check all output paths before writing any files.
    existing = [
        str(path)
        for path, _, _ in outputs
        if path.exists()
    ]

    if existing:

        raise FileExistsError(
            "Existing annotation files detected. "
            "Move or archive them before regenerating: "
            + ", ".join(existing)
        )

    print("\nOUTPUT FILES")

    for path, rows, fields in outputs:

        write_csv(path, rows, fields)

    print("\nSUMMARY")

    print("Unique responses:", len(mapping_key))

    print("Rater A assignments:", len(rater_a))

    print("Rater B assignments:", len(rater_b))

    print(
        "Total planned human annotations:",
        len(rater_a) + len(rater_b),
    )

    print("Randomization seed:", seed)

    print(
        "\nHuman annotation preparation completed "
        "successfully."
    )

    print(
        "Keep annotation_key.csv separate "
        "from the rater sheets."
    )


if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        description=(
            "Prepare blinded human annotation sheets."
        )
    )

    parser.add_argument(
        "--seed",
        type=int,
        default=RANDOMIZATION_SEED,
        help="Reproducible randomization seed.",
    )

    args = parser.parse_args()

    main(seed=args.seed)
