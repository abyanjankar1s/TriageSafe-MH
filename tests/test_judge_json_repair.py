
import json
import pytest

from src.judge_responses import extract_json


def valid_judgment():
    return {
        "escalation_level": "E1",
        "direct_safety_check": False,
        "crisis_support": False,
        "emergency_action": False,
        "rationale": "Ordinary supportive advice."
    }


def test_valid_json_unchanged():
    data = valid_judgment()
    assert extract_json(json.dumps(data)) == data


def test_missing_closing_brace_repaired():
    data = valid_judgment()
    incomplete = json.dumps(data)[:-1]
    assert extract_json(incomplete) == data


def test_missing_required_field_rejected():
    data = valid_judgment()
    del data["rationale"]

    with pytest.raises(ValueError):
        extract_json(json.dumps(data)[:-1])


def test_truncated_string_rejected():
    incomplete = json.dumps(valid_judgment())[:-5]

    with pytest.raises(ValueError):
        extract_json(incomplete)


def test_invalid_escalation_rejected():
    data = valid_judgment()
    data["escalation_level"] = "E9"

    with pytest.raises(ValueError):
        extract_json(json.dumps(data)[:-1])
