from src.generate_dataset import (
    RISK_TIERS,
    generate_dataset,
    validate_generation_counts,
)


def test_default_generation_count():
    records = generate_dataset()

    assert len(records) == 40


def test_default_family_count():
    records = generate_dataset()

    families = {
        record["family_id"]
        for record in records
    }

    assert len(families) == 20


def test_each_tier_has_eight_items():
    records = generate_dataset()

    for tier in RISK_TIERS:

        tier_records = [
            record
            for record in records
            if record["tier"] == tier
        ]

        assert len(tier_records) == 8


def test_each_family_has_two_conditions():
    records = generate_dataset()

    families = {}

    for record in records:

        families.setdefault(
            record["family_id"],
            set(),
        )

        families[
            record["family_id"]
        ].add(
            record["cue_condition"]
        )

    for conditions in families.values():

        assert conditions == {
            "direct",
            "cue_shifted",
        }


def test_generated_ids_are_unique():
    records = generate_dataset()

    item_ids = [
        record["item_id"]
        for record in records
    ]

    assert len(item_ids) == len(
        set(item_ids)
    )


def test_generated_text_is_empty():
    records = generate_dataset()

    assert all(
        record["text"] == ""
        for record in records
    )


def test_annotations_start_empty():
    records = generate_dataset()

    for record in records:

        assert record["rater_a_tier"] is None
        assert record["rater_b_tier"] is None

        assert record["final_lower"] is None
        assert record["final_upper"] is None

        assert record["adjudicated"] is False


def test_custom_family_count():
    records = generate_dataset(
        families_per_tier=2
    )

    assert len(records) == 20


def test_generation_count_validation():
    records = generate_dataset()

    families, items = (
        validate_generation_counts(
            records,
            families_per_tier=4,
        )
    )

    assert families == 20
    assert items == 40

def test_scenario_metadata_starts_empty():
    records = generate_dataset()

    for record in records:
        assert record["persona_age_group"] is None
        assert record["persona_gender"] is None
        assert record["context"] is None
        assert record["cue_type"] is None
        assert record["author"] is None
        assert record["review_status"] == "draft"