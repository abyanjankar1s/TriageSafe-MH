# TriageSafe-MH

**Measuring Whether Language Models Escalate Proportionately When Suicide Risk Is Stated, Hidden, or Only Figurative**

TriageSafe-MH is a research benchmark for evaluating whether large language models respond with a level of safety escalation that is proportionate to the suicide-related risk represented in a user's message.

> **Status:** Development benchmark / preliminary experiment.  
> The current results validate the experimental pipeline and should not be interpreted as final clinical or model-safety conclusions.

---

# 1. Environment Setup

## Operating System Assumptions

The project is written in Python and can be used on:

- macOS
- Linux
- Google Colab

The development repository was managed locally on macOS, while the Qwen3-8B inference experiment was executed in Google Colab using an NVIDIA Tesla T4 GPU.

For reproducing the model-inference experiment, **Google Colab with a GPU runtime is recommended**.

---

## Python Version

The recorded Colab environment used:

```text
Python 3.13.16
```

Check your Python version with:

```bash
python --version
```

---

## Required Libraries

The recorded development environment contained:

```text
torch==2.11.0+cu130
transformers==5.21.0
accelerate==1.15.0
pandas==2.2.3
PyYAML==6.0.3
pytest==8.4.2
```

The repository currently uses the following lightweight requirements for validation and testing:

```text
pytest>=8.0,<9.0
PyYAML>=6.0,<7.0
```

GPU model inference additionally requires the Hugging Face/PyTorch stack listed above.

> **Note:** `bitsandbytes` was not present in the captured environment snapshot. If the current `run_models.py` configuration uses 4-bit bitsandbytes quantization, install a compatible `bitsandbytes` version before running that configuration.

---

## Create a Local Environment

From the project directory:

```bash
python -m venv .venv
```

Activate it on macOS/Linux:

```bash
source .venv/bin/activate
```

Then upgrade pip:

```bash
python -m pip install --upgrade pip
```

Install the repository requirements:

```bash
pip install -r requirements.txt
```

For model inference, install the additional model dependencies:

```bash
pip install torch transformers accelerate pandas
```

If using the 4-bit quantized model configuration:

```bash
pip install bitsandbytes
```

---

## Recommended IDE

Recommended development environments are:

- **Visual Studio Code** for repository development, validation, and analysis.
- **Google Colab** for Qwen3-8B GPU inference.

A GPU is not required for dataset validation, metrics, or most analysis scripts.

A CUDA-capable GPU is strongly recommended for Qwen3-8B inference.

---

## Verify the Environment

Run:

```bash
python --version
```

Then:

```bash
python -c "import torch; print('PyTorch:', torch.__version__); print('CUDA available:', torch.cuda.is_available())"
```

For a GPU runtime, the second command should report:

```text
CUDA available: True
```

You can also run the automated tests:

```bash
pytest
```

The development repository previously passed all automated tests.

---

# 2. Project Structure

```text
TriageSafe-MH/
├── README.md
├── requirements.txt
├── configs/
│   ├── experiment.yaml
│   └── models.yaml
│
├── data/
│   ├── README.md
│   ├── development/
│   │   ├── development_skeleton.jsonl
│   │   ├── scenario_plan.csv
│   │   ├── scenario_texts.csv
│   │   └── development_dataset.jsonl
│   ├── test/
│   └── processed/
│
├── docs/
│   ├── codebook.md
│   ├── methodology.md
│   └── human_rating_guide.md
│
├── schemas/
│   └── benchmark_item.schema.json
│
├── src/
│   ├── generate_dataset.py
│   ├── validate_dataset.py
│   ├── validate_scenario_plan.py
│   ├── apply_scenario_texts.py
│   ├── validate_scenario_texts.py
│   ├── create_blind_review.py
│   ├── run_models.py
│   ├── judge_responses.py
│   ├── metrics.py
│   └── analysis.py
│
├── experiments/
├── notebooks/
├── tests/
│
└── results/
    ├── raw/
    ├── processed/
    ├── tables/
    └── figures/
```

### Important Directories

`data/development/` contains the 40-scenario development benchmark.

`src/` contains the reproducible dataset, inference, judging, metrics, and analysis pipeline.

`results/raw/` contains unmodified subject-model generations.

`results/processed/` contains judged responses and calculated metrics.

`results/tables/` contains generated result tables.

`results/figures/` contains figures generated from the processed results.

`docs/` contains benchmark methodology, coding guidance, and human-rating instructions.

---

# 3. How to Run — Step by Step

## Step 1 — Clone the Repository

```bash
git clone https://github.com/abyanjankar1s/TriageSafe-MH.git
cd TriageSafe-MH
```

---

## Step 2 — Create the Environment

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
```

---

## Step 3 — Install Dependencies

Install the base repository dependencies:

```bash
pip install -r requirements.txt
```

For model inference:

```bash
pip install torch transformers accelerate pandas
```

If using the 4-bit quantized configuration:

```bash
pip install bitsandbytes
```

---

## Step 4 — Prepare and Validate the Dataset

The submitted repository already contains the development benchmark, so rebuilding the dataset is not required to reproduce the submitted results.

Validate the scenario plan:

```bash
python src/validate_scenario_plan.py
```

Validate scenario text:

```bash
python src/validate_scenario_texts.py
```

Validate the completed benchmark:

```bash
python src/validate_dataset.py
```

The submitted development dataset contains:

```text
20 matched scenario families
40 total scenarios
5 risk tiers
2 cue conditions per family
```

A successful final validation should report:

```text
Records loaded: 40
Validation PASSED
No dataset errors detected.
```

---

## Step 5 — Training

**No model training or fine-tuning is performed in this project.**

TriageSafe-MH evaluates existing open-weight language models through inference.

The preliminary development experiment uses:

```text
Model: Qwen3-8B
Seed: 101
Maximum new tokens: 512
Development scenarios: 40
```

---

## Step 6 — Run Model Inference

The preliminary experiment can be reproduced with:

```bash
python src/run_models.py \
    --model qwen3_8b \
    --seed 101 \
    --max-new-tokens 512 \
    --output results/raw/qwen3_8b_seed101.jsonl
```

Expected output:

```text
results/raw/qwen3_8b_seed101.jsonl
```

The output should contain one generated response for each of the 40 development scenarios.

Because Qwen3-8B is substantially larger than the dataset-processing components, a CUDA GPU is strongly recommended.

---

## Step 7 — Run Automated Evaluation

The generated responses are next classified using the E0-E4 response-escalation rubric.

Run:

```bash
python src/judge_responses.py
```

The judge evaluates the model response without receiving the scenario's expected escalation band or cue condition.

Expected processed output:

```text
results/processed/qwen3_8b_seed101_judged.jsonl
```

The development judge records:

- escalation level,
- direct safety check,
- crisis support,
- emergency action,
- rationale.

---

## Step 8 — Calculate Metrics

Run:

```bash
python src/metrics.py
```

The evaluation calculates:

- Band Accuracy
- Under-escalation rate
- Over-escalation rate
- Signed Escalation Error
- Cue Shift Effect
- Per-tier calibration
- Direct vs. cue-shifted performance

Expected outputs include:

```text
results/processed/qwen3_8b_seed101_metrics.csv
results/processed/qwen3_8b_seed101_metrics_pairs.csv
```

---

## Step 9 — Generate Results, Tables, and Figures

Run the analysis script:

```bash
python src/analysis.py
```

Generated outputs are written to:

```text
results/tables/
results/figures/
```

The primary figures used in the project report are:

```text
band_accuracy_by_tier.png
escalation_errors_by_tier.png
cue_condition_comparison.png
```

These figures are generated from processed model judgments rather than manually entered values.

---

## Step 10 — Verify Preliminary Results

The submitted development experiment produced:

| Metric | Result |
|---|---:|
| Responses | 40 |
| Band Accuracy | **75.0%** |
| Under-escalation | **20.0%** |
| Over-escalation | **5.0%** |
| Mean SEE | **-0.200** |
| Mean escalation | **2.175** |

### Results by Risk Tier

| Tier | Band Accuracy | Under | Over |
|---|---:|---:|---:|
| T1 | 75.0% | 0.0% | 25.0% |
| T2 | 100.0% | 0.0% | 0.0% |
| T3 | 100.0% | 0.0% | 0.0% |
| T4 | 87.5% | 12.5% | 0.0% |
| T5 | **12.5%** | **87.5%** | 0.0% |

Direct scenarios produced a mean escalation level of **2.30**, compared with **2.05** for cue-shifted scenarios.

The matched-pair mean Cue Shift Effect was:

```text
CSE = -0.25
```

---

# Approximate Runtime Expectations

Runtime depends strongly on hardware.

| Stage | Approximate Requirement |
|---|---|
| Dataset validation | Seconds |
| Unit tests | Seconds |
| Dataset preparation | Seconds |
| Metrics calculation | Seconds |
| Tables/figures | Seconds |
| Qwen3-8B model download | Several minutes depending on network |
| Qwen3-8B inference | Several minutes or longer depending on GPU |
| Automated LLM judging | Several minutes or longer depending on GPU |

The preliminary experiment was run using an **NVIDIA Tesla T4 GPU in Google Colab**.

CPU-only execution is suitable for dataset validation and analysis but is **not recommended for reproducing the Qwen3-8B inference experiment**.

---

# Reproducing the Submitted Experiment

For the shortest reproduction path:

```bash
# 1. Validate benchmark
python src/validate_dataset.py

# 2. Run Qwen3-8B
python src/run_models.py \
    --model qwen3_8b \
    --seed 101 \
    --max-new-tokens 512 \
    --output results/raw/qwen3_8b_seed101.jsonl

# 3. Judge responses
python src/judge_responses.py

# 4. Calculate metrics
python src/metrics.py

# 5. Generate tables and figures
python src/analysis.py
```

The pipeline is therefore:

```text
Dataset
   ↓
Validation
   ↓
Qwen3-8B Inference
   ↓
E0-E4 Response Judging
   ↓
Calibration Metrics
   ↓
Matched-Pair Analysis
   ↓
Tables + Figures
```

---

# Safety and Intended Use

TriageSafe-MH is a **research benchmark** and is not a clinical diagnostic or decision-support system.

The benchmark uses fully synthetic, non-graphic, method-free scenarios.

T1-T5 are operational categories created specifically for controlled language-model evaluation and should not be interpreted as official clinical risk classifications.

---

# Author

**Aayush Byanjankar**  
M.S. Data Science  
