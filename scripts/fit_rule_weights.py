from __future__ import annotations

"""Fit rule weights and verdict thresholds on the DEV split (planversionalpha.md B.2).

Offline, development-time only. The result is written to
``app/data/rule_weights.json`` as data and committed with the evaluation
report; the running service never fits anything.

Method
------
L2-regularised logistic regression, fitted with plain gradient descent (about
40 lines, no scikit-learn / numpy dependency), over the binary "rule k fired"
matrix plus one structural-URL-risk feature.

Constraints that keep the model explainable and safe:

* a fraud rule's weight is clipped to ``>= 0`` so it can never *lower*
  suspicion, and a guard's to ``<= 0`` so it can never raise it;
* weights stay within ``[-4, 4.5]`` so no single rule can decide a verdict on
  its own, except where the hand-set prior already says it should;
* the hand-set prior is used as the starting point and pulled toward, so a
  rule the dev split happens not to exercise keeps its reviewed weight.

Usage::

    python scripts/fit_rule_weights.py            # report only
    python scripts/fit_rule_weights.py --write    # update app/data/rule_weights.json
"""

import argparse
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.data.scam_rules import SCAM_SIGNAL_RULES  # noqa: E402
from app.services.fallback_analyzer import (  # noqa: E402
    BIAS,
    GUARD_CAP_RATIO,
    MAX_URLS,
    RuleBasedFallbackAnalyzer,
    probability,
)
from app.services.url_intelligence import UrlIntelligenceService, static_url_risk  # noqa: E402

GOLDEN = ROOT / "eval" / "golden"
OUTPUT = ROOT / "app" / "data" / "rule_weights.json"

LEARNING_RATE = 0.4
EPOCHS = 600
L2 = 0.003
PRIOR_PULL = 0.015  # keeps an unexercised rule near its reviewed weight
WEIGHT_MIN, WEIGHT_MAX = 0.0, 4.5
GUARD_MIN, GUARD_MAX = -4.0, 0.0


def split_of(item_id: str) -> str:
    import hashlib

    return "test" if hashlib.sha256(item_id.encode()).digest()[0] % 10 < 3 else "dev"


def load_rows() -> list[dict]:
    rows: list[dict] = []
    for name in ("messages_scam.jsonl", "messages_safe.jsonl"):
        for line in (GOLDEN / name).read_text(encoding="utf-8").splitlines():
            if line.strip():
                rows.append(json.loads(line))
    return rows


def url_feature(message: str) -> float:
    """Same structural-URL term the engine uses, as a model feature."""

    risks = [static_url_risk(url) for url in UrlIntelligenceService.extract_urls(message)[:MAX_URLS]]
    if not risks:
        return 0.0
    worst = max(risks, key=lambda item: item.score)
    if worst.is_official and worst.score == 0:
        return -0.4
    return min(3.0, worst.score / 34.0)


def build_matrix(rows: list[dict]) -> tuple[list[dict[str, float]], list[int], list[float]]:
    engine = RuleBasedFallbackAnalyzer()
    features: list[dict[str, float]] = []
    labels: list[int] = []
    url_terms: list[float] = []
    for row in rows:
        hits = engine._apply_caps(engine.hits(row["text"]))
        features.append({hit.rule.rule_id: 1.0 for hit in hits if hit.counted})
        labels.append(0 if row["label"] == "SAFE" else 1)
        url_terms.append(url_feature(row["text"]))
    return features, labels, url_terms


def score_of(row, url_term: float, weights: dict[str, float]) -> float:
    """The engine's score, including the guard cap, so the fit matches runtime."""

    positive = sum(w for w in (weights.get(key, 0.0) for key in row) if w > 0)
    negative = sum(w for w in (weights.get(key, 0.0) for key in row) if w < 0)
    return BIAS + url_term + positive + max(negative, -GUARD_CAP_RATIO * positive)


def fit(features, labels, url_terms, priors: dict[str, float]) -> dict[str, float]:
    weights = dict(priors)
    n = len(labels)
    for _ in range(EPOCHS):
        gradients: dict[str, float] = {key: 0.0 for key in weights}
        for row, label, url_term in zip(features, labels, url_terms):
            error = probability(score_of(row, url_term, weights)) - label
            for key in row:
                gradients[key] += error
        for key, gradient in gradients.items():
            prior = priors[key]
            step = gradient / n + L2 * weights[key] + PRIOR_PULL * (weights[key] - prior)
            value = weights[key] - LEARNING_RATE * step
            low, high = (GUARD_MIN, GUARD_MAX) if prior < 0 else (WEIGHT_MIN, WEIGHT_MAX)
            weights[key] = max(low, min(high, value))
    return {key: round(value, 3) for key, value in weights.items()}


def probabilities(features, url_terms, weights) -> list[float]:
    return [probability(score_of(row, url_term, weights)) for row, url_term in zip(features, url_terms)]


def pick_thresholds(probs: list[float], rows: list[dict]) -> tuple[float, float, dict]:
    """T_scam: the lowest threshold whose SCAM precision is >= 0.92.

    T_suspicious: the threshold that maximises 3-class macro F1 beneath it.
    """

    truths = [row["label"] for row in rows]
    grid = [round(0.02 * i, 2) for i in range(5, 50)]

    best_scam = 0.9
    for threshold in grid:
        predicted = [p >= threshold for p in probs]
        tp = sum(1 for p, t in zip(predicted, truths) if p and t == "SCAM")
        fp = sum(1 for p, t in zip(predicted, truths) if p and t != "SCAM")
        if tp + fp < 5:
            continue
        if tp / (tp + fp) >= 0.92:
            best_scam = threshold
            break

    def macro_f1(t_scam: float, t_susp: float) -> float:
        labels = ("SCAM", "SUSPICIOUS", "SAFE")
        predicted = ["SCAM" if p >= t_scam else "SUSPICIOUS" if p >= t_susp else "SAFE" for p in probs]
        total = 0.0
        for label in labels:
            tp = sum(1 for p, t in zip(predicted, truths) if p == label and t == label)
            fp = sum(1 for p, t in zip(predicted, truths) if p == label and t != label)
            fn = sum(1 for p, t in zip(predicted, truths) if p != label and t == label)
            precision = tp / (tp + fp) if tp + fp else 0.0
            recall = tp / (tp + fn) if tp + fn else 0.0
            total += 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        return total / len(labels)

    best_susp, best_score = 0.26, -1.0
    for threshold in grid:
        if threshold >= best_scam:
            break
        score = macro_f1(best_scam, threshold)
        if score > best_score:
            best_susp, best_score = threshold, score

    predicted = ["SCAM" if p >= best_scam else "SUSPICIOUS" if p >= best_susp else "SAFE" for p in probs]
    stats = {
        "dev_macro_f1": round(best_score, 3),
        "dev_scam_precision": round(
            sum(1 for p, t in zip(predicted, truths) if p == "SCAM" and t == "SCAM")
            / max(1, sum(1 for p in predicted if p == "SCAM")),
            3,
        ),
        "dev_risky_recall": round(
            sum(1 for p, t in zip(predicted, truths) if p != "SAFE" and t != "SAFE")
            / max(1, sum(1 for t in truths if t != "SAFE")),
            3,
        ),
        "dev_safe_specificity": round(
            sum(1 for p, t in zip(predicted, truths) if p == "SAFE" and t == "SAFE")
            / max(1, sum(1 for t in truths if t == "SAFE")),
            3,
        ),
    }
    return best_scam, best_susp, stats


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="write app/data/rule_weights.json")
    args = parser.parse_args(argv)

    rows = [row for row in load_rows() if split_of(row["id"]) == "dev"]
    print(f"dev items: {len(rows)}")
    features, labels, url_terms = build_matrix(rows)
    priors = {rule.rule_id: rule.weight for rule in SCAM_SIGNAL_RULES}
    weights = fit(features, labels, url_terms, priors)
    probs = probabilities(features, url_terms, weights)
    t_scam, t_susp, stats = pick_thresholds(probs, rows)

    print(f"T_scam={t_scam}  T_suspicious={t_susp}")
    for key, value in stats.items():
        print(f"  {key}: {value}")
    moved = sorted(
        ((abs(weights[k] - priors[k]), k) for k in priors if abs(weights[k] - priors[k]) >= 0.3), reverse=True
    )
    print(f"rules moved by >= 0.3: {len(moved)}")
    for delta, key in moved[:12]:
        print(f"  {key:22s} {priors[key]:+.2f} -> {weights[key]:+.2f}  ({delta:.2f})")

    if args.write:
        payload = {
            "fitted_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "method": "L2 logistic regression (gradient descent) on the dev split; see scripts/fit_rule_weights.py",
            "dev_items": len(rows),
            "bias": BIAS,
            "t_scam": t_scam,
            "t_suspicious": t_susp,
            "dev_metrics": stats,
            "weights": weights,
        }
        OUTPUT.write_text(json.dumps(payload, indent=2, sort_keys=False) + "\n", encoding="utf-8")
        print(f"wrote {OUTPUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
