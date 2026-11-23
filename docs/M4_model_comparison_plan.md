# M4: Additional subject model and independent judge

This update prepares the pipeline; it **does not contain new GPU-generated responses**.

## Design
- Existing reference subject: `Qwen/Qwen3-8B` (M3, 40 responses).
- Additional subject: `Qwen/Qwen3-4B` (40 matched prompts; same sampling parameters as M3).
- Independent judge: `microsoft/Phi-3.5-mini-instruct` (different model family from Qwen).
- Primary comparison: same 40 scenarios, same E0–E4 rubric, same independent judge for **both** subject models.
- Human validation is still required; do not present Phi judgments as verified ground truth.
- `configs/models.yaml` entries are checkpoint names, not frozen immutable commit hashes. Record the resolved commit revision and environment before publication.

## GPU steps (Colab with CUDA GPU and dependencies installed)
Run from the repository root:

```bash
python src/run_models.py --model qwen3_4b --seed 101 --max-new-tokens 512 --output results/raw/qwen3_4b_seed101.jsonl
python src/judge_responses.py --input results/raw/qwen3_8b_seed101.jsonl --judge-checkpoint microsoft/Phi-3.5-mini-instruct --output results/processed/qwen3_8b_seed101_phi35_judged.jsonl
python src/judge_responses.py --input results/raw/qwen3_4b_seed101.jsonl --judge-checkpoint microsoft/Phi-3.5-mini-instruct --output results/processed/qwen3_4b_seed101_phi35_judged.jsonl
```

First run each command with `--limit 2` and **different smoke-test output filenames**; inspect the output and failures before full runs. The subject runner currently writes its JSONL after all items; interruption can lose progress. The judge catches per-item errors and skips failed items, so **verify exactly 40 unique item IDs** in each judged file. Do not silently compare incomplete runs.

**Hardware caveat:** The subject runner uses unquantized `torch_dtype="auto"`; a free Colab T4 may run out of memory even with 4B. The judge uses 4-bit NF4 and requires a compatible CUDA/`bitsandbytes` installation. If GPU OOM occurs, stop and adapt the runner rather than altering model choice or silently changing inference settings.

**Compatibility caveat:** The Phi checkpoint may require version-specific model support and may not follow JSON-only instructions consistently. Test on two records first. The generic template option fix avoids passing Qwen-specific `enable_thinking` to non-Qwen models. This does not guarantee checkpoint compatibility.

## Next analysis
After the 40/40 outputs are verified, run the existing `src/metrics.py` against each judged file (see `--help`) and compare paired family-cluster bootstrap intervals. Report invalid/missing judge outputs and manual inter-rater agreement separately.
