"""CI gate on the golden dataset (planversionalpha.md Phase A.2).

Re-runs the offline evaluation on the test split and fails if any protected
metric is worse than eval/baseline.json (tolerance 0.02; the official-domain
false-positive count may not increase at all). After an intentional
improvement, record a new baseline:

    python scripts/evaluate.py --write-baseline
"""

import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("evaluate", ROOT / "scripts" / "evaluate.py")
evaluate = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(evaluate)

BASELINE = json.loads((ROOT / "eval" / "baseline.json").read_text(encoding="utf-8"))["metrics"]
TOLERANCE = 0.02


@pytest.fixture(scope="module")
def test_report() -> dict:
    return evaluate.run("test")


@pytest.mark.parametrize("key", evaluate.GATED)
def test_metric_does_not_regress(test_report, key: str) -> None:
    current = evaluate.metric(test_report, key)
    recorded = BASELINE[key]
    if key in evaluate.LOWER_IS_BETTER:
        assert current <= recorded, f"{key} rose from {recorded} to {current}"
    else:
        assert current >= recorded - TOLERANCE, f"{key} fell from {recorded} to {current}"


def test_split_is_deterministic_and_roughly_thirty_percent() -> None:
    ids = [f"m{i:03d}" for i in range(1, 301)]
    first = [evaluate.split_of(i) for i in ids]
    assert first == [evaluate.split_of(i) for i in ids]
    share = first.count("test") / len(first)
    assert 0.2 < share < 0.4


def test_golden_set_meets_minimum_sizes() -> None:
    messages = evaluate.load_jsonl("messages_scam.jsonl", "messages_safe.jsonl")
    assert len(messages) >= 300
    assert sum(row["label"] == "SAFE" for row in messages) / len(messages) >= 0.40  # hard negatives
    assert len(evaluate.load_jsonl("urls.jsonl")) >= 120
    assert len(evaluate.load_jsonl("identifiers.jsonl")) >= 80
    assert len(evaluate.load_jsonl("websites.jsonl")) >= 30
    ids = [row["id"] for row in messages]
    assert len(ids) == len(set(ids)), "duplicate message ids"
