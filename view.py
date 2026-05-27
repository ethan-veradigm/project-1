"""
Random entry inspector for eval_results.json.

Usage:
    python inspect.py                          # pick a random entry
    python inspect.py --index 42              # pick a specific entry by index
    python inspect.py --file my_results.json  # use a different results file
    python inspect.py --status correct        # random entry filtered by judge verdict
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path


# ---------------------------------------------------------------------------
# Display helpers
# ---------------------------------------------------------------------------

RESET  = "\033[0m"
BOLD   = "\033[1m"
CYAN   = "\033[36m"
GREEN  = "\033[32m"
RED    = "\033[31m"
YELLOW = "\033[33m"
BLUE   = "\033[34m"
DIM    = "\033[2m"


def _color(text: str, code: str) -> str:
    return f"{code}{text}{RESET}"


def _header(title: str) -> str:
    width = 60
    bar = "─" * width
    return f"\n{_color(bar, CYAN)}\n{_color(f'  {title}', BOLD)}\n{_color(bar, CYAN)}"


def _field(label: str, value: str, color: str = "") -> None:
    label_str = _color(f"{label}:", BOLD)
    value_str = _color(value, color) if color else value
    print(f"  {label_str} {value_str}")


def _verdict_color(verdict: str) -> str:
    return {
        "correct": GREEN,
        "incorrect": RED,
    }.get(verdict, "")


def _label_color(label: str) -> str:
    return {
        "yes": GREEN,
        "no": RED,
        "maybe": YELLOW,
    }.get(label, "")


def display_entry(entry: dict, index: int, total: int) -> None:
    """Pretty-print a single eval result entry."""

    print(_header(f"Entry {index + 1} of {total}  ·  PubMed ID: {entry.get('pubid', '?')}"))

    # --- Question & context --------------------------------------------------
    print(f"\n{_color('QUESTION', BOLD + BLUE)}")
    print(f"  {entry.get('question', 'N/A')}")

    context = entry.get("context", "")
    if context:
        print(f"\n{_color('CONTEXT', BOLD + BLUE)}")
        for line in context.splitlines():
            print(f"  {_color(line, DIM) if line.startswith('[') else '  ' + line}")

    # --- Gold answer ---------------------------------------------------------
    gold = entry.get("gold_label", "?")
    print(f"\n{_color('GOLD ANSWER', BOLD + BLUE)}")
    _field("Label", gold.upper(), _label_color(gold))

    long_answer = entry.get("long_answer", "")
    if long_answer:
        print(f"  {_color('Long answer:', BOLD)} {long_answer}")

    # --- Candidate response --------------------------------------------------
    candidate = entry.get("candidate")
    print(_header("Candidate Response"))
    if not candidate:
        print(f"  {_color('No candidate response recorded.', RED)}")
    elif candidate.get("error"):
        _field("Error", candidate["error"], RED)
    else:
        ans = candidate.get("answer", "?")
        _field("Answer", ans.upper(), _label_color(ans))
        print(f"\n  {_color('Reasoning:', BOLD)}")
        for line in candidate.get("reasoning", "").splitlines():
            print(f"    {line}")
        print(f"\n  {_color('Key Evidence:', BOLD)}")
        for line in candidate.get("key_evidence", "").splitlines():
            print(f"    {line}")

    # --- Judge evaluation ----------------------------------------------------
    judge = entry.get("judge")
    print(_header("Judge Evaluation"))
    if not judge:
        print(f"  {_color('No judge response recorded.', RED)}")
    elif judge.get("error") and not judge.get("verdict"):
        _field("Error", judge["error"], RED)
    else:
        verdict = judge.get("verdict", "?")
        match = judge.get("label_match", False)
        score = judge.get("quality_score", 0)

        _field("Verdict",     verdict.upper(), _verdict_color(verdict))
        _field("Label match", "✓ YES" if match else "✗ NO", GREEN if match else RED)
        _field("Quality",     f"{score} / 5",  GREEN if score >= 4 else YELLOW if score >= 3 else RED)

        print(f"\n  {_color('Reasoning:', BOLD)}")
        for line in judge.get("reasoning", "").splitlines():
            print(f"    {line}")

    print(f"\n{_color('─' * 60, CYAN)}\n")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def _pick_entry_interactively(entries: list[dict]) -> tuple[int, dict]:
    """Show a numbered summary list of entries and let the user pick one."""
    print(_color("\nEntries:", BOLD))

    for i, entry in enumerate(entries):
        pubid    = entry.get("pubid", "?")
        question = entry.get("question", "")
        # Truncate long questions for the listing
        preview  = question if len(question) <= 80 else question[:77] + "..."
        gold     = entry.get("gold_label", "?")
        verdict  = entry.get("judge", {}).get("verdict", "—") if entry.get("judge") else "—"

        gold_c    = _label_color(gold)
        verdict_c = _verdict_color(verdict)

        print(
            f"  {_color(str(i + 1).rjust(4), DIM)}  "
            f"{_color(f'[{gold.upper()}]', gold_c)} "
            f"{_color(f'[{verdict}]', verdict_c)}  "
            f"{_color(pubid, DIM)}  {preview}"
        )

    print()
    while True:
        raw = input(
            f"Select an entry {_color(f'[1–{len(entries)}] or r for random', DIM)}: "
        ).strip().lower()

        if raw == "r":
            index = random.randrange(len(entries))
            return index, entries[index]
        if raw.isdigit() and 1 <= int(raw) <= len(entries):
            index = int(raw) - 1
            return index, entries[index]
        print(f"  {_color(f'Please enter a number between 1 and {len(entries)}, or r.', RED)}")


def _pick_file_interactively() -> Path:
    """Scan the current directory for eval result files and prompt the user to pick one."""
    candidates = sorted(Path(".").glob("eval_results*.json"))

    if not candidates:
        print(f"{_color('Error:', RED)} No eval_results*.json files found in the current directory.", file=sys.stderr)
        sys.exit(1)

    if len(candidates) == 1:
        print(f"Using {_color(str(candidates[0]), CYAN)}\n")
        return candidates[0]

    print(_color("Available result files:", BOLD))
    for i, path in enumerate(candidates):
        print(f"  {_color(str(i + 1), CYAN)}  {path}")

    print()
    while True:
        raw = input(f"Select a file {_color(f'[1–{len(candidates)}]', DIM)}: ").strip()
        if raw.isdigit() and 1 <= int(raw) <= len(candidates):
            return candidates[int(raw) - 1]
        print(f"  {_color('Please enter a number between 1 and ' + str(len(candidates)), RED)}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Randomly inspect entries from eval result files",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--file", "-f",
        default=None,
        metavar="PATH",
        help="Path to the eval results JSON file. If omitted, an interactive "
             "prompt lists all eval_results*.json files in the current directory.",
    )
    parser.add_argument(
        "--trial", "-t",
        type=int,
        default=None,
        metavar="N",
        help="Shortcut to select eval_results_N.json directly (e.g. --trial 2).",
    )
    parser.add_argument(
        "--index", "-i",
        type=int,
        default=None,
        metavar="N",
        help="Pick a specific entry by zero-based index instead of random",
    )
    parser.add_argument(
        "--status", "-s",
        default=None,
        choices=["success", "candidate_error", "judge_error"],
        help="Filter to entries with this status before picking",
    )
    parser.add_argument(
        "--verdict", "-v",
        default=None,
        choices=["correct", "incorrect"],
        help="Filter to entries with this judge verdict before picking",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    # Resolve which file to open
    if args.trial is not None:
        path = Path(f"eval_results_{args.trial}.json")
    elif args.file:
        path = Path(args.file)
    else:
        path = _pick_file_interactively()

    if not path.exists():
        print(f"{_color('Error:', RED)} File not found: {path.resolve()}", file=sys.stderr)
        return 1

    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)

    results: list[dict] = data.get("results", data) if isinstance(data, dict) else data

    if not results:
        print(f"{_color('Error:', RED)} No results found in {path}.", file=sys.stderr)
        return 1

    # Apply filters
    filtered = results

    if args.status:
        filtered = [r for r in filtered if r.get("status") == args.status]
        if not filtered:
            print(f"{_color('Error:', RED)} No entries with status='{args.status}'.", file=sys.stderr)
            return 1

    if args.verdict:
        filtered = [
            r for r in filtered
            if r.get("judge") and r["judge"].get("verdict") == args.verdict
        ]
        if not filtered:
            print(f"{_color('Error:', RED)} No entries with verdict='{args.verdict}'.", file=sys.stderr)
            return 1

    # Select entry
    if args.index is not None:
        if args.index >= len(filtered):
            print(
                f"{_color('Error:', RED)} Index {args.index} out of range "
                f"(0–{len(filtered) - 1}).",
                file=sys.stderr,
            )
            return 1
        entry = filtered[args.index]
        index = args.index
    else:
        index, entry = _pick_entry_interactively(filtered)

    display_entry(entry, index, len(filtered))
    return 0


if __name__ == "__main__":
    sys.exit(main())
