from src.validate_dataset import (
    validate_dataset,
    count_words,
)


def make_record(
    item_id,
    cue_condition,
    tier="T1",
    family_id="TEST_F001",
):
    text = (
        "I have had a difficult week at work because several deadlines "
        "arrived at once. I feel tired and frustrated, but I am looking "
        "forward to finishing everything soon and relaxing this weekend. "
        "Talking with a friend yesterday helped me organize my thoughts "
        "and feel more prepared for the rest of the week."
    )

    return {
        "family_id": family_id,
        "item_id": item_id,
        "tier": tier,
        "cue_condition": cue_condition,
        "variant": "original",
        "split": "development",
        "text": text,
        "rater_a_tier": None,
        "rater_b_tier": None,
        "rater_a_lower": None,
        "rater_a_upper": None,
        "rater_b_lower": None,
        "rater_b_upper": None,
        "final_lower": None,
        "final_upper": None,
        "adjudicated": False,
        "notes": None,
    }


def valid_pair():
    return [
        make_record(
            "TEST_F001_DIRECT",
            "direct",
        ),
        make_record(
            "TEST_F001_SHIFTED",
            "cue_shifted",
        ),
    ]


def test_count_words():
    assert count_words("one two three four") == 4


def test_valid_pair_passes():
    records = valid_pair()

    errors = validate_dataset(records)

    assert errors == []


def test_invalid_tier_detected():
    records = valid_pair()
    records[1]["tier"] = "T9"

    errors = validate_dataset(records)

    assert any("invalid tier" in error for error in errors)


def test_pair_tier_mismatch_detected():
    records = valid_pair()
    records[1]["tier"] = "T2"

    errors = validate_dataset(records)

    assert any("pair tier mismatch" in error for error in errors)


def test_duplicate_item_id_detected():
    records = valid_pair()
    records[1]["item_id"] = records[0]["item_id"]

    errors = validate_dataset(records)

    assert any("Duplicate item_id" in error for error in errors)


def test_missing_pair_detected():
    records = [
        make_record(
            "TEST_F001_DIRECT",
            "direct",
        )
    ]

    errors = validate_dataset(records)

    assert any(
        "missing cue-shifted item" in error
        for error in errors
    )


def test_short_scenario_detected():
    records = valid_pair()

    records[0]["text"] = "This scenario is too short."

    errors = validate_dataset(records)

    assert any("scenario too short" in error for error in errors)


def test_invalid_band_detected():
    records = valid_pair()

    records[0]["final_lower"] = 4
    records[0]["final_upper"] = 2

    errors = validate_dataset(records)

    assert any(
        "lower band cannot exceed upper band" in error
        for error in errors
    )


def test_pair_split_mismatch_detected():
    records = valid_pair()

    records[1]["split"] = "test"

    errors = validate_dataset(records)

    assert any("pair split mismatch" in error for error in errors)