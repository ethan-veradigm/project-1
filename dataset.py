"""
PubMedQA dataset loader.

Loads either the 'pqa_labeled' or 'pqa_artificial' config from HuggingFace,
formats the context, and yields PubMedQASample objects ready for evaluation.
"""

from __future__ import annotations

from datasets import load_dataset

from utils import EvalConfig, PubMedQASample


def _format_context(context_dict: dict) -> tuple[str, list]:
    """
    Convert the raw HuggingFace context dict into a readable string and a list
    of section labels.

    The PubMedQA context field looks like:
        {
            "contexts": ["sentence A", "sentence B", ...],
            "labels":   ["BACKGROUND", "METHODS", "RESULTS", ...],
            "meshes":   ["term1", "term2", ...]
        }
    """
    contexts: list[str] = context_dict.get("contexts", [])
    labels: list[str] = context_dict.get("labels", [])

    # Pair each paragraph with its section label for readability
    parts: list[str] = []
    for i, text in enumerate(contexts):
        label = labels[i] if i < len(labels) else f"SECTION {i + 1}"
        parts.append(f"[{label}]\n{text.strip()}")

    formatted = "\n\n".join(parts)
    return formatted, labels


def load_pubmedqa(config: EvalConfig) -> list[PubMedQASample]:
    """
    Load PubMedQA from HuggingFace and return a list of PubMedQASample objects.

    Args:
        config: EvalConfig controlling which split/partition to load and how
                many samples to use.

    Returns:
        List of PubMedQASample objects.
    """
    print(
        f"Loading PubMedQA  split='{config.dataset_split}'  "
        f"partition='{config.dataset_partition}'  "
        f"subset='{config.dataset_subset or 'all'}'  "
        f"max_samples={config.max_samples or 'all'} ..."
    )

    ds = load_dataset(config.dataset_name, config.dataset_split)

    # Access the partition (e.g. "train") from the DatasetDict
    ds = ds[config.dataset_partition]

    # Filter by row-level subset if specified
    if config.dataset_subset:
        before = len(ds)
        ds = ds.filter(lambda row: row.get("subset") == config.dataset_subset)
        print(f"Subset filter '{config.dataset_subset}': {before} → {len(ds)} rows.")
        if len(ds) == 0:
            available = list(set(ds.unique("subset")))
            raise ValueError(
                f"No rows matched subset='{config.dataset_subset}'. "
                f"Available subsets: {available}"
            )

    # Optionally truncate
    if config.max_samples is not None:
        ds = ds.select(range(min(config.max_samples, len(ds))))

    samples: list[PubMedQASample] = []
    for row in ds:
        context_str, context_labels = _format_context(row["context"])
        samples.append(
            PubMedQASample(
                pubid=str(row["pubid"]),
                question=row["question"],
                context=context_str,
                context_labels=context_labels,
                long_answer=row.get("long_answer", ""),
                gold_label=row["final_decision"].strip().lower(),
            )
        )

    print(f"Loaded {len(samples)} samples.")
    return samples
