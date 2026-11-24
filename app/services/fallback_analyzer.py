from __future__ import annotations

"""Offline rule engine v2 (planversionalpha.md B.2).

Replaces the old "add integer points, score >= 55 is a scam" approach with
**log-odds evidence combination**, which stays fully explainable:

    logit = bias + Σ w_k · x_k        (x_k = 1 if rule k fired, after de-duplication)
    p(scam) = 1 / (1 + e^-logit)

Three rules keep the arithmetic honest:

* **Tactic de-duplication** — rules sharing a ``tactic_group`` contribute once
  (the strongest), so "urgent + immediately + today only" cannot stack.
* **Category cap** — at most two rules per scam category count.
* **Guards** — negative-weight rules for legitimate structures (a real bank
  debit alert, an official "never share your OTP" advisory) pull the logit down.

Every counted rule is returned as ``RuleEvidence`` with its contribution, so a
report can cite exactly which reviewed rule fired and by how much.

The engine is deterministic, needs no network and no AI provider.
"""

import json
import math
from collections import defaultdict
from pathlib import Path

from app.data.scam_rules import DEFAULT_ACTIONS, GENERIC_ACTIONS, SCAM_SIGNAL_RULES, ScamSignalRule
from app.schemas import (
    AnalysisResponse,
    AnalysisSource,
    PsychologicalTactic,
    RedFlag,
    RuleEvidence,
    ScamCategory,
    Severity,
    Verdict,
)
from app.services.url_intelligence import UrlIntelligenceService, static_url_risk
from app.utils.text_normalise import NormalisedText, normalise

# Prior odds of an arbitrary message being a scam. Negative: most messages are
# ordinary. Held fixed; the rule weights are fitted around it.
BIAS = -3.4

# p(scam) thresholds. Defaults are the reviewed hand-set values; the fitted
# file below replaces them with the values chosen on the dev split (the lowest
# T_SCAM whose dev SCAM precision is >= 0.92).
T_SCAM = 0.62
T_SUSPICIOUS = 0.26

MAX_RULES_PER_CATEGORY = 2

# A guard can cancel at most this share of the positive evidence.
GUARD_CAP_RATIO = 0.6
MAX_URLS = 5

_WEIGHTS_FILE = Path(__file__).resolve().parent.parent / "data" / "rule_weights.json"


# Weights and thresholds fitted by scripts/fit_rule_weights.py on the dev
# split and committed as data. Missing file: the reviewed defaults above are
# used, so the engine still works in a fresh checkout.
def _load_fitted() -> dict:
    try:
        return json.loads(_WEIGHTS_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


_FITTED = _load_fitted()
WEIGHT_OVERRIDES: dict[str, float] = {
    str(key): float(value)
    for key, value in (_FITTED.get("weights") or {}).items()
    if isinstance(value, (int, float))
}
if isinstance(_FITTED.get("t_scam"), (int, float)):
    T_SCAM = float(_FITTED["t_scam"])
if isinstance(_FITTED.get("t_suspicious"), (int, float)):
    T_SUSPICIOUS = float(_FITTED["t_suspicious"])
FITTED_AT: str | None = _FITTED.get("fitted_at")


def weight_of(rule: ScamSignalRule) -> float:
    return WEIGHT_OVERRIDES.get(rule.rule_id, rule.weight)


def probability(logit: float) -> float:
    return 1.0 / (1.0 + math.exp(-max(-30.0, min(30.0, logit))))


class _Hit:
    __slots__ = ("rule", "phrase", "weight", "counted")

    def __init__(self, rule: ScamSignalRule, phrase: str, weight: float) -> None:
        self.rule = rule
        self.phrase = phrase
        self.weight = weight
        self.counted = True


class RuleBasedFallbackAnalyzer:
    """A transparent offline engine used when no AI provider is available.

    It does not claim that a real-world sender is a criminal. It reports which
    reviewed patterns are present in the text and how strongly they point to
    fraud.
    """

    def __init__(self, rules: tuple[ScamSignalRule, ...] = SCAM_SIGNAL_RULES) -> None:
        self._rules = rules

    # -- matching -----------------------------------------------------------

    def _match(self, rule: ScamSignalRule, view: NormalisedText) -> str | None:
        """First match of any language variant, as the original text."""

        for pattern in rule.compiled:
            match = pattern.search(view.text)
            if match and match.end() > match.start():
                phrase = view.original_phrase(match.start(), match.end()).strip()
                return phrase[:160] if phrase else None
        return None

    def hits(self, message: str) -> list[_Hit]:
        view = normalise(message)
        found: list[_Hit] = []
        for rule in self._rules:
            phrase = self._match(rule, view)
            if phrase:
                found.append(_Hit(rule, phrase, weight_of(rule)))
        return found

    @staticmethod
    def _apply_caps(hits: list[_Hit]) -> list[_Hit]:
        """Tactic de-duplication and per-category caps; marks hits not counted."""

        # Strongest hit per tactic group wins; the rest stay as evidence but
        # do not add to the score.
        by_group: dict[str, _Hit] = {}
        for hit in hits:
            group = hit.rule.tactic_group
            if group is None:
                continue
            current = by_group.get(group)
            if current is None or abs(hit.weight) > abs(current.weight):
                by_group[group] = hit
        for hit in hits:
            if hit.rule.tactic_group and by_group.get(hit.rule.tactic_group) is not hit:
                hit.counted = False

        per_category: dict[ScamCategory, int] = defaultdict(int)
        for hit in hits:
            if not hit.counted or hit.rule.is_guard:
                continue
            category = hit.rule.category
            if category is ScamCategory.UNKNOWN:
                continue
            per_category[category] += 1
            if per_category[category] > MAX_RULES_PER_CATEGORY:
                hit.counted = False
        return hits

    # -- scoring ------------------------------------------------------------

    def score(self, message: str) -> tuple[float, list[_Hit], list[object]]:
        hits = self._apply_caps(self.hits(message))
        positive = sum(hit.weight for hit in hits if hit.counted and hit.weight > 0)
        negative = sum(hit.weight for hit in hits if hit.counted and hit.weight < 0)
        # A guard may reduce the evidence, never erase it: an awareness
        # advisory has little positive evidence, so the full guard applies,
        # while a scam that happens to contain advisory-like wording ("do not
        # disconnect the call") keeps most of its score.
        logit = BIAS + positive + max(negative, -GUARD_CAP_RATIO * positive)

        url_risks = []
        for raw in UrlIntelligenceService.extract_urls(message)[:MAX_URLS]:
            risk = static_url_risk(raw)
            url_risks.append(risk)
        if url_risks:
            worst = max(url_risks, key=lambda item: item.score)
            if worst.is_official and worst.score == 0:
                # A link to a genuine official site is mild evidence *against*
                # a phishing attempt, though the text can still be a scam.
                logit -= 0.4
            else:
                # Structural URL risk, scaled into log-odds. 54/100
                # (sbi-verify-kyc.in) contributes about +1.6.
                logit += min(3.0, worst.score / 34.0)
        return logit, hits, url_risks

    # -- public API ---------------------------------------------------------

    def analyze(self, message: str) -> AnalysisResponse:
        logit, hits, url_risks = self.score(message)
        p = probability(logit)

        if p >= T_SCAM:
            verdict, severity = Verdict.SCAM, Severity.HIGH
        elif p >= T_SUSPICIOUS:
            verdict, severity = Verdict.SUSPICIOUS, Severity.MEDIUM
        else:
            verdict, severity = Verdict.SAFE, Severity.LOW

        counted = [hit for hit in hits if hit.counted and not hit.rule.is_guard]
        category = self._category(counted, url_risks)
        tactics = self._tactics(counted)
        flags = self._red_flags(hits, url_risks, verdict)
        actions = self._actions(counted, category, verdict)
        hindi = self._hindi(counted, verdict)

        confidence = int(round(100 * (p if verdict is not Verdict.SAFE else 1 - p)))
        confidence = max(55, min(96, confidence))

        return AnalysisResponse(
            verdict=verdict,
            confidence=confidence,
            scam_category=category,
            severity=severity,
            psychological_tactics=tactics[:6],
            red_flags=flags[:6],
            action_steps=actions[:3],
            hindi_summary=hindi,
            safe_explanation=(
                "No strong scam signals were found by the offline checks. This is not a guarantee of legitimacy."
                if verdict is Verdict.SAFE
                else None
            ),
            analysis_source=AnalysisSource.RULE_FALLBACK,
            model_used=None,
            notice="Checked with PARAKH's reviewed offline rules; the AI service was not used.",
            rule_evidence=[
                RuleEvidence(
                    rule_id=hit.rule.rule_id,
                    phrase=hit.phrase,
                    weight=round(hit.weight, 2),
                    category=hit.rule.category,
                    counted=hit.counted,
                )
                for hit in hits
            ][:40],
            rule_probability=round(p, 4),
        )

    # -- presentation -------------------------------------------------------

    @staticmethod
    def _category(counted: list[_Hit], url_risks) -> ScamCategory:
        """The fraud family with the most evidence behind it.

        UNKNOWN is carried by cross-cutting tactic rules (urgency, advance fee)
        that add real risk but name no family, so it never outranks a rule that
        does identify one.
        """

        totals: dict[ScamCategory, float] = defaultdict(float)
        for hit in counted:
            if hit.rule.category is not ScamCategory.UNKNOWN:
                totals[hit.rule.category] += hit.weight
        if not totals:
            if any(risk.score >= 30 and not risk.is_official for risk in url_risks):
                return ScamCategory.PHISHING_LINK
            return ScamCategory.UNKNOWN
        best = max(totals.values())
        # Ties are broken by the strongest single rule, so a two-weak-rule
        # category cannot outrank a decisive one.
        finalists = [cat for cat, total in totals.items() if total == best]
        if len(finalists) == 1:
            return finalists[0]
        strongest = max(
            (hit for hit in counted if hit.rule.category in finalists), key=lambda hit: hit.weight
        )
        return strongest.rule.category

    @staticmethod
    def _tactics(counted: list[_Hit]) -> list[PsychologicalTactic]:
        out: list[PsychologicalTactic] = []
        for hit in sorted(counted, key=lambda item: item.weight, reverse=True):
            if hit.rule.tactic and hit.rule.tactic not in out:
                out.append(hit.rule.tactic)
        return out

    @staticmethod
    def _red_flags(hits: list[_Hit], url_risks, verdict: Verdict) -> list[RedFlag]:
        flags: list[RedFlag] = []
        seen: set[str] = set()
        ordered = sorted(
            (hit for hit in hits if not hit.rule.is_guard), key=lambda item: (not item.counted, -item.weight)
        )
        for hit in ordered:
            key = hit.phrase.casefold()
            if key in seen or len(hit.phrase) < 2:
                continue
            flags.append(RedFlag(phrase=hit.phrase, explanation=hit.rule.simple_explanation))
            seen.add(key)
            if len(flags) >= 6:
                return flags
        if verdict is not Verdict.SAFE:
            for risk in url_risks:
                if risk.is_official or not risk.codes:
                    continue
                phrase = (risk.host or risk.url)[:160]
                if phrase.casefold() in seen:
                    continue
                flags.append(
                    RedFlag(
                        phrase=phrase,
                        explanation="Open official sites by typing the address yourself, not from a message link.",
                    )
                )
                seen.add(phrase.casefold())
                if len(flags) >= 6:
                    break
        return flags

    @staticmethod
    def _actions(counted: list[_Hit], category: ScamCategory, verdict: Verdict) -> list[str]:
        actions: list[str] = []
        for hit in sorted(counted, key=lambda item: item.weight, reverse=True):
            if hit.rule.safe_action not in actions:
                actions.append(hit.rule.safe_action)
        for action in DEFAULT_ACTIONS.get(category, GENERIC_ACTIONS):
            if action not in actions:
                actions.append(action)
        if verdict is Verdict.SCAM:
            urgent = [action for action in actions if "1930" in action]
            ordinary = [action for action in actions if "1930" not in action]
            actions = ordinary[:2] + urgent[:1] if urgent else ordinary
        return actions or list(GENERIC_ACTIONS)

    @staticmethod
    def _hindi(counted: list[_Hit], verdict: Verdict) -> str:
        if verdict is Verdict.SCAM:
            strongest = max(counted, key=lambda hit: hit.weight, default=None)
            if strongest is not None:
                return strongest.rule.hindi_explanation
            return "इस संदेश में धोखाधड़ी के कई संकेत हैं। कोई लिंक न खोलें और कोई OTP या बैंक जानकारी साझा न करें।"
        if verdict is Verdict.SUSPICIOUS:
            return "यह संदेश संदिग्ध लग रहा है। कार्रवाई करने से पहले आधिकारिक ऐप या वेबसाइट से इसकी पुष्टि करें।"
        return "इस संदेश में स्पष्ट धोखाधड़ी के संकेत नहीं मिले, फिर भी पैसे या निजी जानकारी से जुड़े अनुरोध की आधिकारिक माध्यम से पुष्टि करें।"


__all__ = [
    "RuleBasedFallbackAnalyzer",
    "BIAS",
    "T_SCAM",
    "T_SUSPICIOUS",
    "FITTED_AT",
    "GUARD_CAP_RATIO",
    "probability",
    "weight_of",
]
