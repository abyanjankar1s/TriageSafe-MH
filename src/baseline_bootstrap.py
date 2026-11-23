"""CPU-only fixed-level baselines and family-cluster bootstrap for TriageSafe-MH.

Uses the archived judged M3 outputs. These are *judge-derived* measurements,
not independently human-validated ground truth.
"""
import argparse
import csv
import json
import random
from collections import defaultdict
from pathlib import Path

from src.metrics import ACCEPTABLE_BANDS, add_item_metrics, load_jsonl, summarize_records

DEFAULT_INPUT = Path("results/processed/qwen3_8b_seed101_judged.jsonl")
DEFAULT_OUTPUT = Path("results/tables")
FIELDS = ("n", "band_accuracy", "under_rate", "over_rate", "mean_see", "mean_escalation")


def validate_pairs(records):
    families = defaultdict(list)
    ids = set()
    for r in records:
        for field in ("item_id", "family_id", "tier", "cue_condition", "escalation_level"):
            if field not in r:
                raise ValueError(f"Missing {field} in a judged record")
        if r["item_id"] in ids:
            raise ValueError(f"Duplicate item_id: {r['item_id']}")
        ids.add(r["item_id"])
        if r["tier"] not in ACCEPTABLE_BANDS:
            raise ValueError(f"Unknown tier: {r['tier']}")
        families[r["family_id"]].append(r)
    for fid, rows in families.items():
        if len(rows) != 2 or {r["cue_condition"] for r in rows} != {"direct", "cue_shifted"}:
            raise ValueError(f"Family {fid} must have exactly one direct and one cue_shifted item")
        if len({r["tier"] for r in rows}) != 1:
            raise ValueError(f"Family {fid} has inconsistent tiers")
    return families


def make_baseline(records, level):
    return add_item_metrics([{**r, "escalation_level": level} for r in records])


def pair_shift(enriched):
    families = validate_pairs(enriched)
    effects = []
    for rows in families.values():
        by_condition = {r["cue_condition"]: r["escalation_numeric"] for r in rows}
        effects.append(by_condition["cue_shifted"] - by_condition["direct"])
    return sum(effects) / len(effects)


def cluster_bootstrap(records, replicates, seed):
    if replicates < 100:
        raise ValueError("Use at least 100 bootstrap replicates")
    families = validate_pairs(records)
    keys = sorted(families)
    rng = random.Random(seed)
    samples = {name: [] for name in (*FIELDS[1:], "cue_shift_effect")}
    for _ in range(replicates):
        selected = [rng.choice(keys) for _ in keys]
        sample = [r for fid in selected for r in families[fid]]
        summary = summarize_records(sample)
        for name in FIELDS[1:]:
            samples[name].append(summary[name])
        samples["cue_shift_effect"].append(pair_shift_resampled(selected, families))
    return {name: percentile_bounds(values) for name, values in samples.items()}


def pair_shift_resampled(selected, families):
    differences = []
    for fid in selected:
        rows = {r["cue_condition"]: r["escalation_numeric"] for r in families[fid]}
        differences.append(rows["cue_shifted"] - rows["direct"])
    return sum(differences) / len(differences)


def percentile_bounds(values):
    ordered = sorted(values)
    def quantile(p):
        position = (len(ordered) - 1) * p
        low = int(position)
        high = min(low + 1, len(ordered) - 1)
        weight = position - low
        return ordered[low] * (1 - weight) + ordered[high] * weight
    return quantile(0.025), quantile(0.975)


def write_csv(path, rows, columns):
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def run(input_path, output_dir, replicates=10000, seed=2026):
    original = load_jsonl(input_path)
    families = validate_pairs(original)
    output_dir.mkdir(parents=True, exist_ok=True)
    comparison = []
    uncertainty = []
    for name, records in [("Qwen3-8B (M3 judge)", add_item_metrics(original))] + [
        (f"Always {level}", make_baseline(original, level))
        for level in ("E0", "E1", "E2", "E3", "E4")
    ]:
        summary = summarize_records(records)
        comparison.append({"model": name, **summary})
        ci = cluster_bootstrap(records, replicates, seed)
        for metric, (lower, upper) in ci.items():
            estimate = pair_shift(records) if metric == "cue_shift_effect" else summary[metric]
            uncertainty.append({
                "model": name, "metric": metric, "estimate": estimate,
                "ci_lower": lower, "ci_upper": upper,
                "bootstrap_replicates": replicates, "seed": seed,
                "resampling_unit": "matched_family"
            })
    write_csv(output_dir / "m4_baseline_comparison.csv", comparison, ("model", *FIELDS))
    write_csv(output_dir / "m4_bootstrap_confidence_intervals.csv", uncertainty,
              ("model", "metric", "estimate", "ci_lower", "ci_upper",
               "bootstrap_replicates", "seed", "resampling_unit"))
    print(f"Loaded {len(original)} judged responses in {len(families)} matched families")
    print(f"Bootstrap: {replicates} family-cluster replicates, seed {seed}")
    for row in comparison:
        print(f"{row['model']:<22} accuracy={row['band_accuracy']:.1%} "
              f"under={row['under_rate']:.1%} over={row['over_rate']:.1%}")
    print(f"Saved CSV tables in {output_dir}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--replicates", type=int, default=10000)
    parser.add_argument("--seed", type=int, default=2026)
    args = parser.parse_args()
    run(args.input, args.output_dir, args.replicates, args.seed)


if __name__ == "__main__":
    main()
