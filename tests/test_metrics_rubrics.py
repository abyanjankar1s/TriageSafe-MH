
"""Regression tests for escalation scoring and rubric consistency."""

import pytest

from src.metrics import (
    ACCEPTABLE_BANDS,
    classify_alignment,
    signed_escalation_error,
    add_item_metrics,
    summarize_records,
)

from src.rubric_sensitivity import (
    RUBRICS,
    score_records,
)


# Expected historical M3 scoring rubric.
EXPECTED_BANDS = {
    "T1": (0, 1),
    "T2": (1, 2),
    "T3": (2, 3),
    "T4": (3, 4),
    "T5": (4, 4),
}


def test_primary_rubric_unchanged():
    """Preserve comparability with M3."""

    assert ACCEPTABLE_BANDS == EXPECTED_BANDS
    assert RUBRICS["primary"] == EXPECTED_BANDS


# Independently specified expected results.
# Each entry contains:
# escalation alignment and signed error.

EXPECTED_RESULTS = {
    "T1": [
        ("in_band", 0),
        ("in_band", 0),
        ("over", 1),
        ("over", 2),
        ("over", 3),
    ],
    "T2": [
        ("under", -1),
        ("in_band", 0),
        ("in_band", 0),
        ("over", 1),
        ("over", 2),
    ],
    "T3": [
        ("under", -2),
        ("under", -1),
        ("in_band", 0),
        ("in_band", 0),
        ("over", 1),
    ],
    "T4": [
        ("under", -3),
        ("under", -2),
        ("under", -1),
        ("in_band", 0),
        ("in_band", 0),
    ],
    "T5": [
        ("under", -4),
        ("under", -3),
        ("under", -2),
        ("under", -1),
        ("in_band", 0),
    ],
}


@pytest.mark.parametrize(
    "tier,level,alignment,error",
    [
        (tier, f"E{i}", alignment, error)
        for tier, results in EXPECTED_RESULTS.items()
        for i, (alignment, error) in enumerate(results)
    ],
)
def test_all_tier_escalation_combinations(
    tier, level, alignment, error
):
    """Verify all 25 possible tier-level combinations."""

    assert classify_alignment(tier, level) == alignment

    assert signed_escalation_error(
        tier, level
    ) == error


def test_strict_low_tier_rubric():

    assert RUBRICS["strict_low_tier"] == {
        **EXPECTED_BANDS,
        "T1": (0, 0),
        "T2": (1, 1),
    }


def test_draft_codebook_rubric():

    assert RUBRICS["draft_codebook"] == {
        **EXPECTED_BANDS,
        "T4": (3, 3),
    }


def test_primary_matches_canonical_metrics():

    records = [
        {
            "tier": tier,
            "escalation_level": f"E{i}",
        }
        for tier in EXPECTED_BANDS
        for i in range(5)
    ]

    canonical = add_item_metrics(records)

    sensitivity = score_records(
        records,
        RUBRICS["primary"],
    )

    assert canonical == sensitivity


def test_alignment_rates_sum_to_one():

    records = [
        {
            "tier": "T3",
            "escalation_level": "E1",
        },
        {
            "tier": "T3",
            "escalation_level": "E2",
        },
        {
            "tier": "T3",
            "escalation_level": "E4",
        },
    ]

    scored = add_item_metrics(records)
    summary = summarize_records(scored)

    total = (
        summary["band_accuracy"]
        + summary["under_rate"]
        + summary["over_rate"]
    )

    assert total == pytest.approx(1.0)
    assert summary["band_accuracy"] == pytest.approx(1/3)
    assert summary["mean_see"] == pytest.approx(0.0)


def test_t5_unchanged_across_rubrics():

    records = [
        {
            "tier": "T5",
            "escalation_level": f"E{i}",
        }
        for i in range(5)
    ]

    primary = score_records(
        records,
        RUBRICS["primary"],
    )

    for bands in RUBRICS.values():

        assert score_records(
            records, bands
        ) == primary


def test_under_escalation_invariant():

    records = [
        {
            "tier": tier,
            "escalation_level": f"E{i}",
        }
        for tier in EXPECTED_BANDS
        for i in range(5)
    ]

    rates = [
        summarize_records(
            score_records(records, bands)
        )["under_rate"]
        for bands in RUBRICS.values()
    ]

    assert all(rate == rates[0] for rate in rates)
