"""
TriageSafe-MH subject-model runner.

Loads benchmark scenarios, runs an open-weight Hugging Face model,
and stores responses with reproducibility metadata.

Initial use:
    Qwen3-8B development smoke test

Example:
    python src/run_models.py \
        --model qwen3_8b \
        --limit 5 \
        --seed 101 \
        --output results/raw/qwen3_8b_smoke.jsonl
"""

import argparse
import json
import random
from datetime import datetime, timezone
from pathlib import Path

import torch
import yaml
from transformers import AutoModelForCausalLM, AutoTokenizer


DEFAULT_DATASET = Path(
    "data/development/development_dataset.jsonl"
)

DEFAULT_MODELS_CONFIG = Path(
    "configs/models.yaml"
)

DEFAULT_OUTPUT = Path(
    "results/raw/model_responses.jsonl"
)


def load_jsonl(path: Path):
    """Load JSON Lines records."""

    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    records = []

    with path.open("r", encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            line = line.strip()

            if not line:
                continue

            try:
                records.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"Invalid JSON on line {line_number}: {exc}"
                ) from exc

    if not records:
        raise ValueError(f"No records found in {path}")

    return records


def load_model_config(path: Path, model_key: str):
    """Load one subject-model configuration."""

    if not path.exists():
        raise FileNotFoundError(
            f"Model configuration not found: {path}"
        )

    with path.open("r", encoding="utf-8") as file:
        config = yaml.safe_load(file)

    subject_models = config.get("subject_models", {})

    if model_key not in subject_models:
        available = ", ".join(subject_models.keys())

        raise ValueError(
            f"Unknown subject model '{model_key}'. "
            f"Available models: {available}"
        )

    model_config = subject_models[model_key]

    if not model_config.get("enabled", False):
        raise ValueError(
            f"Model '{model_key}' is disabled."
        )

    checkpoint = model_config.get("checkpoint")

    if not checkpoint:
        raise ValueError(
            f"Model '{model_key}' does not have a checkpoint "
            "configured in configs/models.yaml."
        )

    return model_config


def select_records(records, limit, seed):
    """
    Reproducibly select benchmark records.

    For a smoke test, this samples records using a fixed seed.
    """

    selected = list(records)

    if limit is not None and limit < len(selected):
        rng = random.Random(seed)
        selected = rng.sample(selected, limit)

    return selected


def set_seed(seed):
    """Set Python and PyTorch random seeds."""

    random.seed(seed)
    torch.manual_seed(seed)

    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def load_model_and_tokenizer(checkpoint, revision):
    """Load Hugging Face tokenizer and causal language model."""

    print()
    print(f"Loading tokenizer: {checkpoint}")

    tokenizer = AutoTokenizer.from_pretrained(
        checkpoint,
        revision=revision,
    )

    print(f"Loading model: {checkpoint}")

    model = AutoModelForCausalLM.from_pretrained(
        checkpoint,
        revision=revision,
        torch_dtype="auto",
        device_map="auto",
    )

    model.eval()

    return tokenizer, model


def build_prompt(tokenizer, scenario_text):
    """
    Build the model input using the checkpoint's own chat template.

    TriageSafe-MH primary subject-model runs use no system prompt.

    Qwen3 thinking is explicitly disabled so the generated text
    represents the user-facing response rather than a reasoning trace.
    """

    messages = [
        {
            "role": "user",
            "content": scenario_text,
        }
    ]

    prompt = tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True,
        enable_thinking=False,
    )

    return prompt


def generate_response(
    tokenizer,
    model,
    scenario_text,
    seed,
    max_new_tokens,
    temperature,
    top_p,
    top_k,
):
    """Generate one response for one benchmark scenario."""

    set_seed(seed)

    prompt = build_prompt(
        tokenizer,
        scenario_text,
    )

    inputs = tokenizer(
        prompt,
        return_tensors="pt",
    ).to(model.device)

    input_length = inputs["input_ids"].shape[1]

    with torch.inference_mode():
        generated = model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            do_sample=True,
            temperature=temperature,
            top_p=top_p,
            top_k=top_k,
            pad_token_id=tokenizer.eos_token_id,
        )

    new_tokens = generated[0][input_length:]

    response = tokenizer.decode(
        new_tokens,
        skip_special_tokens=True,
    ).strip()

    return response


def create_result_record(
    item,
    model_key,
    model_config,
    seed,
    response,
    max_new_tokens,
    temperature,
    top_p,
    top_k,
):
    """Create reproducible output record."""

    return {
        "item_id": item["item_id"],
        "family_id": item["family_id"],
        "tier": item["tier"],
        "cue_condition": item["cue_condition"],
        "variant": item.get("variant"),
        "split": item.get("split"),
        "model_key": model_key,
        "model_family": model_config["family"],
        "model_parameters": model_config["parameters"],
        "checkpoint": model_config["checkpoint"],
        "revision": model_config.get("revision"),
        "seed": seed,
        "generation_config": {
            "thinking": False,
            "max_new_tokens": max_new_tokens,
            "temperature": temperature,
            "top_p": top_p,
            "top_k": top_k,
            "do_sample": True,
            "system_prompt": None,
        },
        "scenario_text": item["text"],
        "response": response,
        "generated_at_utc": datetime.now(
            timezone.utc
        ).isoformat(),
    }


def write_jsonl(path: Path, records):
    """Write result records as JSON Lines."""

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with path.open(
        "w",
        encoding="utf-8",
    ) as file:

        for record in records:
            file.write(
                json.dumps(
                    record,
                    ensure_ascii=False,
                )
                + "\n"
            )


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Run TriageSafe-MH subject-model inference."
        )
    )

    parser.add_argument(
        "--dataset",
        type=Path,
        default=DEFAULT_DATASET,
    )

    parser.add_argument(
        "--models-config",
        type=Path,
        default=DEFAULT_MODELS_CONFIG,
    )

    parser.add_argument(
        "--model",
        required=True,
        help=(
            "Model key from configs/models.yaml, "
            "for example qwen3_8b"
        ),
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Number of benchmark items to run.",
    )

    parser.add_argument(
        "--seed",
        type=int,
        default=101,
    )

    parser.add_argument(
        "--max-new-tokens",
        type=int,
        default=768,
    )

    parser.add_argument(
        "--temperature",
        type=float,
        default=0.7,
    )

    parser.add_argument(
        "--top-p",
        type=float,
        default=0.8,
    )

    parser.add_argument(
        "--top-k",
        type=int,
        default=20,
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
    )

    args = parser.parse_args()

    print("TriageSafe-MH Subject Model Runner")
    print("=" * 42)

    records = load_jsonl(args.dataset)

    print(f"Dataset records: {len(records)}")

    model_config = load_model_config(
        args.models_config,
        args.model,
    )

    selected = select_records(
        records,
        args.limit,
        args.seed,
    )

    print(f"Selected records: {len(selected)}")
    print(f"Model: {args.model}")
    print(
        f"Checkpoint: {model_config['checkpoint']}"
    )
    print(f"Seed: {args.seed}")
    print("Thinking mode: disabled")
    print(
        "Sampling: "
        f"temperature={args.temperature}, "
        f"top_p={args.top_p}, "
        f"top_k={args.top_k}"
    )

    tokenizer, model = load_model_and_tokenizer(
        model_config["checkpoint"],
        model_config.get("revision"),
    )

    results = []

    total = len(selected)

    for index, item in enumerate(
        selected,
        start=1,
    ):
        print()
        print(
            f"[{index}/{total}] "
            f"{item['item_id']}"
        )

        response = generate_response(
            tokenizer=tokenizer,
            model=model,
            scenario_text=item["text"],
            seed=args.seed,
            max_new_tokens=args.max_new_tokens,
            temperature=args.temperature,
            top_p=args.top_p,
            top_k=args.top_k,
        )

        result = create_result_record(
            item=item,
            model_key=args.model,
            model_config=model_config,
            seed=args.seed,
            response=response,
            max_new_tokens=args.max_new_tokens,
            temperature=args.temperature,
            top_p=args.top_p,
            top_k=args.top_k,
        )

        results.append(result)

        print(
            f"Generated response characters: "
            f"{len(response)}"
        )

    write_jsonl(
        args.output,
        results,
    )

    print()
    print("=" * 42)
    print("RUN COMPLETE")
    print(f"Responses generated: {len(results)}")
    print(f"Output: {args.output}")


if __name__ == "__main__":
    main()