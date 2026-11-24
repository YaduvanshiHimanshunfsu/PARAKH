from __future__ import annotations

"""Reviewed content rules for fraudulent investment, MLM, and betting sites.

PS01 asks for examination of "promotional content for guaranteed returns,
referral-chain (MLM) language and betting indicators". These rules operate on
the visible text of a fetched page and mirror the ``ScamSignalRule`` shape used
elsewhere, so a website verdict is explained by the same kind of reviewed,
version-controlled rule as a message verdict.

Deterministic by design (DECISIONS.md ADR-005): no AI provider is consulted to
reach a website verdict.
"""

import re
from dataclasses import dataclass

from app.schemas import ScamCategory, Severity


@dataclass(frozen=True)
class WebsiteRule:
    code: str
    pattern: re.Pattern[str]
    category: ScamCategory
    severity: Severity
    weight: int
    explanation: str


def _rule(
    code: str,
    pattern: str,
    category: ScamCategory,
    severity: Severity,
    weight: int,
    explanation: str,
) -> WebsiteRule:
    return WebsiteRule(code, re.compile(pattern, re.IGNORECASE), category, severity, weight, explanation)


WEBSITE_RULES: tuple[WebsiteRule, ...] = (
    # --- guaranteed returns -------------------------------------------------
    _rule(
        "GUARANTEED_RETURNS",
        r"\b(?:guaranteed|assured|fixed|risk[\s-]?free)\s+(?:returns?|profits?|income|roi|earnings?)\b",
        ScamCategory.PONZI_MLM,
        Severity.HIGH,
        30,
        "The site promises guaranteed or risk-free returns. No lawful investment can guarantee a "
        "return, and this wording is the most common marker of a Ponzi scheme.",
    ),
    _rule(
        "DAILY_RETURN_PERCENTAGE",
        r"\b\d{1,3}\s*%\s*(?:daily|per\s+day|everyday|weekly|per\s+week|monthly|per\s+month)\b",
        ScamCategory.PONZI_MLM,
        Severity.HIGH,
        32,
        "A fixed daily, weekly, or monthly percentage return is advertised. Sustained returns at "
        "these rates are mathematically impossible and are paid from new deposits.",
    ),
    _rule(
        "DOUBLE_YOUR_MONEY",
        r"\b(?:double|triple)\s+(?:your\s+)?(?:money|investment|capital|amount)\b|\bmoney\s+back\s+guarantee[d]?\b",
        ScamCategory.PONZI_MLM,
        Severity.HIGH,
        28,
        "The site promises to multiply the visitor's money, a classic high-yield investment fraud claim.",
    ),
    _rule(
        "NO_RISK_CLAIM",
        r"\b(?:100\s*%\s*(?:safe|secure|guaranteed)|zero\s+risk|no\s+loss|loss\s*-?\s*free)\b",
        ScamCategory.PONZI_MLM,
        Severity.MEDIUM,
        20,
        "The site claims there is no risk of loss. Every genuine investment carries risk, and "
        "regulated firms are required to say so.",
    ),

    # --- MLM / referral chain ----------------------------------------------
    _rule(
        "REFERRAL_CHAIN_INCOME",
        r"\b(?:referral\s+(?:bonus|income|commission)|refer\s+(?:and|&)\s+earn|downline|upline|"
        r"level\s+(?:income|bonus)|binary\s+(?:plan|income)|matrix\s+plan|team\s+commission)\b",
        ScamCategory.PONZI_MLM,
        Severity.HIGH,
        30,
        "Earnings depend on recruiting other people rather than on any product or service. This "
        "referral-chain structure is the defining feature of an MLM or pyramid scheme.",
    ),
    _rule(
        "JOINING_PACKAGE_FEE",
        r"\b(?:joining\s+(?:fee|package|amount)|registration\s+(?:fee|package)|activation\s+(?:fee|amount)|"
        r"id\s+activation|activate\s+your\s+id|starter\s+package)\b",
        ScamCategory.PONZI_MLM,
        Severity.HIGH,
        26,
        "An upfront payment is required before the visitor can start earning, which is how a "
        "pyramid scheme funds payouts to earlier members.",
    ),
    _rule(
        "RANK_AND_REWARD_LADDER",
        r"\b(?:silver|gold|platinum|diamond)\s+(?:member|package|plan|level)\b|\brank\s+(?:bonus|reward)\b",
        ScamCategory.PONZI_MLM,
        Severity.MEDIUM,
        14,
        "Tiered membership ranks tied to payouts are used to push participants to invest more and "
        "recruit faster.",
    ),

    # --- betting / gambling -------------------------------------------------
    _rule(
        "BETTING_PLATFORM",
        r"\b(?:betting\s+(?:id|site|app|exchange)|bet\s+now|place\s+(?:your\s+)?bets?|satta|"
        r"fancy\s+rate|teer\s+result|book(?:ie|maker))\b",
        ScamCategory.BETTING_GAMBLING,
        Severity.HIGH,
        28,
        "The site operates or advertises betting. Online betting of this kind is illegal in most "
        "Indian states and these platforms frequently refuse withdrawals.",
    ),
    _rule(
        "PREDICTION_GAME",
        r"\b(?:colou?r\s+prediction|aviator\s+game|crash\s+game|dice\s+game|wingo|lucky\s+number\s+game)\b",
        ScamCategory.BETTING_GAMBLING,
        Severity.HIGH,
        30,
        "Colour-prediction and crash-style games are rigged gambling products marketed as skill "
        "games or earning apps.",
    ),
    _rule(
        "DEPOSIT_BONUS_LURE",
        r"\b(?:deposit\s+bonus|welcome\s+bonus|first\s+deposit\s+offer|instant\s+withdrawal|"
        r"sign\s*up\s+bonus|cashback\s+on\s+deposit)\b",
        ScamCategory.BETTING_GAMBLING,
        Severity.MEDIUM,
        18,
        "Deposit bonuses and instant-withdrawal promises are used to pull users into depositing "
        "money that often cannot be taken back out.",
    ),
    _rule(
        "SURE_WINNING_TIPS",
        r"\b(?:100\s*%\s*(?:winning|sure|accurate)|sure\s*-?\s*shot\s+tips?|guaranteed\s+win|"
        r"fixed\s+match(?:es)?)\b",
        ScamCategory.BETTING_GAMBLING,
        Severity.HIGH,
        26,
        "Guaranteed winning tips or fixed matches are advertised. These claims are always false "
        "and are used to sell subscriptions or collect deposits.",
    ),

    # --- predatory lending --------------------------------------------------
    _rule(
        "INSTANT_LOAN_NO_CHECKS",
        r"\b(?:instant\s+loan|loan\s+in\s+(?:\d+\s*)?(?:minutes?|mins?|hours?)|no\s+cibil|"
        r"no\s+credit\s+check|without\s+documents?|only\s+aadhaar|aadhaar\s+only)\b",
        ScamCategory.LOAN_APP_FRAUD,
        Severity.HIGH,
        28,
        "Loans are offered with no credit assessment or documentation. Unregulated lenders use "
        "this to harvest personal data and charge extortionate rates.",
    ),
    _rule(
        "DIRECT_APK_DOWNLOAD",
        r"\bdownload\s+(?:our\s+)?apk\b|\.apk\b|\bsideload\b|\binstall\s+from\s+unknown\s+sources?\b",
        ScamCategory.LOAN_APP_FRAUD,
        Severity.HIGH,
        30,
        "The site distributes an Android APK directly instead of through an official app store, "
        "which bypasses store review entirely.",
    ),

    # --- regulatory and transparency gaps -----------------------------------
    _rule(
        "FAKE_REGULATORY_CLAIM",
        r"\b(?:sebi|rbi)\s+(?:approved|registered|certified|authorised|authorized)\b|"
        r"\bgovernment\s+(?:approved|certified)\s+(?:scheme|investment|plan)\b",
        ScamCategory.PONZI_MLM,
        Severity.HIGH,
        24,
        "The site claims regulatory approval. SEBI and RBI do not approve investment schemes or "
        "guarantee returns, so this claim is itself a warning sign — verify on the regulator's "
        "own website.",
    ),
    _rule(
        "URGENCY_PRESSURE",
        r"\b(?:limited\s+(?:time|slots?|seats?)|offer\s+ends|hurry|last\s+chance|only\s+\d+\s+(?:slots?|seats?)\s+left)\b",
        ScamCategory.UNKNOWN,
        Severity.LOW,
        10,
        "Artificial time pressure is used to stop visitors from checking the scheme before paying.",
    ),
    _rule(
        "TELEGRAM_WHATSAPP_FUNNEL",
        r"\b(?:join\s+(?:our\s+)?telegram|telegram\s+channel|whatsapp\s+group|t\.me/|wa\.me/|chat\s+on\s+whatsapp)\b",
        ScamCategory.UNKNOWN,
        Severity.MEDIUM,
        16,
        "Visitors are funnelled into Telegram or WhatsApp, moving the conversation off any "
        "moderated or auditable platform.",
    ),
    _rule(
        "CRYPTO_DEPOSIT_REQUEST",
        r"\b(?:send\s+(?:btc|eth|usdt|bitcoin)|crypto\s+deposit|wallet\s+address|usdt\s+trc20|bep20)\b",
        ScamCategory.INVESTMENT_FRAUD,
        Severity.HIGH,
        26,
        "The site requests cryptocurrency deposits, which are effectively irreversible and are "
        "preferred by fraudulent operators for that reason.",
    ),
)


# Markers whose ABSENCE is meaningful on a site soliciting money. A genuine
# financial business publishes these; a disposable fraud site rarely bothers.
LEGITIMACY_MARKERS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("privacy policy", re.compile(r"privacy\s+policy", re.IGNORECASE)),
    ("terms and conditions", re.compile(r"terms\s+(?:and|&)\s+conditions|terms\s+of\s+(?:use|service)", re.IGNORECASE)),
    ("contact or address", re.compile(r"\b(?:contact\s+us|registered\s+office|our\s+address)\b", re.IGNORECASE)),
    ("company registration", re.compile(r"\b(?:cin|gstin|registration\s+(?:no|number)|incorporat)\w*", re.IGNORECASE)),
    ("refund policy", re.compile(r"refund\s+policy|cancellation\s+policy", re.IGNORECASE)),
)

# A money-soliciting page is judged more strictly than a brochure site.
MONEY_SOLICITATION = re.compile(
    r"\b(?:deposit|invest|pay(?:ment)?|recharge|withdraw|wallet|upi|bank\s+transfer|subscribe)\b",
    re.IGNORECASE,
)


# --- Hindi equivalents (planversionalpha.md B.8 step 4) --------------------
#
# A Hindi-language Ponzi or betting site scored zero before this: every rule
# above is English-only. Devanagari patterns use no \b, because Python word
# boundaries fall inside Hindi words (see tests/test_rule_patterns.py).

HINDI_WEBSITE_RULES: tuple[WebsiteRule, ...] = (
    _rule(
        "GUARANTEED_RETURNS_HI",
        r"(?:गारंटीड?|निश्चित|पक्का|सुनिश्चित)\s*(?:रिटर्न|मुनाफ़?ा|लाभ|कमाई)"
        r"|(?:रोज़?ाना|रोजाना|हर\s*दिन|दैनिक)\s*(?:मुनाफ़?ा|कमाई|आय|रिटर्न)"
        r"|पैसा\s*(?:डबल|दोगुना)",
        ScamCategory.PONZI_MLM,
        Severity.HIGH,
        30,
        "The page promises guaranteed or daily returns in Hindi. No lawful investment can "
        "guarantee a fixed return.",
    ),
    _rule(
        "REFERRAL_INCOME_HI",
        r"रेफरल\s*(?:बोनस|आय|कमीशन)|डाउनलाइन|अपलाइन|(?:लेवल|बाइनरी)\s*(?:इनकम|आय)"
        r"|टीम\s*(?:इनकम|आय)",
        ScamCategory.PONZI_MLM,
        Severity.HIGH,
        26,
        "Income that depends on recruiting other members is the defining feature of a Ponzi "
        "or MLM scheme.",
    ),
    _rule(
        "BETTING_HI",
        r"सट्टा|सट्टेबाज़?ी|बेटिंग\s*आईडी|क्रिकेट\s*आईडी|मटका|रंग\s*भविष्यवाणी"
        r"|जुआ|दांव\s*लगाएं",
        ScamCategory.BETTING_GAMBLING,
        Severity.HIGH,
        26,
        "The page advertises betting or gambling in Hindi, which is illegal in most Indian "
        "states.",
    ),
    _rule(
        "JOINING_FEE_HI",
        r"(?:जॉइनिंग|ज्वाइनिंग|पंजीकरण|रजिस्ट्रेशन)\s*(?:शुल्क|फीस|पैकेज|राशि)"
        r"|आईडी\s*(?:सक्रिय|एक्टिवेट)",
        ScamCategory.PONZI_MLM,
        Severity.MEDIUM,
        18,
        "An upfront joining or activation fee before any earning is a classic Ponzi entry fee.",
    ),
    _rule(
        "INSTANT_LOAN_HI",
        r"(?:तुरंत|इंस्टेंट|फ़ौरन)\s*लोन|बिना\s*(?:सिबिल|दस्तावेज़?|कागज़?)"
        r"|सिर्फ़?\s*आधार\s*(?:से|पर)\s*लोन",
        ScamCategory.LOAN_APP_FRAUD,
        Severity.MEDIUM,
        20,
        "Instant loans with no credit check or documents indicate an unregulated lender.",
    ),
    _rule(
        "WITHDRAWAL_BLOCKED_HI",
        r"निकासी\s*(?:रोक|बंद|अवरुद्ध)|विड्रॉल\s*(?:रोक|बंद)"
        r"|(?:और|अधिक)\s*(?:जमा|डिपॉज़िट)\s*(?:कर(?:ें|ो)|करने)\s*(?:पर|के\s*बाद)",
        ScamCategory.PONZI_MLM,
        Severity.HIGH,
        24,
        "Demanding a further deposit before a withdrawal is released is how these schemes "
        "take the last payment.",
    ),
)

WEBSITE_RULES = WEBSITE_RULES + HINDI_WEBSITE_RULES
