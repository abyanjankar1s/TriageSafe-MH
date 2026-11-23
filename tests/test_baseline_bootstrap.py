import unittest
from src.baseline_bootstrap import make_baseline, pair_shift, validate_pairs, percentile_bounds, cluster_bootstrap
from src.metrics import summarize_records, add_item_metrics


def sample():
    return [
        {"item_id":"a","family_id":"f1","tier":"T1","cue_condition":"direct","escalation_level":"E0"},
        {"item_id":"b","family_id":"f1","tier":"T1","cue_condition":"cue_shifted","escalation_level":"E1"},
        {"item_id":"c","family_id":"f2","tier":"T5","cue_condition":"direct","escalation_level":"E4"},
        {"item_id":"d","family_id":"f2","tier":"T5","cue_condition":"cue_shifted","escalation_level":"E3"},
    ]


class TestBaselines(unittest.TestCase):
    def test_fixed_e4(self):
        result = summarize_records(make_baseline(sample(), "E4"))
        self.assertEqual(result["band_accuracy"], .5)
        self.assertEqual(result["over_rate"], .5)

    def test_cue_shift(self):
        self.assertEqual(pair_shift(add_item_metrics(sample())), 0)

    def test_reject_incomplete_family(self):
        with self.assertRaises(ValueError):
            validate_pairs(sample()[:3])

    def test_bootstrap_reproducible(self):
        records = add_item_metrics(sample())
        self.assertEqual(cluster_bootstrap(records, 100, 42),
                         cluster_bootstrap(records, 100, 42))

    def test_percentile(self):
        self.assertEqual(percentile_bounds([1]*100), (1, 1))
