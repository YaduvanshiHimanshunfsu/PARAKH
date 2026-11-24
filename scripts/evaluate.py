"""Measure PARAKH's detection accuracy on the golden dataset (planversionalpha.md Phase A).

Runs every golden item through the same code the API uses, fully offline:

* messages   -> RuleBasedFallbackAnalyzer (the engine used when no AI key is set)
* URLs       -> UrlIntelligenceService (TLS probe and reputation lookups off)
* identifiers-> extract_identifiers
* websites   -> WebsiteAnalyzer.analyze_page on saved HTML (no fetching)
* APKs       -> ApkAnalyzer on synthetic packages built from eval/golden/apks.json

    python scripts/evaluate.py                    # writes eval/report.md + eval/report.json
    python scripts/evaluate.py --write-baseline   # also records eval/baseline.json for the CI gate

The split is deterministic (30% test by hash of the item id). Tune rules on
`dev` only; quote numbers from `test` only.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

GOLDEN = ROOT / "eval" / "golden"
OUT_DIR = ROOT / "eval"
LABELS = ("SCAM", "SUSPICIOUS", "SAFE")

# Phase B target metrics (reported, not enforced until Phase B lands).
TARGETS = {
    "messages.macro_f1": 0.85,
    "messages.scam_precision": 0.92,
    "messages.risky_recall_hi_hinglish": 0.85,
    "urls.official_false_positives": 0,
    "identifiers.micro_f1": 0.90,
}

# Metrics the CI gate protects against regression (higher is better unless noted).
GATED = (
    "messages.macro_f1",
    "messages.risky_recall",
    "messages.safe_specificity",
    "urls.phishing_recall",
    "urls.official_false_positives",  # lower is better
    "identifiers.micro_f1",
    "websites.accuracy",
    "apks.accuracy",
)
LOWER_IS_BETTER = {"urls.official_false_positives"}


def split_of(item_id: str) -> str:
    return "test" if hashlib.sha256(item_id.encode()).digest()[0] % 10 < 3 else "dev"


def load_jsonl(*names: str) -> list[dict]:
    rows: list[dict] = []
    for name in names:
        for line in (GOLDEN / name).read_text(encoding="utf-8").splitlines():
            if line.strip():
                rows.append(json.loads(line))
    return rows


def prf(tp: int, fp: int, fn: int) -> dict:
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {"precision": round(precision, 3), "recall": round(recall, 3), "f1": round(f1, 3), "support": tp + fn}


def settings():
    from app.config import Settings

    return Settings(
        _env_file=None,
        gemini_api_key=None,
        web_risk_api_key=None,
        virustotal_api_key=None,
        url_tls_probe_enabled=False,
        domain_age_enabled=False,
        redirect_following_enabled=False,
    )


# --- messages -----------------------------------------------------------------


def evaluate_messages(rows: list[dict]) -> dict:
    from app.services.fallback_analyzer import RuleBasedFallbackAnalyzer

    engine = RuleBasedFallbackAnalyzer()
    confusion = {truth: Counter() for truth in LABELS}
    by_lang = defaultdict(lambda: Counter())
    by_category = defaultdict(lambda: Counter())
    category_match = Counter()
    misses: list[dict] = []
    false_alarms: list[dict] = []

    for row in rows:
        result = engine.analyze(row["text"])
        predicted = result.verdict.value
        truth = row["label"]
        confusion[truth][predicted] += 1
        risky_truth = truth != "SAFE"
        risky_pred = predicted != "SAFE"
        by_lang[row["lang"]]["n"] += 1
        by_lang[row["lang"]]["risky"] += risky_truth
        by_lang[row["lang"]]["caught"] += risky_truth and risky_pred
        by_lang[row["lang"]]["safe"] += not risky_truth
        by_lang[row["lang"]]["false_alarm"] += (not risky_truth) and risky_pred
        by_category[row["category"]]["n"] += 1
        by_category[row["category"]]["correct"] += (risky_pred == risky_truth)
        if truth == "SCAM":
            category_match["n"] += 1
            category_match["hit"] += result.scam_category.value == row["category"]
        if risky_truth and not risky_pred:
            misses.append({"id": row["id"], "lang": row["lang"], "category": row["category"], "text": row["text"][:120]})
        if not risky_truth and risky_pred:
            false_alarms.append({"id": row["id"], "lang": row["lang"], "predicted": predicted, "text": row["text"][:120]})

    per_class = {}
    for label in LABELS:
        tp = confusion[label][label]
        fp = sum(confusion[other][label] for other in LABELS if other != label)
        fn = sum(confusion[label][other] for other in LABELS if other != label)
        per_class[label] = prf(tp, fp, fn)
    macro_f1 = round(sum(per_class[label]["f1"] for label in LABELS) / len(LABELS), 3)

    risky_tp = sum(confusion[t][p] for t in ("SCAM", "SUSPICIOUS") for p in ("SCAM", "SUSPICIOUS"))
    risky_fn = sum(confusion[t]["SAFE"] for t in ("SCAM", "SUSPICIOUS"))
    safe_total = sum(confusion["SAFE"].values())
    safe_ok = confusion["SAFE"]["SAFE"]
    hi = [by_lang[lang] for lang in ("hi", "hinglish")]
    hi_risky = sum(item["risky"] for item in hi)
    hi_caught = sum(item["caught"] for item in hi)

    return {
        "n": len(rows),
        "confusion": {truth: dict(confusion[truth]) for truth in LABELS},
        "per_class": per_class,
        "macro_f1": macro_f1,
        "scam_precision": per_class["SCAM"]["precision"],
        "risky_recall": round(risky_tp / (risky_tp + risky_fn), 3) if risky_tp + risky_fn else 0.0,
        "safe_specificity": round(safe_ok / safe_total, 3) if safe_total else 0.0,
        "risky_recall_hi_hinglish": round(hi_caught / hi_risky, 3) if hi_risky else 0.0,
        "by_language": {
            lang: {
                "n": c["n"],
                "risky_recall": round(c["caught"] / c["risky"], 3) if c["risky"] else None,
                "false_alarm_rate": round(c["false_alarm"] / c["safe"], 3) if c["safe"] else None,
            }
            for lang, c in sorted(by_lang.items())
        },
        "by_category": {cat: {"n": c["n"], "accuracy": round(c["correct"] / c["n"], 3)} for cat, c in sorted(by_category.items())},
        "category_match_on_scams": round(category_match["hit"] / category_match["n"], 3) if category_match["n"] else None,
        "misses": misses,
        "false_alarms": false_alarms,
    }


# --- URLs -----------------------------------------------------------------------


def evaluate_urls(rows: list[dict]) -> dict:
    from app.services.url_intelligence import UrlIntelligenceService

    service = UrlIntelligenceService(settings())

    async def run():
        return await asyncio.gather(*(service.analyze_url(row["url"]) for row in rows))

    results = asyncio.run(run())
    official_fp: list[dict] = []
    phishing_missed: list[dict] = []
    tp = fp = fn = tn = 0
    for row, result in zip(rows, results):
        risky = result.risk_level.value in {"MEDIUM", "HIGH", "CRITICAL"}
        codes = [signal.code for signal in result.signals]
        if row["label"] == "SAFE":
            if risky or "BRAND_LIKE_DOMAIN" in codes:
                fp += 1
                official_fp.append({"id": row["id"], "url": row["url"], "risk": result.risk_level.value, "signals": codes})
            else:
                tn += 1
        else:
            if risky:
                tp += 1
            else:
                fn += 1
                phishing_missed.append({"id": row["id"], "url": row["url"], "kind": row["kind"], "risk": result.risk_level.value, "signals": codes})
    return {
        "n": len(rows),
        "phishing_recall": round(tp / (tp + fn), 3) if tp + fn else 0.0,
        "precision": round(tp / (tp + fp), 3) if tp + fp else 0.0,
        "official_false_positives": fp,
        "official_total": fp + tn,
        "official_fp_list": official_fp,
        "phishing_missed": phishing_missed,
    }


# --- identifiers ---------------------------------------------------------------


def evaluate_identifiers(rows: list[dict]) -> dict:
    from app.services.identifier_extractor import extract_identifiers

    per_type = defaultdict(Counter)
    mistakes: list[dict] = []
    for row in rows:
        expected = {(item["type"], item["value"]) for item in row["expected"]}
        found = {(item.type.value, item.value) for item in extract_identifiers(row["text"], include_context=False)}
        for pair in expected & found:
            per_type[pair[0]]["tp"] += 1
        for pair in found - expected:
            per_type[pair[0]]["fp"] += 1
        for pair in expected - found:
            per_type[pair[0]]["fn"] += 1
        if expected != found:
            mistakes.append({
                "id": row["id"],
                "missing": sorted(f"{t}:{v}" for t, v in expected - found),
                "extra": sorted(f"{t}:{v}" for t, v in found - expected),
            })
    totals = Counter()
    for counts in per_type.values():
        totals.update(counts)
    micro = prf(totals["tp"], totals["fp"], totals["fn"])
    return {
        "n": len(rows),
        "micro_f1": micro["f1"],
        "micro_precision": micro["precision"],
        "micro_recall": micro["recall"],
        "per_type": {t: prf(c["tp"], c["fp"], c["fn"]) for t, c in sorted(per_type.items())},
        "mistakes": mistakes,
    }


# --- websites -------------------------------------------------------------------


def evaluate_websites(rows: list[dict]) -> dict:
    from app.services.website_analyzer import WebsiteAnalyzer

    analyzer = WebsiteAnalyzer(settings())
    wrong: list[dict] = []
    correct = 0
    for row in rows:
        page = analyzer._build_page(row["url"], row["url"], 200, "text/html", row["html"].encode("utf-8"), [row["url"]], False)
        bundle = analyzer.analyze_page(page)
        risky = bundle.risk_level.value in {"MEDIUM", "HIGH"}
        ok = risky == (row["label"] != "SAFE")
        correct += ok
        if not ok:
            wrong.append({"id": row["id"], "label": row["label"], "risk": bundle.risk_level.value, "score": bundle.risk_score,
                          "findings": [finding.code for finding in bundle.findings][:8]})
    return {"n": len(rows), "accuracy": round(correct / len(rows), 3) if rows else 0.0, "wrong": wrong}


# --- APKs -----------------------------------------------------------------------


def evaluate_apks(specs: list[dict]) -> dict:
    from app.services.apk_analyzer import ApkAnalyzer
    from tests.apk_fixtures import build_apk

    analyzer = ApkAnalyzer()
    wrong: list[dict] = []
    benign_high = 0
    correct = 0
    for spec in specs:
        data = build_apk(
            package=spec["package"],
            label=spec["app_label"],
            permissions=tuple(f"android.permission.{p}" for p in spec["permissions"]),
            target_sdk=spec["target_sdk"],
            dex_strings=tuple(spec["dex_strings"]),
        )
        bundle = analyzer.analyze(data, f"{spec['id']}.apk")
        level = bundle.risk_level.value
        if spec["label"] == "SAFE":
            ok = level != "HIGH"
            benign_high += level == "HIGH"
        else:
            ok = level == "HIGH"
        correct += ok
        if not ok:
            wrong.append({"id": spec["id"], "label": spec["label"], "risk": level, "score": bundle.risk_score,
                          "findings": [finding.code for finding in bundle.findings][:8]})
    return {"n": len(specs), "accuracy": round(correct / len(specs), 3) if specs else 0.0, "benign_flagged_high": benign_high, "wrong": wrong}


# --- report ---------------------------------------------------------------------


def run(split: str) -> dict:
    def pick(rows):
        return rows if split == "all" else [row for row in rows if split_of(row["id"]) == split]

    messages = pick(load_jsonl("messages_scam.jsonl", "messages_safe.jsonl"))
    urls = pick(load_jsonl("urls.jsonl"))
    identifiers = pick(load_jsonl("identifiers.jsonl"))
    websites = pick(load_jsonl("websites.jsonl"))
    apks = pick(json.loads((GOLDEN / "apks.json").read_text(encoding="utf-8"))["apks"])
    return {
        "split": split,
        "messages": evaluate_messages(messages),
        "urls": evaluate_urls(urls),
        "identifiers": evaluate_identifiers(identifiers),
        "websites": evaluate_websites(websites),
        "apks": evaluate_apks(apks),
    }


def metric(report: dict, dotted: str):
    section, key = dotted.split(".", 1)
    return report[section][key]


def render_markdown(reports: dict) -> str:
    test, full = reports["test"], reports["all"]
    lines = [
        "# PARAKH evaluation report",
        "",
        f"Generated {reports['generated_at']} by `scripts/evaluate.py`. Offline: rule engine only, no AI key, no network.",
        "",
        "> The golden set is team-written synthetic data modelled on public police and CERT-In advisory patterns. "
        "Add real R4C / cyber-cell samples before quoting these numbers externally.",
        "",
        "## Headline (test split)",
        "",
        "| Metric | Value | Phase B target |",
        "|---|---|---|",
    ]
    for key in (
        "messages.macro_f1",
        "messages.scam_precision",
        "messages.risky_recall",
        "messages.safe_specificity",
        "messages.risky_recall_hi_hinglish",
        "urls.phishing_recall",
        "urls.official_false_positives",
        "identifiers.micro_f1",
        "websites.accuracy",
        "apks.accuracy",
    ):
        target = TARGETS.get(key, "")
        lines.append(f"| `{key}` | {metric(test, key)} | {target} |")
    lines += [
        "",
        f"Split sizes (test): messages {test['messages']['n']}, URLs {test['urls']['n']}, identifiers {test['identifiers']['n']}, "
        f"websites {test['websites']['n']}, APKs {test['apks']['n']}.",
        "",
        "## Messages (all items)",
        "",
        "Confusion matrix (rows = truth, columns = predicted):",
        "",
        "| truth \\ predicted | SCAM | SUSPICIOUS | SAFE |",
        "|---|---|---|---|",
    ]
    for truth in LABELS:
        row = full["messages"]["confusion"][truth]
        lines.append(f"| {truth} | {row.get('SCAM', 0)} | {row.get('SUSPICIOUS', 0)} | {row.get('SAFE', 0)} |")
    lines += ["", "| Language | n | risky recall | false-alarm rate |", "|---|---|---|---|"]
    for lang, values in full["messages"]["by_language"].items():
        lines.append(f"| {lang} | {values['n']} | {values['risky_recall']} | {values['false_alarm_rate']} |")
    lines += ["", "| Category | n | accuracy (risky vs safe) |", "|---|---|---|"]
    for category, values in full["messages"]["by_category"].items():
        lines.append(f"| {category} | {values['n']} | {values['accuracy']} |")
    lines += [
        "",
        f"Category label match on SCAM items: {full['messages']['category_match_on_scams']}",
        "",
        f"### Missed scams ({len(full['messages']['misses'])})",
        "",
    ]
    lines += [f"- `{m['id']}` [{m['lang']}, {m['category']}] {m['text']}" for m in full["messages"]["misses"][:40]]
    lines += ["", f"### False alarms on safe messages ({len(full['messages']['false_alarms'])})", ""]
    lines += [f"- `{m['id']}` [{m['lang']}] → {m['predicted']}: {m['text']}" for m in full["messages"]["false_alarms"][:40]]
    lines += [
        "",
        "## URLs (all items)",
        "",
        f"Phishing recall {full['urls']['phishing_recall']}, precision {full['urls']['precision']}, "
        f"official false positives {full['urls']['official_false_positives']} / {full['urls']['official_total']}.",
        "",
        "Official or legitimate sites flagged:",
        "",
    ]
    lines += [f"- `{u['url']}` → {u['risk']} {u['signals']}" for u in full["urls"]["official_fp_list"]]
    lines += ["", "Phishing URLs missed:", ""]
    lines += [f"- `{u['url']}` ({u['kind']}) → {u['risk']} {u['signals']}" for u in full["urls"]["phishing_missed"]]
    lines += ["", "## Identifiers (all items)", "", "| Type | precision | recall | F1 | support |", "|---|---|---|---|---|"]
    for type_name, values in full["identifiers"]["per_type"].items():
        lines.append(f"| {type_name} | {values['precision']} | {values['recall']} | {values['f1']} | {values['support']} |")
    lines += ["", "Mismatches:", ""]
    lines += [f"- `{m['id']}` missing {m['missing']} extra {m['extra']}" for m in full["identifiers"]["mistakes"]]
    lines += ["", "## Websites (all items)", "", f"Accuracy {full['websites']['accuracy']}.", ""]
    lines += [f"- `{w['id']}` {w['label']} → {w['risk']} ({w['score']}) {w['findings']}" for w in full["websites"]["wrong"]]
    lines += [
        "",
        "## APKs (all items, synthetic)",
        "",
        f"Accuracy {full['apks']['accuracy']}; benign apps flagged HIGH: {full['apks']['benign_flagged_high']}.",
        "",
    ]
    lines += [f"- `{a['id']}` {a['label']} → {a['risk']} ({a['score']}) {a['findings']}" for a in full["apks"]["wrong"]]
    return "\n".join(lines) + "\n"


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write-baseline", action="store_true", help="record eval/baseline.json from the test split")
    args = parser.parse_args(argv)

    reports = {"generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")}
    for split in ("test", "dev", "all"):
        reports[split] = run(split)
    (OUT_DIR / "report.json").write_text(json.dumps(reports, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (OUT_DIR / "report.md").write_text(render_markdown(reports), encoding="utf-8")

    if args.write_baseline:
        baseline = {key: metric(reports["test"], key) for key in GATED}
        (OUT_DIR / "baseline.json").write_text(json.dumps({"recorded_at": reports["generated_at"], "metrics": baseline}, indent=2) + "\n", encoding="utf-8")

    test = reports["test"]
    print("test split:", ", ".join(f"{key}={metric(test, key)}" for key in GATED))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
