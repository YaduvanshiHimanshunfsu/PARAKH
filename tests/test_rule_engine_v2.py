from __future__ import annotations

"""Rule engine v2: evidence combination, caps, guards (planversionalpha.md B.2)."""

import pytest

from app.data.scam_rules import RULES_BY_ID, SCAM_SIGNAL_RULES
from app.schemas import ScamCategory, Verdict
from app.services.fallback_analyzer import (
    GUARD_CAP_RATIO,
    MAX_RULES_PER_CATEGORY,
    T_SCAM,
    T_SUSPICIOUS,
    RuleBasedFallbackAnalyzer,
    probability,
)


@pytest.fixture()
def engine() -> RuleBasedFallbackAnalyzer:
    return RuleBasedFallbackAnalyzer()


def test_thresholds_are_ordered_and_in_range():
    assert 0 < T_SUSPICIOUS < T_SCAM < 1


def test_every_rule_has_an_id_source_and_sane_weight():
    for rule in SCAM_SIGNAL_RULES:
        assert rule.rule_id == rule.rule_id.upper()
        assert rule.source
        assert -4.5 <= rule.weight <= 4.5
        assert rule.simple_explanation and rule.hindi_explanation and rule.safe_action
    assert len(RULES_BY_ID) == len(SCAM_SIGNAL_RULES)


def test_guards_are_the_only_negative_rules():
    for rule in SCAM_SIGNAL_RULES:
        assert rule.is_guard == (rule.weight < 0)
        if rule.is_guard:
            assert rule.rule_id.startswith("GUARD_")


def test_tactic_group_deduplication(engine):
    """Three urgency phrases must count once, not three times."""

    one = engine.score("Urgent: act now.")[0]
    three = engine.score("Urgent! Act now, today only, within 24 hours.")[0]
    assert three == pytest.approx(one, abs=0.01)


def test_category_cap(engine):
    hits = engine._apply_caps(engine.hits(
        "Your SBI account will be blocked, update KYC, PAN card update pending, "
        "enter card details and reward points expire today"
    ))
    counted = [h for h in hits if h.counted and h.rule.category is ScamCategory.KYC_SCAM]
    assert len(counted) <= MAX_RULES_PER_CATEGORY


def test_guard_lowers_an_advisory_to_safe(engine):
    advisory = engine.analyze(
        "Beware of fraud: your bank will never ask for OTP or PIN. Report cyber fraud at 1930."
    )
    assert advisory.verdict is Verdict.SAFE


def test_guard_cannot_erase_strong_evidence(engine):
    """A scam that borrows advisory wording keeps most of its score."""

    scam = engine.analyze(
        "This is CBI. You are under digital arrest. Do not disconnect the call and do not tell "
        "anyone. Transfer the bail amount to the verification account now."
    )
    assert scam.verdict is Verdict.SCAM
    assert GUARD_CAP_RATIO < 1


def test_red_flags_are_exact_substrings_of_the_original(engine):
    message = "Your K.Y.C will be bl​ocked. Share O​TP now."
    result = engine.analyze(message)
    assert result.red_flags
    for flag in result.red_flags:
        assert flag.phrase in message


def test_evidence_lists_rule_ids_and_contributions(engine):
    result = engine.analyze("Share your OTP to verify your account immediately.")
    assert result.rule_evidence
    assert {item.rule_id for item in result.rule_evidence} <= set(RULES_BY_ID)
    assert any(item.rule_id == "OTP_ASK" and item.weight > 0 for item in result.rule_evidence)
    assert 0.0 <= result.rule_probability <= 1.0


def test_probability_is_monotonic():
    assert probability(-5) < probability(0) < probability(5)


# --- B.3 typology packs: one case per language, plus hard negatives ---------

SCAM_CASES = [
    ("DIGITAL_ARREST en", ScamCategory.DIGITAL_ARREST,
     "This is the CBI. A parcel in your name contained drugs and a case has been registered. "
     "You are under digital arrest, do not disconnect the video call."),
    ("DIGITAL_ARREST hi", ScamCategory.DIGITAL_ARREST,
     "मैं सीबीआई से बोल रहा हूँ। आपके नाम के पार्सल में ड्रग्स मिले हैं, केस दर्ज हुआ है। "
     "आप डिजिटल अरेस्ट में हैं, वीडियो कॉल बंद न करें।"),
    ("DIGITAL_ARREST hinglish", ScamCategory.DIGITAL_ARREST,
     "CBI se baat kar raha hoon. Aapke aadhaar se money laundering ka case darj hua hai. "
     "Digital arrest me hain, call mat kaatna."),
    ("MALICIOUS_APP en", ScamCategory.MALICIOUS_APP,
     "Your vehicle e-challan is pending. Download RTO_Challan.apk to view the photo and pay."),
    ("MALICIOUS_APP hi", ScamCategory.MALICIOUS_APP,
     "आपका ई-चालान लंबित है। चालान देखने के लिए यह एपीके डाउनलोड करें: rto-challan.apk"),
    ("SEXTORTION en", ScamCategory.SEXTORTION,
     "We recorded your private video. Pay now or we will upload it and send it to your family."),
    ("SEXTORTION hi", ScamCategory.SEXTORTION,
     "आपका अश्लील वीडियो हमारे पास है। पैसे भेजो वरना वायरल कर देंगे और परिवार को भेज देंगे।"),
    ("MARKETPLACE_FRAUD en", ScamCategory.MARKETPLACE_FRAUD,
     "I am an Army officer on transfer, I saw your bike on OLX. I will send an advance, "
     "scan this QR and enter your PIN."),
    ("MARKETPLACE_FRAUD hi", ScamCategory.MARKETPLACE_FRAUD,
     "मैं आर्मी अफसर हूँ, आपकी बाइक ओएलएक्स पर देखी। एडवांस भेजने के लिए यह क्यूआर स्कैन करें।"),
    ("UTILITY hi", ScamCategory.UTILITY_BILL_SCAM,
     "प्रिय उपभोक्ता, आपकी बिजली आज रात काट दी जाएगी क्योंकि पिछला बिल अपडेट नहीं हुआ। "
     "तुरंत बिजली अधिकारी 9988776655 पर कॉल करें।"),
    ("UTILITY hinglish", ScamCategory.UTILITY_BILL_SCAM,
     "Aapki bijli aaj raat 9:30 baje kat jayegi kyunki pichla bill update nahi hua. "
     "Turant call karein 9988776655."),
    ("KYC hi", ScamCategory.KYC_SCAM,
     "आपका खाता बंद कर दिया जाएगा। तुरंत केवाईसी अपडेट करें।"),
    ("GOVT hi", ScamCategory.GOVERNMENT_IMPERSONATION,
     "आपकी एसएसओ आईडी 24 घंटे में ब्लॉक होगी। अभी सत्यापन करें sso-rajasthan-verify.online"),
    ("FAKE_JOB hinglish", ScamCategory.FAKE_JOB,
     "Aapke 3 task complete ho gaye, ab next task ke liye 10000 deposit karo, 15000 wapas milega."),
    ("LOAN hinglish", ScamCategory.LOAN_APP_FRAUD,
     "Loan time par nahi chukaya, ab tumhare saare contacts ko photo bhej denge. "
     "2 ghante me payment karo."),
]


@pytest.mark.parametrize("name,category,message", SCAM_CASES, ids=[case[0] for case in SCAM_CASES])
def test_typology_packs_detect_and_classify(engine, name, category, message):
    result = engine.analyze(message)
    assert result.verdict is not Verdict.SAFE, f"{name} scored SAFE"
    assert result.scam_category is category, f"{name} -> {result.scam_category.value}"


HARD_NEGATIVES = [
    ("real debit alert",
     "Rs.2,500.00 debited from A/c XX4821 on 23-11-26 to VPA grocery.store@okicici. "
     "Avl Bal Rs.18,240.55. Not you? Call 1800 1234 -SBI"),
    ("real OTP notice",
     "482913 is your OTP for login to your bank account. Valid for 5 minutes. "
     "Do not share this OTP with anyone, including bank staff."),
    ("police awareness advisory",
     "Rajasthan Police: no police officer arrests anyone on a video call. "
     "If you are defrauded, call 1930 immediately."),
    ("police advisory hinglish",
     "Rajasthan Police: koi bhi police video call par digital arrest nahi karti. "
     "Thagi hone par turant 1930 par call karein."),
    ("discom advisory hi",
     "सावधान! बिजली कटने के फर्जी संदेशों से बचें। बिजली विभाग कभी निजी मोबाइल नंबर पर कॉल करने को नहीं कहता।"),
    ("apk advisory hi",
     "व्हाट्सऐप पर आई कोई भी एपीके फ़ाइल इंस्टॉल न करें, चाहे वह शादी का कार्ड हो या ई-चालान।"),
    ("planned outage hi",
     "वैशाली नगर में 27 नवंबर को सुबह 10 से दोपहर 2 बजे तक रखरखाव के कारण बिजली बंद रहेगी।"),
    ("sebi advisory",
     "Guaranteed returns are a red flag. Check if an investment advisor is registered with SEBI before investing."),
    ("delivery code",
     "Your order is out for delivery. Share the code 4471 only with the delivery agent at your door."),
    ("ordinary dispatch note",
     "Your order 4471239 has been dispatched and will arrive on Tuesday between 10am and 2pm. No action is needed."),
]


@pytest.mark.parametrize("name,message", HARD_NEGATIVES, ids=[case[0] for case in HARD_NEGATIVES])
def test_hard_negatives_are_not_scams(engine, name, message):
    assert engine.analyze(message).verdict is not Verdict.SCAM, name
