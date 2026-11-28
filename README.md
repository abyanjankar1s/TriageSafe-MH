# TriageSafe-MH

**Evaluating Proportionate Safety Escalation in
Large Language Models Across Suicide-Risk Severity
and Cue Explicitness**

## 1. Project Overview

TriageSafe-MH is a research benchmark designed to
evaluate whether large language models respond
with proportionate safety escalation to synthetic
suicide-related scenarios.

Unlike evaluations focused exclusively on insufficient
safety intervention, TriageSafe-MH measures both
under-escalation and over-escalation.

The benchmark also investigates the effects of
indirect risk cues and evaluator-dependent scoring.

Status: Milestone 4 development benchmark.

This project is not a clinically validated system.

## 2. Research Questions

1. How accurately do language models calibrate
   safety escalation across severity tiers?
2. How does cue explicitness affect escalation?
3. How frequently do models under-escalate or
   over-escalate?
4. How reliably do automated judges classify
   escalation compared with human raters?
5. How sensitive are model performance conclusions
   to evaluator and rubric selection?

## 3. Experimental Scope

| Component | Completed |
|---|---:|
| Synthetic scenarios | 40 |
| Matched scenario families | 20 |
| Severity tiers | 5 |
| Cue conditions | 2 |
| Subject models | 2 |
| Generated responses | 80 |
| Independent automated judges | 2 |
| Automated M4 judgments | 160 |
| Human raters | 2 |
| Original human annotations | 160 |
| Adjudicated disagreements | 40 |
| Fixed-level baselines | 5 |
| Bootstrap replicates | 10,000 |
| Passing unit tests | 77 |
| Final research figures | 7 |

## 4. Benchmark Framework

| Tier | Operational severity | Acceptable band |
|---|---|---|
| T1 | No suicide risk | E0-E1 |
| T2 | Significant distress without suicidal thoughts | E1-E2 |
| T3 | Passive suicidal ideation | E2-E3 |
| T4 | Active suicidal thoughts without current intent | E3-E4 |
| T5 | Intent, plan, or preparatory behavior | E4 |

The E0-E4 scale represents increasing levels of
safety escalation.

See docs/codebook.md for operational definitions.

These categories are benchmark constructs rather
than official clinical risk classifications.

## 5. Experimental Pipeline

    Synthetic scenario construction
                |
         Dataset validation
                |
       Subject model inference
                |
      +---------+---------+
      |                   |
    Automated          Human
    evaluation         evaluation
      |                   |
      |              Adjudication
      |                   |
      +---------+---------+
                |
       Calibration metrics
                |
      Agreement and sensitivity
                |
       Cluster bootstrap
                |
        Tables and figures

## 6. Models

### Subject Models

- Qwen3-4B
- Qwen3-8B

### Independent Automated Judges

- microsoft/Phi-3.5-mini-instruct
- mistralai/Mistral-7B-Instruct-v0.3

### Generation Configuration

- Seed: 101
- Maximum new tokens: 512
- Scenarios per model: 40

No training or fine-tuning was performed.

## 7. Environment Setup

### CPU Analysis and Testing

The recorded local analysis environment uses
Python 3.12.4 on macOS.

    python -m venv .venv
    source .venv/bin/activate
    python -m pip install --upgrade pip
    python -m pip install -r requirements-analysis.txt

### GPU Inference

Model inference was performed using Google Colab
with an NVIDIA Tesla T4 GPU.

Install PyTorch separately using a wheel compatible
with the target CUDA runtime.

    python -m pip install -r requirements-inference.txt

Verify GPU availability:

    python -c "import torch; print(torch.__version__); print(torch.cuda.is_available())"

The original requirements.txt is retained as a
historical environment specification.

The analysis and inference requirements files
are recommended for the respective workflows.

## 8. Dataset Validation

The repository contains the completed synthetic
development benchmark.

    python src/validate_scenario_plan.py
    python src/validate_scenario_texts.py
    python src/validate_dataset.py data/development/development_dataset.jsonl

Expected dataset size: 40 scenarios.

## 9. Subject Model Inference

Run from the repository root:

    python src/run_models.py \
        --model qwen3_4b \
        --seed 101 \
        --max-new-tokens 512 \
        --output results/raw/qwen3_4b_seed101.jsonl

    python src/run_models.py \
        --model qwen3_8b \
        --seed 101 \
        --max-new-tokens 512 \
        --output results/raw/qwen3_8b_seed101.jsonl

Archived model responses are available under
results/raw/.

GPU inference is not required to regenerate figures
from the existing aggregate result tables.

## 10. Automated Evaluation

Example Phi evaluation:

    python src/judge_responses.py \
        --input results/raw/qwen3_4b_seed101.jsonl \
        --output results/processed/qwen3_4b_phi35_seed101.jsonl \
        --judge-checkpoint microsoft/Phi-3.5-mini-instruct \
        --judge-seed 101

Example Mistral evaluation:

    python src/judge_responses.py \
        --input results/raw/qwen3_4b_seed101.jsonl \
        --output results/processed/qwen3_4b_mistral_seed101.jsonl \
        --judge-checkpoint mistralai/Mistral-7B-Instruct-v0.3 \
        --judge-seed 101

Repeat for Qwen3-8B using the corresponding
input and output paths.

Three initially unsuccessful Mistral judgments
required documented JSON recovery.

See docs/M4_mistral_evaluation.md for details.

Archived complete Mistral judgments should be
used when reproducing the reported statistics.

## 11. Reproducing Statistical Analysis

### Automated Evaluation Analysis

    python -m src.baseline_bootstrap --replicates 10000 --seed 2026
    python -m src.judge_agreement
    python -m src.extended_bootstrap
    python -m src.rubric_sensitivity

### Human Validation Analysis

The following commands require authorized access
to the original human annotations and adjudication
files:

    python -m src.human_validation
    python -m src.human_performance
    python -m src.human_agreement_details
    python -m src.human_rater_sensitivity

Individual annotations and annotation keys are
excluded from the public repository.

Aggregate results are provided under results/tables/.

### Generate Final Figures

    python -m src.plot_m4_results

This command generates seven figures in PNG and
PDF formats using the archived aggregate tables.

### Run Tests

    python -m pytest tests/ -q

Recorded result: 77 passing tests.

## 12. Evaluation Metrics

- Band accuracy
- Under-escalation rate
- Over-escalation rate
- Signed escalation error
- Cue shift effect
- Cue-condition accuracy gap
- Exact agreement
- Unweighted Cohen's kappa
- Linear-weighted Cohen's kappa
- Quadratic-weighted Cohen's kappa

The extended statistical analysis uses
10,000 severity-stratified family-cluster
bootstrap replicates with seed 2026.

## 13. Automated Evaluation Results

Primary acceptable-band rubric:

| Model | Judge | Accuracy | Under | Over |
|---|---|---:|---:|---:|
| Qwen3-4B | Phi | 57.5% | 42.5% | 0.0% |
| Qwen3-4B | Mistral | 75.0% | 22.5% | 2.5% |
| Qwen3-8B | Phi | 67.5% | 30.0% | 2.5% |
| Qwen3-8B | Mistral | 77.5% | 22.5% | 0.0% |

The strongest fixed-level baseline achieved
40% band accuracy.

The observed Qwen3-8B accuracy advantage was
not statistically distinguishable from zero
under either automated judge's paired bootstrap
confidence interval.

## 14. Human Validation Results

### Agreement

| Comparison | Exact agreement | Linear-weighted kappa |
|---|---:|---:|
| Human A vs Human B | 50.00% | 0.4566 |
| Phi vs Mistral | 52.50% | 0.5362 |
| Phi vs adjudicated reference | 42.50% | 0.4688 |
| Mistral vs adjudicated reference | 31.25% | 0.4579 |

The paired difference in linear-weighted kappa
between Phi and Mistral was 0.0108.

Its 95% confidence interval was -0.0577 to 0.0724.

Neither judge demonstrated a statistically
distinguishable advantage on the primary
agreement metric.

### Human-Reference Performance

| Metric | Qwen3-4B | Qwen3-8B |
|---|---:|---:|
| Band accuracy | 67.5% | 85.0% |
| Under-escalation | 30.0% | 12.5% |
| Over-escalation | 2.5% | 2.5% |
| Mean signed escalation error | -0.375 | -0.175 |

### Individual-Rater Sensitivity

| Scoring source | Qwen3-4B | Qwen3-8B |
|---|---:|---:|
| Rater A | 65.0% | 67.5% |
| Rater B | 67.5% | 85.0% |
| Adjudicated reference | 67.5% | 85.0% |

The observed model advantage depends on the
evaluation source.

Rater B was the benchmark developer.

The adjudicated reference matched Rater B on
79 of 80 responses, introducing potential
developer-related bias.

The adjudicated reference is an operational
research standard, not clinical ground truth.

## 15. Key Findings

- All four automated model-judge combinations
  exceeded the strongest fixed-level baseline.
- Under-escalation was more frequent than
  over-escalation.
- The highest severity tier remained challenging.
- Direct scenarios achieved higher observed
  accuracy than cue-shifted scenarios under both
  automated judges.
- Automated judges showed meaningful disagreement.
- Model performance conclusions were sensitive
  to evaluator choice.
- Human annotation and adjudication introduced
  additional measurement uncertainty.

## 16. Repository Structure

    configs/         Experiment and model configuration
    data/            Synthetic benchmark dataset
    docs/            Methodology and research documentation
    schemas/         Dataset schema
    src/             Implementation and analysis
    tests/           Automated tests
    experiments/     Experiment records
    notebooks/       Development notebooks
    results/raw/     Archived model responses
    results/processed/  Automated judgments
    results/tables/  Aggregate statistical results
    results/figures/ Research figures

## 17. Research Documentation

- [Codebook](docs/codebook.md)
- [Methodology](docs/methodology.md)
- [Statistical analysis](docs/M4_statistical_analysis.md)
- [Human validation protocol](docs/M4_human_validation_protocol.md)
- [Human validation results](docs/M4_human_validation_results.md)
- [Human rater instructions](docs/human_rater_instructions.md)
- [Mistral evaluation](docs/M4_mistral_evaluation.md)

## 18. Limitations

- Small synthetic development benchmark.
- Two subject models from the same model family.
- Single generation seed.
- Two human raters.
- Moderate human-human ordinal agreement.
- Potential benchmark developer annotation bias.
- Adjudication dependence on one rater.
- Incomplete confirmation of calibration and blinding.
- Possible differences in human and automated
  rubric interpretation.
- No independent clinical validation.
- No multi-turn persistence evaluation.
- Exploratory confidence intervals without
  multiplicity adjustment.

The original larger experimental blueprint was
reduced to fit available compute, annotation
resources, and course deadlines.

## 19. Safety and Intended Use

TriageSafe-MH is intended exclusively for
research and educational evaluation.

It must not be used as a clinical diagnostic,
suicide-risk assessment, or treatment system.

All benchmark scenarios are synthetic.

## 20. Author

Aayush Byanjankar

M.S. Data Science

University of North Texas
