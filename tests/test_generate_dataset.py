"""
Tests for the TriageSafe-MH development dataset generator.

These tests verify that the generator correctly reads the
source-grounded scenario plan and produces the expected paired
development dataset structure.
"""

from collections import Counter, defaultdict

from src.generate_dataset import (
    generate_dataset,
    validate_generation_counts,
)


# ============================================================
# Basic generation tests
# ============================================================

def test_default_generation_count():
    """The development plan should generate exactly 40 items."""

    records = generate_dataset()

    assert len(records) == 40


def test_default_family_count():
    """The development dataset should contain 20 unique families."""

    records = generate_dataset()

    family_ids = {
        record["family_id"]
        for record in records
    }

    assert len(family_ids) == 20


def test_each_tier_has_eight_items():
    """
    Each tier should contain four families.

    Since every family has a direct and cue-shifted item,
    each tier should contain eight total items.
    """

    records = generate_dataset()

    tier_counts = Counter(
        record["tier"]
        for record in records
    )

    assert tier_counts["T1"] == 8
    assert tier_counts["T2"] == 8
    assert tier_counts["T3"] == 8
    assert tier_counts["T4"] == 8
    assert tier_counts["T5"] == 8


# ============================================================
# Matched-pair tests
# ============================================================

def test_each_family_has_two_conditions():
    """
    Every scenario family should contain exactly two items:

    1. direct
    2. cue_shifted
    """

    records = generate_dataset()

    families = defaultdict(list)

    for record in records:
        families[
            record["family_id"]
        ].append(record)

    for family_records in families.values():

        assert len(family_records) == 2

        cue_conditions = {
            record["cue_condition"]
            for record in family_records
        }

        assert cue_conditions == {
            "direct",
            "cue_shifted",
        }


def test_matched_pairs_share_core_metadata():
    """
    Direct and cue-shifted versions should represent the same
    persona, context, tier, and split.
    """

    records = generate_dataset()

    families = defaultdict(list)

    for record in records:
        families[
            record["family_id"]
        ].append(record)

    for family_records in families.values():

        direct = next(
            record
            for record in family_records
            if record["cue_condition"] == "direct"
        )

        shifted = next(
            record
            for record in family_records
            if record["cue_condition"] == "cue_shifted"
        )

        assert direct["tier"] == shifted["tier"]

        assert (
            direct["persona_age_group"]
            == shifted["persona_age_group"]
        )

        assert (
            direct["persona_gender"]
            == shifted["persona_gender"]
        )

        assert (
            direct["context"]
            == shifted["context"]
        )

        assert (
            direct["split"]
            == shifted["split"]
        )


# ============================================================
# Identifier tests
# ============================================================

def test_generated_ids_are_unique():
    """Every generated benchmark item must have a unique ID."""

    records = generate_dataset()

    item_ids = [
        record["item_id"]
        for record in records
    ]

    assert len(item_ids) == len(set(item_ids))


def test_item_ids_match_cue_condition():
    """
    Direct records should end in DIRECT and cue-shifted
    records should end in SHIFTED.
    """

    records = generate_dataset()

    for record in records:

        if record["cue_condition"] == "direct":

            assert record[
                "item_id"
            ].endswith("_DIRECT")

        else:

            assert record[
                "item_id"
            ].endswith("_SHIFTED")


# ============================================================
# Scenario-plan integration tests
# ============================================================

def test_generation_uses_scenario_plan():
    """
    The generated dataset should contain families defined in
    the validated scenario plan.
    """

    records = generate_dataset()

    family_ids = {
        record["family_id"]
        for record in records
    }

    assert len(family_ids) == 20

    assert "T1_F001" in family_ids
    assert "T5_F004" in family_ids


def test_scenario_metadata_loaded_from_plan():
    """
    Scenario metadata should be populated from scenario_plan.csv
    instead of starting empty.
    """

    records = generate_dataset()

    for record in records:

        assert (
            record["persona_age_group"]
            is not None
        )

        assert (
            record["persona_gender"]
            is not None
        )

        assert (
            record["context"]
            is not None
        )

        assert (
            record["cue_type"]
            is not None
        )

        assert (
            record["author"]
            == "human"
        )

        assert (
            record["review_status"]
            == "draft"
        )


def test_direct_and_shifted_have_cue_types():
    """
    Both versions of every family should receive a cue type
    from the scenario plan.
    """

    records = generate_dataset()

    for record in records:

        cue_type = record["cue_type"]

        assert isinstance(cue_type, str)
        assert cue_type.strip() != ""


def test_source_provenance_is_preserved():
    """
    Generated records should preserve the scenario concept and
    source basis from the source-grounded scenario plan.
    """

    records = generate_dataset()

    for record in records:

        assert record["notes"] is not None

        assert (
            "Scenario concept:"
            in record["notes"]
        )

        assert (
            "Source basis:"
            in record["notes"]
        )


# ============================================================
# Scenario-text tests
# ============================================================

def test_generated_text_is_empty():
    """
    Scenario text should remain empty at the skeleton stage.

    Text will be authored only after the scenario family plan
    has been validated.
    """

    records = generate_dataset()

    for record in records:

        assert record["text"] == ""


# ============================================================
# Human-annotation tests
# ============================================================

def test_annotations_start_empty():
    """
    Human annotation fields must remain empty until independent
    human review takes place.
    """

    records = generate_dataset()

    for record in records:

        assert record["rater_a_tier"] is None
        assert record["rater_b_tier"] is None

        assert record["rater_a_lower"] is None
        assert record["rater_a_upper"] is None

        assert record["rater_b_lower"] is None
        assert record["rater_b_upper"] is None

        assert record["final_lower"] is None
        assert record["final_upper"] is None

        assert record["adjudicated"] is False


# ============================================================
# Count-validation tests
# ============================================================

def test_generation_count_validation():
    """
    The generation validator should confirm the expected
    20-family / 40-item development dataset.
    """

    records = generate_dataset()

    families, items = (
        validate_generation_counts(
            records
        )
    )

    assert families == 20
    assert items == 40