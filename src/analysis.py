"""
TriageSafe-MH Preliminary Results Visualization

Generates publication-ready figures and summary tables for the
40-item Qwen3-8B development experiment.

Outputs:
    results/figures/band_accuracy_by_tier.png
    results/figures/escalation_errors_by_tier.png
    results/figures/cue_condition_comparison.png
    results/tables/preliminary_results_by_tier.csv
"""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


# ============================================================
# PATHS
# ============================================================

METRICS_FILE = Path(
    "results/processed/qwen3_8b_seed101_metrics.csv"
)

PAIR_FILE = Path(
    "results/processed/qwen3_8b_seed101_metrics_pairs.csv"
)

FIGURE_DIR = Path("results/figures")
TABLE_DIR = Path("results/tables")

FIGURE_DIR.mkdir(parents=True, exist_ok=True)
TABLE_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# LOAD DATA
# ============================================================

df = pd.read_csv(METRICS_FILE)
pairs = pd.read_csv(PAIR_FILE)

TIER_ORDER = ["T1", "T2", "T3", "T4", "T5"]


# ============================================================
# SUMMARY TABLE
# ============================================================

summary_rows = []

for tier in TIER_ORDER:

    subset = df[df["tier"] == tier]

    n = len(subset)

    in_band = (subset["alignment"] == "in_band").sum()
    under = (subset["alignment"] == "under").sum()
    over = (subset["alignment"] == "over").sum()

    summary_rows.append(
        {
            "Tier": tier,
            "N": n,
            "Band Accuracy": in_band / n,
            "Under-escalation": under / n,
            "Over-escalation": over / n,
            "Mean SEE": subset[
                "signed_escalation_error"
            ].mean(),
            "Mean Escalation": subset[
                "escalation_numeric"
            ].mean(),
        }
    )


summary = pd.DataFrame(summary_rows)

summary.to_csv(
    TABLE_DIR / "preliminary_results_by_tier.csv",
    index=False,
)

print("\nPRELIMINARY RESULTS BY TIER")
print("=" * 75)

print(
    summary.to_string(
        index=False,
        formatters={
            "Band Accuracy": "{:.1%}".format,
            "Under-escalation": "{:.1%}".format,
            "Over-escalation": "{:.1%}".format,
            "Mean SEE": "{:.3f}".format,
            "Mean Escalation": "{:.3f}".format,
        },
    )
)


# ============================================================
# FIGURE 1
# BAND ACCURACY BY TIER
# ============================================================

fig, ax = plt.subplots(figsize=(8, 5))

accuracy_percent = (
    summary["Band Accuracy"] * 100
)

bars = ax.bar(
    summary["Tier"],
    accuracy_percent,
)

ax.set_title(
    "Band Accuracy by Risk Tier"
)

ax.set_xlabel(
    "TriageSafe-MH Risk Tier"
)

ax.set_ylabel(
    "Band Accuracy (%)"
)

ax.set_ylim(0, 110)

ax.axhline(
    75,
    linestyle="--",
    linewidth=1,
    label="Overall accuracy (75%)",
)

for bar, value in zip(
    bars,
    accuracy_percent,
):
    ax.text(
        bar.get_x() + bar.get_width() / 2,
        bar.get_height() + 2,
        f"{value:.1f}%",
        ha="center",
        va="bottom",
    )

ax.legend()

fig.tight_layout()

fig.savefig(
    FIGURE_DIR / "band_accuracy_by_tier.png",
    dpi=300,
    bbox_inches="tight",
)

plt.close(fig)


# ============================================================
# FIGURE 2
# UNDER- VS OVER-ESCALATION BY TIER
# ============================================================

fig, ax = plt.subplots(figsize=(9, 5))

x = np.arange(len(TIER_ORDER))
width = 0.36

under_percent = (
    summary["Under-escalation"] * 100
)

over_percent = (
    summary["Over-escalation"] * 100
)

bars_under = ax.bar(
    x - width / 2,
    under_percent,
    width,
    label="Under-escalation",
)

bars_over = ax.bar(
    x + width / 2,
    over_percent,
    width,
    label="Over-escalation",
)

ax.set_title(
    "Escalation Errors by Risk Tier"
)

ax.set_xlabel(
    "TriageSafe-MH Risk Tier"
)

ax.set_ylabel(
    "Responses (%)"
)

ax.set_xticks(x)
ax.set_xticklabels(TIER_ORDER)

ax.set_ylim(0, 100)

ax.legend()

for bars in [bars_under, bars_over]:

    for bar in bars:

        value = bar.get_height()

        if value > 0:
            ax.text(
                bar.get_x()
                + bar.get_width() / 2,
                value + 2,
                f"{value:.1f}%",
                ha="center",
                va="bottom",
            )

fig.tight_layout()

fig.savefig(
    FIGURE_DIR
    / "escalation_errors_by_tier.png",
    dpi=300,
    bbox_inches="tight",
)

plt.close(fig)


# ============================================================
# FIGURE 3
# DIRECT VS CUE-SHIFTED
# ============================================================

cue_rows = []

for condition in [
    "direct",
    "cue_shifted",
]:

    subset = df[
        df["cue_condition"] == condition
    ]

    cue_rows.append(
        {
            "Condition": condition,
            "Band Accuracy":
                (
                    subset["alignment"]
                    == "in_band"
                ).mean()
                * 100,
            "Mean Escalation":
                subset[
                    "escalation_numeric"
                ].mean(),
            "Mean SEE":
                subset[
                    "signed_escalation_error"
                ].mean(),
        }
    )


cue_summary = pd.DataFrame(cue_rows)

fig, ax = plt.subplots(figsize=(7, 5))

labels = [
    "Direct",
    "Cue-shifted",
]

values = cue_summary[
    "Mean Escalation"
]

bars = ax.bar(
    labels,
    values,
)

ax.set_title(
    "Mean Escalation by Cue Condition"
)

ax.set_ylabel(
    "Mean Escalation Level (E0–E4)"
)

ax.set_ylim(0, 4)

for bar, value in zip(
    bars,
    values,
):
    ax.text(
        bar.get_x() + bar.get_width() / 2,
        value + 0.08,
        f"{value:.2f}",
        ha="center",
        va="bottom",
    )

mean_cse = pairs[
    "cue_shift_effect"
].mean()

ax.text(
    0.5,
    0.93,
    f"Matched-pair CSE = {mean_cse:.2f}",
    transform=ax.transAxes,
    ha="center",
    va="center",
)

fig.tight_layout()

fig.savefig(
    FIGURE_DIR
    / "cue_condition_comparison.png",
    dpi=300,
    bbox_inches="tight",
)

plt.close(fig)


# ============================================================
# CUE SUMMARY TABLE
# ============================================================

cue_summary.to_csv(
    TABLE_DIR
    / "preliminary_results_by_cue.csv",
    index=False,
)


# ============================================================
# MATCHED PAIR SUMMARY
# ============================================================

pair_summary = (
    pairs.groupby("tier")[
        "cue_shift_effect"
    ]
    .agg(
        [
            "count",
            "mean",
            "min",
            "max",
        ]
    )
    .reset_index()
)

pair_summary.to_csv(
    TABLE_DIR
    / "cue_shift_effect_by_tier.csv",
    index=False,
)


# ============================================================
# FINAL OUTPUT
# ============================================================

print("\nCUE CONDITION SUMMARY")
print("=" * 75)

print(
    cue_summary.to_string(
        index=False,
        formatters={
            "Band Accuracy": "{:.1f}%".format,
            "Mean Escalation": "{:.3f}".format,
            "Mean SEE": "{:.3f}".format,
        },
    )
)

print(
    "\nOverall matched-pair CSE:",
    f"{mean_cse:.3f}",
)

print("\nGenerated figures:")

for path in sorted(
    FIGURE_DIR.glob("*.png")
):
    print(" -", path)

print("\nGenerated tables:")

for path in sorted(
    TABLE_DIR.glob("*.csv")
):
    print(" -", path)