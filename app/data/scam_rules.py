from __future__ import annotations

"""Reviewed offline scam-signal rules (rule engine v2, planversionalpha.md B.2/B.3).

Each rule is explainable and observable in the message text. A rule has:

* ``rule_id`` and ``version``: cited in reports so a reader knows exactly which
  reviewed rule fired.
* ``patterns``: English, Hinglish and Devanagari variants. Rules run on the
  normalised view of the message (app/utils/text_normalise.py). Devanagari
  patterns never use ``\\b``: vowel signs are combining marks and break Python
  word boundaries.
* ``weight``: a log-odds contribution. The prior below is hand-set from the
  pattern's specificity; ``app/data/rule_weights.json`` (fitted on the dev split
  by ``scripts/fit_rule_weights.py``) overrides it when present.
* ``tactic_group``: rules in the same group count once (the strongest), so
  "urgent + immediately + today only" cannot stack.
* Negative-weight *guards* encode legitimate structures (a real debit alert,
  an official "never share your OTP" advisory) and lower suspicion.

These rules are a safety net, not proof that a sender is a criminal.
"""

import re
from dataclasses import dataclass, field

from app.schemas import PsychologicalTactic, ScamCategory

C = ScamCategory
T = PsychologicalTactic

PUBLIC_ADVISORIES = "Pattern from public I4C / RBI / police awareness material"


@dataclass(frozen=True)
class ScamSignalRule:
    rule_id: str
    patterns: tuple[str, ...]
    category: ScamCategory
    weight: float
    simple_explanation: str
    hindi_explanation: str
    safe_action: str
    tactic: PsychologicalTactic | None = None
    tactic_group: str | None = None
    languages: tuple[str, ...] = ("en",)
    source: str = PUBLIC_ADVISORIES
    version: int = 1
    compiled: tuple[re.Pattern[str], ...] = field(init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "compiled", tuple(re.compile(p, re.IGNORECASE | re.DOTALL) for p in self.patterns)
        )

    @property
    def is_guard(self) -> bool:
        return self.weight < 0


def R(rule_id, patterns, category, weight, simple, hindi, action, tactic=None, group=None, languages=("en",), source=PUBLIC_ADVISORIES):
    if isinstance(patterns, str):
        patterns = (patterns,)
    return ScamSignalRule(rule_id, tuple(patterns), category, weight, simple, hindi, action, tactic, group, tuple(languages), source)


EN_HI = ("en", "hinglish", "hi")

SCAM_SIGNAL_RULES: tuple[ScamSignalRule, ...] = (
    # --- cross-cutting tactics (category UNKNOWN: add risk, name no family) ---
    R("TAC_URGENCY",
      (r"\b(?:within|in)\s+(?:\d+|one|two|24|48)\s*(?:hours?|hrs?|minutes?|mins?)\b|\b(?:urgent(?:ly)?|immediately|right now|last (?:date|chance|warning|reminder)|today only|tonight|expires? today|final (?:notice|warning)|act now)\b",
       r"\b(?:turant|jaldi\s+(?:karo|karein|se)|abhi\s+(?:ke abhi|turant)|aaj\s+raat|aaj\s+hi)\b",
       r"तुरंत|फौरन|फ़ौरन|आज\s*रात|आज\s*ही|अंतिम\s*(?:चेतावनी|तिथि|मौका)|\d+\s*घंटे"),
      C.UNKNOWN, 0.8, "Pressure to act quickly can stop you from checking safely.", "जल्दी करने का दबाव आपको जांच करने से रोक सकता है।",
      "Pause and verify through an independently known official channel.", T.FALSE_URGENCY, "URGENCY", EN_HI),
    R("TAC_ADVANCE_FEE",
      (r"\b(?:registration|joining|advance|processing|activation|verification|clearance|release|customs|training|token|security|gst|convenience)\s+(?:fee|charges?|amount|kit)\b|\bpay\b.{0,18}\b(?:fee|charges?)\b|\bfee\s+of\s+(?:rs\.?\s*)?[\d,]+\b",
       r"\bfees?\s+(?:bharo|bharna|jama\s+karo|jama\s+karna|dena\s+hoga|bhej\w*)\b|\b(?:processing|registration|customs)\s+fee\b",
       r"(?:शुल्क|फीस|चार्ज).{0,25}(?:जमा|भुगतान|भरें|देना)"),
      C.UNKNOWN, 1.6, "A fee demanded before you receive anything is a common scam pattern.", "कुछ मिलने से पहले फीस मांगना आम धोखाधड़ी का तरीका है।",
      "Do not pay a fee to receive a prize, refund, loan or job.", T.PROCESSING_FEE_TRAP, "FEE", EN_HI),
    R("TAC_FEE_BEFORE_DELIVERY",
      (r"\b(?:pay|send|transfer|deposit|submit)\b.{0,45}\b(?:fee|charges?|amount|rs\.?\s*[\d,]+)\b.{0,30}\bto\s+(?:receive|get|claim|release|proceed|continue|unlock|activate|avail|collect)\b"
       r"|\b(?:to\s+(?:receive|get|claim|release|proceed|continue|unlock|activate))\b.{0,45}\b(?:pay|send|transfer|deposit|submit)\b.{0,25}\b(?:fee|charges?|rs\.?\s*[\d,]+)\b",
       r"\b(?:paane|lene|milne)\s+(?:ke\s+liye)\b.{0,35}\b(?:fee|paise|rupaye|jama|bhej\w*)\b",
       r"(?:पाने|लेने|प्राप्त\s*करने)\s*(?:के\s*लिए).{0,40}(?:शुल्क|फीस|राशि|जमा|भेज)"),
      C.UNKNOWN, 1.3, "You are asked to pay before you receive anything.", "कुछ मिलने से पहले भुगतान मांगा जा रहा है।",
      "Never pay to release a prize, refund, parcel, loan or job.", T.PROCESSING_FEE_TRAP, "FEE_FIRST", EN_HI),

    R("TAC_LINK_ACTION",
      (r"\b(?:click|tap)\s+(?:here|on\s+(?:the|this|below)\s+link|the\s+link|this\s+link|below)\b|\bopen\s+(?:the\s+|this\s+)?link\b|\b(?:bit\.ly|tinyurl\.com|cutt\.ly|is\.gd|t\.ly|rb\.gy|shorturl\.at)/|\bwa\.me/",
       r"\blink\s+(?:par|pe|pr)\s+click\b|\blink\s+(?:kholo|kholein|khol\s+ke)\b",
       r"लिंक\s*(?:पर|पे)\s*क्लिक|लिंक\s*(?:खोलें|खोलो|खोलकर)|नीचे\s*दिए\s*(?:गए\s*)?लिंक"),
      C.PHISHING_LINK, 1.1, "Unexpected links can lead to fake login or payment pages.", "अनजान लिंक नकली लॉगिन या पेमेंट पेज पर ले जा सकता है।",
      "Do not open the link; type the official website yourself.", T.FALSE_URGENCY, "LINK", EN_HI),
    R("TAC_PRIVATE_NUMBER",
      (r"\b(?:call|contact|whatsapp|message|sms|ring)\b[^.\n]{0,30}?(?:\+91[\s-]?|0)?[6-9]\d{9}\b",
       r"(?:कॉल|संपर्क|व्हाट्सएप)[^।\n]{0,30}?(?:\+91[\s-]?)?[6-9]\d{9}"),
      C.UNKNOWN, 0.9, "Organisations do not ask you to call a private mobile number from a message.", "कोई संस्था संदेश में निजी मोबाइल नंबर पर कॉल करने को नहीं कहती।",
      "Call only the number printed on your bill, card or the official website.", T.AUTHORITY_IMPERSONATION, "CONTACT", ("en", "hi")),
    R("TAC_MOVE_CHANNEL",
      (r"\b(?:join|contact|message|ping|add)\b.{0,25}\b(?:telegram|whatsapp)\b(?:\s+(?:group|channel))?|\bt\.me/",
       r"(?:टेलीग्राम|व्हाट्सएप)\s*(?:ग्रुप|चैनल).{0,20}(?:जुड़ें|जॉइन)"),
      C.UNKNOWN, 0.7, "Moving you to Telegram or WhatsApp avoids the platform's protections.", "आपको टेलीग्राम या व्हाट्सएप पर ले जाना सुरक्षा से बचने का तरीका है।",
      "Stay on official channels; do not join unknown groups.", T.SOCIAL_PROOF_FABRICATION, "CHANNEL", ("en", "hi")),
    R("TAC_SECRECY",
      (r"\b(?:do\s*n[o']?t|don't|never)\s+(?:tell|inform|share\s+this\s+with)\s+(?:anyone|anybody|your\s+(?:family|bank|parents))\b|\bkeep\s+(?:this|it)\s+(?:confidential|secret)\b",
       r"\bkisi\s+ko\s+(?:mat|na)\s+(?:batana|batao|bataye)\b",
       r"किसी\s*को\s*(?:न|ना|मत)\s*(?:बताएं|बताएँ|बताना|बताओ)|गोपनीय\s*रखें"),
      C.UNKNOWN, 1.6, "Being told to keep it secret is how scammers stop victims from getting help.", "किसी को न बताने को कहना ठगों का तरीका है ताकि आप मदद न ले सकें।",
      "Tell a family member and verify independently before doing anything.", T.FEAR_INDUCTION, "SECRECY", EN_HI),

    # --- KYC / account block --------------------------------------------------
    R("KYC_TOPIC",
      (r"\b(?:re-?)?kyc\b|\bverify\s+(?:your\s+)?(?:account|kyc|pan|identity)\b|\bupdate\s+(?:your\s+)?(?:kyc|pan|details|aadhaar|account)\b|\bpan\s+(?:card\s+)?(?:update|link|verification)\b",
       r"\bkyc\s+(?:update\s+)?(?:karo|karein|kare|kijiye)\b",
       r"केवाईसी|के\s*वाई\s*सी|पैन\s*(?:कार्ड\s*)?(?:अपडेट|लिंक)|(?:खाता|अकाउंट)\s*(?:वेरीफाई|सत्यापित)"),
      C.KYC_SCAM, 1.4, "Unexpected account verification can be used to steal details.", "अचानक KYC या अकाउंट वेरिफिकेशन का संदेश धोखाधड़ी हो सकता है।",
      "Open the official bank or telecom app yourself; do not use this message's link.", T.AUTHORITY_IMPERSONATION, "KYC", EN_HI),
    R("KYC_BLOCK_THREAT",
      (r"\b(?:account|a/c|card|netbanking|net\s*banking|yono|wallet|sim|number|connection|services?|upi(?:\s+id)?|login|subscription|policy)\b.{0,40}\b(?:block(?:ed)?|suspend(?:ed)?|deactivat\w*|frozen|freez\w*|clos(?:ed|e)|terminat\w*|disabled?|stopp?ed|barred)\b|\b(?:block(?:ed)?|suspend(?:ed)?|deactivated|frozen)\b.{0,30}\b(?:account|card|sim|number|netbanking|upi)\b",
       r"\b(?:account|khata|sim|number|card)\s+(?:band|block)\s+(?:ho|kar|kiya)",
       r"(?:खाता|अकाउंट|कार्ड|सिम|नंबर|बैंक\s*खाता|नेट\s*बैंकिंग).{0,30}(?:बंद|ब्लॉक|निलंबित|फ्रीज़|फ्रीज|रोक\s*दिया|सस्पेंड)"),
      C.KYC_SCAM, 1.8, "A threat to block an account is meant to create fear.", "खाता बंद होने की धमकी देकर डराया जा रहा है।",
      "Do not rush. Check the account only in the official app.", T.FEAR_INDUCTION, "BLOCK", EN_HI),
    R("KYC_REWARD_POINTS",
      (r"\b(?:reward\s+points?|credit\s+card\s+limit|card\s+limit|cashback\s+points?)\b.{0,60}\b(?:redeem|expir\w*|increase|claim|link|today|lapse)\b",
       r"(?:रिवॉर्ड|रिवार्ड)\s*(?:पॉइंट|प्वाइंट).{0,40}(?:रिडीम|समाप्त|एक्सपायर)"),
      C.KYC_SCAM, 2.0, "Reward-point and card-limit messages are used to collect card details on fake pages.", "रिवॉर्ड पॉइंट या कार्ड लिमिट के नाम पर नकली पेज पर कार्ड विवरण लिया जाता है।",
      "Check points or limits only inside the official card app.", T.TOO_GOOD_TO_BE_TRUE, "REWARD", ("en", "hi")),
    R("KYC_CARD_DETAILS",
      (r"\b(?:enter|provide|share|update|fill)\b.{0,30}\b(?:card\s+(?:details|number)|debit\s+card|credit\s+card|expiry|net\s*banking\s+(?:id|password|details))\b",
       r"(?:कार्ड\s*(?:नंबर|विवरण)|नेट\s*बैंकिंग\s*पासवर्ड).{0,25}(?:दर्ज|भरें|बताएं|डालें)"),
      C.KYC_SCAM, 2.0, "No bank asks you to type card or net-banking details from a message.", "कोई बैंक संदेश से कार्ड या नेट बैंकिंग विवरण नहीं मांगता।",
      "Never enter card or banking details on a page opened from a message.", T.AUTHORITY_IMPERSONATION, "CREDENTIALS", ("en", "hi")),

    # --- OTP / secrets ----------------------------------------------------------
    R("OTP_ASK",
      (r"(?<!not\s)(?<!never\s)(?<!n't\s)(?<!dont\s)\b(?:share|send|tell|provide|give|forward|read\s+out|confirm|reply\s+with)\b.{0,40}\b(?:otp|one[ -]?time\s+password|cvv|upi\s+pin|atm\s+pin|password|verification\s+code)\b",
       r"\botp\b.{0,20}\b(?:batao|bhejo|bata\s+do|de\s+do|dijiye|share\s+karo|bataiye)\b|\b(?:batao|bhejo|bataiye)\b.{0,15}\botp\b",
       r"(?:ओटीपी|OTP|पिन|पासवर्ड).{0,25}(?:बताएं|बताएँ|बताइए|बताओ|भेजें|भेजो|शेयर\s*करें|दें|दीजिए)"),
      C.OTP_THEFT, 3.5, "A real bank or payment app will not ask you to reveal an OTP, PIN, CVV or password.", "बैंक या पेमेंट ऐप आपसे OTP, PIN, CVV या पासवर्ड नहीं मांगता।",
      "End the conversation. Do not share any security secret.", T.OTP_SOCIAL_ENGINEERING, "SECRET", EN_HI),

    # --- UPI ----------------------------------------------------------------------
    R("UPI_PIN_TO_RECEIVE",
      (r"\b(?:upi|gpay|google\s+pay|phonepe|paytm|bhim)\b.{0,55}\b(?:collect|approve|pin|receive\s+money|refund|cashback)\b|\benter\s+(?:your\s+)?(?:upi\s+)?pin\b.{0,40}\b(?:receive|get|credit|refund|cashback)\b",
       r"\bpin\s+(?:daalo|dalo|daal\s+ke|daalein)\b.{0,30}\b(?:paise|paisa|refund|cashback)\b",
       r"पिन\s*(?:डालें|डालकर|डाले|डालिए|डालो)|(?:पैसे|रिफंड|कैशबैक)\s*(?:पाने|प्राप्त).{0,70}(?:पिन|कलेक्ट\s*रिक्वेस्ट)|कलेक्ट\s*रिक्वेस्ट\s*(?:स्वीकार|मंजूर|अप्रूव)"),
      C.UPI_FRAUD, 2.8, "Receiving money never needs a UPI PIN; approving a request sends money out.", "पैसे पाने के लिए UPI PIN नहीं डालना पड़ता; collect request मंजूर करने से भुगतान हो जाता है।",
      "Do not approve the request or enter your UPI PIN.", T.OTP_SOCIAL_ENGINEERING, "UPI", EN_HI),
    R("UPI_QR_TO_RECEIVE",
      (r"\b(?:scan|qr\s+code|qr)\b.{0,55}\b(?:receive|refund|cashback|get\s+(?:the\s+)?money|advance|payment\s+received)\b",
       r"(?:क्यूआर|QR).{0,40}(?:स्कैन).{0,40}(?:पैसे|रिफंड|कैशबैक|एडवांस)"),
      C.UPI_FRAUD, 2.5, "A QR code starts a payment. It is never needed to receive money.", "QR कोड स्कैन करने से भुगतान शुरू होता है; पैसे पाने के लिए QR स्कैन नहीं करना पड़ता।",
      "Do not scan the QR code or enter a UPI PIN.", T.TOO_GOOD_TO_BE_TRUE, "UPI", ("en", "hi")),
    R("UPI_WRONG_TRANSFER",
      (r"\bsent\s+(?:by\s+)?mistake\b|\bwrong(?:ly)?\s+(?:transfer(?:red)?|sent|credited)\b|\bmistakenly\s+(?:sent|transferred)\b",
       r"\bgalti\s+se\s+(?:bhej|transfer|aa\s+gaye)",
       r"गलती\s*से.{0,20}(?:भेज|ट्रांसफर|आ\s*गए)"),
      C.UPI_FRAUD, 1.8, "\"I sent money by mistake, please return it\" is a known trick to make you pay twice.", "\"गलती से पैसे भेज दिए\" कहकर पैसे वापस मांगना आम ठगी है।",
      "Check your balance in the bank app; never return money to a stranger directly.", T.RECIPROCITY_TRAP, "UPI", EN_HI),

    # --- tech support / remote access --------------------------------------------
    R("TECH_REMOTE_ACCESS",
      (r"\b(?:anydesk|any\s+desk|teamviewer|quick\s*support|rustdesk|airdroid|remote\s+access|screen\s*shar\w*|share\s+(?:your\s+)?screen)\b",
       r"स्क्रीन\s*शेयर|एनीडेस्क|टीम\s*व्यूअर"),
      C.TECH_SUPPORT, 3.0, "Remote-access apps let a stranger see or control your phone.", "रिमोट एक्सेस ऐप से कोई आपके फोन को देख या कंट्रोल कर सकता है।",
      "Do not install the app or share your screen; disconnect if access was given.", T.AUTHORITY_IMPERSONATION, "REMOTE", ("en", "hi")),
    R("TECH_FAKE_CARE",
      (r"\b(?:customer\s+care|helpline|support\s+number|toll[\s-]?free)\b.{0,45}\b(?:bank|upi|paytm|phonepe|amazon|flipkart|microsoft|refund)\b",),
      C.TECH_SUPPORT, 1.0, "Customer-care numbers in messages or search results can be fake.", "मैसेज या सर्च रिज़ल्ट में मिला कस्टमर केयर नंबर नकली हो सकता है।",
      "Call only the number shown in the official app or website.", T.AUTHORITY_IMPERSONATION, "CONTACT"),

    # --- lottery / prize ---------------------------------------------------------
    R("PRIZE_WON",
      (r"\b(?:you\s+have\s+won|you\s+won|winner|lucky\s+draw|kbc|lottery|jackpot|prize\s+money)\b|\bcongratulations\b.{0,40}\b(?:won|selected|winner|lucky)\b",
       r"\b(?:aapne\s+jeeta|aap\s+jeet\s+gaye|lucky\s+draw\s+(?:me|mein)|inaam\s+jeeta)\b",
       r"लॉटरी|इनाम\s*(?:जीता|मिला|राशि)|विजेता|आपने\s*जीत|लकी\s*ड्रा|केबीसी|जैकपॉट"),
      C.LOTTERY_PRIZE, 1.8, "Unexpected prizes are used to demand fees or personal details.", "अचानक इनाम या लॉटरी का संदेश अक्सर धोखाधड़ी होता है।",
      "Do not pay a fee or share details to claim a prize.", T.TOO_GOOD_TO_BE_TRUE, "REWARD", EN_HI),
    R("PRIZE_CLAIM_FEE",
      (r"\b(?:claim|prize|lottery|winning|winner|lucky\s+draw|won)\b.{0,60}\b(?:fee|tax|gst|charges?|deposit|processing)\b|\b(?:tax|gst)\b.{0,30}\b(?:prize|receive|claim)\b",
       r"(?:इनाम|लॉटरी).{0,40}(?:टैक्स|शुल्क|फीस|जमा)"),
      C.LOTTERY_PRIZE, 2.0, "Paying a fee or tax to release a prize is the scam itself.", "इनाम पाने के लिए टैक्स या फीस भरवाना ही ठगी है।",
      "Do not pay anything to claim a prize.", T.PROCESSING_FEE_TRAP, "FEE", ("en", "hi")),

    # --- fake / task jobs ----------------------------------------------------------
    R("JOB_TASK",
      (r"\b(?:rate|review|like|subscribe\s+to|follow)\s+(?:hotels?|products?|videos?|restaurants?|youtube|channels?|movies?|google\s+maps)\b|\bpart[\s-]?time\s+(?:job|work|income|earning)\b|\bwork\s+from\s+home\b|\bdata\s+entry\b|\b(?:prepaid|merchant|vip)\s+tasks?\b|\btask\s+(?:job|based|work)\b|\bearn\b.{0,25}\b(?:per\s+(?:task|hour|day|like|review)|daily|every\s+day|a\s+day)\b",
       r"\bghar\s+baithe\b.{0,25}\b(?:kamay\w*|kamao|kamaiye|income|paise|earning)\b|\broz(?:ana)?\b.{0,15}\bkama|\b(?:video|photo|post|hotel|product)s?\s+like\s+kar\w+\b|\blike\s+ke\s+\d+\s*(?:rupaye|rs)\b|\bonline\s+(?:kaam|work)\b.{0,30}\b(?:kamai|paise|income|achhi)\b",
       r"पार्ट\s*टाइम|घर\s*बैठे.{0,25}(?:कमाएं|कमाएँ|कमाई|पैसे|कमाइए|कमा\s*सकते)|रोज़?ाना.{0,15}(?:कमा|कमाई)|टास्क\s*(?:जॉब|पूरा|करें)|ऑनलाइन\s*(?:काम|जॉब|नौकरी).{0,30}(?:कमाई|पैसे|अच्छी)|(?:वीडियो|होटल|पोस्ट).{0,15}(?:लाइक|रेटिंग)\s*(?:करें|दें|करो)"),
      C.FAKE_JOB, 2.2, "Easy-income task offers turn into deposit scams.", "आसान कमाई या टास्क जॉब के नाम पर बाद में पैसे जमा करवाए जाते हैं।",
      "Real jobs never ask you to pay. Do not deposit money for tasks.", T.TOO_GOOD_TO_BE_TRUE, "EASY_MONEY", EN_HI),
    R("JOB_TASK_DEPOSIT",
      (r"\b(?:deposit|pay|send|invest)\b.{0,30}\b(?:rs\.?\s*)?[\d,]{3,}\b.{0,45}\b(?:you\s+will\s+get|get|receive|return|back|credited?)\b.{0,25}\b(?:rs\.?\s*)?[\d,]{3,}\b|\b(?:next|another|final)\s+(?:merchant\s+|prepaid\s+)?task\b.{0,40}\b(?:deposit|pay|recharge)\b|\btasks?\s+(?:are\s+)?complete[d]?\b.{0,60}\b(?:deposit|pay|next\s+task)\b",
       r"\b(?:deposit|jama)\s+kar\w*\b.{0,45}\b(?:wapas|vapas|milega|milenge)\b|\btask\s+complete\b.{0,50}\b(?:deposit|jama|paise)\b",
       r"(?:जमा\s*(?:करें|करो|कीजिए)).{0,50}(?:वापस|मिलेंगे|मिलेगा)|टास्क\s*(?:पूरे?|पूरा).{0,50}(?:जमा|भुगतान)"),
      C.FAKE_JOB, 2.8, "Small payouts first, then a bigger 'task deposit' that never comes back.", "पहले छोटी कमाई, फिर बड़ी रकम जमा करवाकर पैसा हड़प लिया जाता है।",
      "Stop now and do not deposit. Earlier small payouts are bait.", T.RECIPROCITY_TRAP, "TASK_DEPOSIT", EN_HI),

    R("JOB_SELECTED_FEE",
      (r"\b(?:selected|shortlisted|appointed|hired)\b.{0,60}\b(?:fee|deposit|pay|charge|security\s+amount)\b|\boffer\s+letter\b.{0,40}\b(?:fee|pay|deposit|charge)\b",
       r"(?:चयन|चयनित|नौकरी|आईडी\s*सक्रिय).{0,45}(?:शुल्क|फीस|जमा\s*राशि|सिक्योरिटी|पंजीकरण)|(?:पंजीकरण|रजिस्ट्रेशन)\s*शुल्क.{0,30}(?:जमा|भेज)",
       r"\b(?:registration|joining|training)\s+(?:ke|ki|ka)\s+\d+\s*(?:rupaye|rs|bhej\w*)\b|\b(?:fees?|paise)\s+bhej\w*\b.{0,30}\b(?:job|kaam|loan|training)\b"),
      C.FAKE_JOB, 2.2, "A job that asks for a fee or deposit is not a real job.", "जो नौकरी फीस या जमा राशि मांगे वह असली नहीं है।",
      "Do not pay any fee for a job offer.", T.PROCESSING_FEE_TRAP, "FEE", ("en", "hi")),

    # --- investment / Ponzi --------------------------------------------------------
    R("INVEST_TIPS",
      (r"\b(?:stock|share\s+market|trading|crypto|forex|ipo)\b.{0,30}\b(?:tips?|signals?|group|vip|allotment|guidance)\b|\binstitutional\s+(?:account|trading)\b|\b(?:95|99|100)\s*%\s*accurate\b|\bsure\s*shot\s+(?:profit|returns?|tips?)\b|\bmultibagger\b",
       r"\b(?:vip|stock|trading|ipo)\b.{0,30}\b(?:group|tips)\b.{0,40}\b(?:join|pakka|guaranteed|profit)\w*\b|\bpakka\s+profit\b|\bprofit\s+(?:pakka|guaranteed)\b",
       r"(?:शेयर|स्टॉक|ट्रेडिंग|क्रिप्टो).{0,20}(?:टिप्स|ग्रुप|सिग्नल)"),
      C.INVESTMENT_FRAUD, 1.6, "Tip groups and 'accurate signals' are how fake trading apps recruit victims.", "टिप्स ग्रुप और पक्के सिग्नल नकली ट्रेडिंग ऐप में फँसाने का तरीका हैं।",
      "Invest only through SEBI-registered brokers you found yourself.", T.SOCIAL_PROOF_FABRICATION, "INVEST", ("en", "hi")),
    R("PONZI_GUARANTEED",
      (r"\b(?:guaranteed|assured|fixed)\s+(?:returns?|profit|income|roi|earning)\b|\b\d{1,3}\s*%\s*(?:daily|per\s+day|monthly|per\s+month|weekly|guaranteed|returns?)\b|\bdouble\s+your\s+(?:money|investment)\b",
       r"\b(?:paisa|paise|rakam)\s+double\b|\b(?:guaranteed|pakka|daily)\s+munafa\b",
       r"गारंटीड?\s*(?:रिटर्न|मुनाफ़?ा)|(?:रोज़?ाना|रोजाना|हर\s*दिन|निश्चित|पक्का)\s*(?:मुनाफ़?ा|रिटर्न|कमाई)|पैसा\s*डबल|मुनाफ़?ा\s*पक्का"),
      C.PONZI_MLM, 2.6, "No legitimate investment can guarantee a fixed or daily return.", "कोई भी वैध निवेश रोज़ाना या निश्चित मुनाफ़े की गारंटी नहीं दे सकता।",
      "Treat guaranteed-return claims as fraud. Verify with SEBI or RBI before paying.", T.TOO_GOOD_TO_BE_TRUE, "EASY_MONEY", EN_HI),
    R("PONZI_REFERRAL",
      (r"\b(?:referral\s+(?:bonus|income|commission)|refer\s+(?:and|&)\s+earn|refer\s+friends?|downline|upline|level\s+income|binary\s+(?:plan|income)|matrix\s+plan|team\s+income)\b",
       r"रेफरल|डाउनलाइन|अपलाइन|लेवल\s*इनकम"),
      C.PONZI_MLM, 2.2, "Income that depends on recruiting others is the defining feature of a Ponzi or MLM scheme.", "दूसरों को जोड़ने पर मिलने वाली कमाई Ponzi या MLM योजना की पहचान है।",
      "Do not join or deposit. Recruitment-based income collapses by design.", T.SOCIAL_PROOF_FABRICATION, "RECRUIT", ("en", "hi")),
    R("PONZI_JOINING",
      (r"\b(?:joining\s+(?:fee|package|amount)|registration\s+package|activate\s+your\s+id|id\s+activation|starter\s+package)\b",
       r"(?:जॉइनिंग|ज्वाइनिंग)\s*(?:पैकेज|फीस|शुल्क)"),
      C.PONZI_MLM, 1.8, "An upfront joining package to start earning is a classic Ponzi entry fee.", "कमाई शुरू करने के लिए joining fee माँगना Ponzi योजना का सामान्य तरीका है।",
      "Do not pay a joining or activation fee to start earning.", T.PROCESSING_FEE_TRAP, "FEE", ("en", "hi")),

    # --- loan apps --------------------------------------------------------------------
    R("LOAN_INSTANT",
      (r"\b(?:instant|quick|turant|pre-?approved)\s+(?:personal\s+)?loan\b|\bloan\s+in\s+(?:\d+\s*)?(?:minutes?|mins?|hours?)\b",
       r"\bturant\s+loan\b|\bloan\s+(?:milega|le\s+lo)\b.{0,20}\b(?:turant|minute)",
       r"(?:तुरंत|इंस्टेंट|फ़ौरन)\s*लोन|लोन\s*(?:मिनटों|मिनट)\s*में"),
      C.LOAN_APP_FRAUD, 1.6, "Instant-loan offers with no checks are a common predatory-app lure.", "बिना जांच के तुरंत लोन का वादा अक्सर धोखाधड़ी वाले ऐप का संकेत है।",
      "Borrow only from an RBI-regulated lender.", T.TOO_GOOD_TO_BE_TRUE, "LOAN_SPEED", EN_HI),
    R("LOAN_APPROVED_FEE",
      (r"\b(?:loan|amount)\b.{0,40}\b(?:approved|sanctioned|pre-?approved)\b.{0,60}\b(?:fee|charges?|deposit|pay|transfer|send)\b|\bloan\b.{0,40}\bprocessing\s+fee\b",
       r"\bloan\s+approve\b.{0,50}\b(?:fee|bhejo|bhej\s+do|jama)\b",
       r"लोन\s*(?:स्वीकृत|अप्रूव|मंज़ूर).{0,50}(?:शुल्क|फीस|जमा|भेज)"),
      C.LOAN_APP_FRAUD, 2.6, "A fee demanded before a loan is disbursed is the scam itself.", "लोन मिलने से पहले फीस मांगना ही ठगी है।",
      "A regulated lender deducts charges from the disbursed amount; never pay in advance.", T.PROCESSING_FEE_TRAP, "LOAN_FEE", EN_HI),

    R("LOAN_PERMISSIONS",
      (r"\b(?:allow|grant|give|enable)\b.{0,30}\b(?:contacts?|sms|gallery|photos?|storage)\b.{0,30}\b(?:permission|access)\b|\b(?:contacts?|sms)\s+(?:and|&)\s+(?:sms|contacts?)\s+permission\b",
       r"(?:संपर्क|कॉन्टैक्ट|एसएमएस).{0,25}(?:अनुमति|परमिशन|एक्सेस)"),
      C.LOAN_APP_FRAUD, 2.4, "A lender that needs your contacts and SMS plans to harass you with them.", "जो ऐप आपके contacts और SMS माँगे, वह बाद में उनसे परेशान करता है।",
      "Never grant contacts or SMS access to a loan app.", T.AUTHORITY_IMPERSONATION, "LOAN_PERMS", ("en", "hi")),

    R("LOAN_NO_CHECKS",
      (r"\bno\s+(?:cibil|credit\s+check|documents?|paperwork|income\s+proof)\b|\bonly\s+aadhaar\b|\baadhaar\s+(?:card\s+)?se\s+loan\b|\bwithout\s+(?:cibil|documents?)\b",
       r"\bbina\s+(?:cibil|kagaz|document)",
       r"बिना\s*(?:सिबिल|कागज़?|दस्तावेज़?)|सिर्फ़?\s*आधार\s*(?:से|पर)"),
      C.LOAN_APP_FRAUD, 2.0, "No credit check and Aadhaar-only approval indicate an unregulated lender.", "बिना CIBIL या दस्तावेज़ के लोन देने वाले ऐप अक्सर गैर-कानूनी होते हैं।",
      "Do not grant contact or SMS permissions to an unverified loan app.", T.TOO_GOOD_TO_BE_TRUE, "LOAN_NO_CHECK", EN_HI),
    R("LOAN_HARASSMENT",
      (r"\b(?:loan\s+recovery|recovery\s+agent|your\s+contacts?\s+will\s+be\s+(?:informed|called|messaged)|photos?\s+will\s+be\s+(?:sent|shared|morphed)|morphed\s+photos?)\b",
       r"\b(?:tumhare|aapke|tere)\s+(?:saare\s+)?contacts?\b.{0,40}\b(?:bhej|call|photo|message)\w*\b|\bphoto\s+bhej\s+(?:denge|dunga)\b|\bloan\s+(?:time\s+par\s+)?nahi\s+chukaya\b",
       r"(?:आपके\s*)?(?:संपर्कों|कॉन्टैक्ट|रिश्तेदारों).{0,35}(?:भेज|बता|कॉल)|रिकवरी\s*एजेंट|फोटो\s*(?:वायरल|भेज)"),
      C.LOAN_APP_FRAUD, 2.8, "Threatening to contact your phonebook is illegal loan-app harassment.", "आपके contacts को फोन करने या फोटो भेजने की धमकी गैर-कानूनी वसूली है।",
      "Do not pay under threat. Keep screenshots and report at 1930.", T.FEAR_INDUCTION, "THREAT", ("en", "hi")),

    # --- betting ------------------------------------------------------------------------
    R("BET_ID",
      (r"\b(?:betting\s+id|bet\s+id|cricket\s+id|online\s+book|fancy\s+rate|satta|matka|teer\s+result|colou?r\s+prediction|aviator\s+(?:game|predictor))\b",
       r"सट्टा|बेटिंग\s*आईडी|क्रिकेट\s*आईडी|मटका"),
      C.BETTING_GAMBLING, 2.4, "Betting IDs and prediction games are run by illegal gambling operations.", "Betting ID और prediction game अवैध सट्टेबाज़ी का हिस्सा हैं।",
      "Do not deposit money. This kind of online betting is illegal in most states.", T.TOO_GOOD_TO_BE_TRUE, "BET", ("en", "hi")),
    R("BET_BONUS",
      (r"\b(?:deposit\s+bonus|welcome\s+bonus|instant\s+withdrawal|100\s*%\s*(?:winning|sure)\s*(?:tips?|prediction)|sure\s+shot\s+(?:tips?|win))\b",),
      C.BETTING_GAMBLING, 1.6, "Guaranteed winnings and deposit bonuses pull users into betting platforms.", "पक्की जीत और deposit bonus के वादे सट्टेबाज़ी में फँसाने के लिए होते हैं।",
      "Do not deposit. Guaranteed winning tips do not exist.", T.SOCIAL_PROOF_FABRICATION, "BET"),

    # --- utility bills ------------------------------------------------------------------
    R("UTIL_DISCONNECT",
      (r"\b(?:electricity|power|bijli|light)\b.{0,60}\b(?:disconnect(?:ed|ion)?|cut\s*off|will\s+be\s+cut|band\s+ho)\b|\bupdate\s+(?:your\s+)?(?:electricity\s+)?meter\b|\b(?:gas|water)\s+(?:connection|supply)\b.{0,40}\b(?:disconnect\w*|cut|band)\b",
       r"\bbijli\b.{0,35}\b(?:kat|cut|band)\s*\w*\b|\b(?:connection|supply)\s+(?:aaj\s+)?(?:band|kat)\b|\bsmart\s+meter\s+update\b",
       r"बिजली.{0,40}(?:कट|काट|बंद|कनेक्शन\s*काट|सप्लाई\s*बंद)|बिजली\s*बिल.{0,40}(?:बकाया|अपडेट\s*नहीं|भुगतान\s*नहीं)|स्मार्ट\s*मीटर\s*अपडेट|सप्लाई\s*बंद"),
      C.UTILITY_BILL_SCAM, 2.4, "Threats to cut electricity tonight are a widespread phishing lure.", "आज रात बिजली काटने की धमकी एक आम ठगी का तरीका है।",
      "Check your bill only in the discom's official app or website; dial 1912.", T.FEAR_INDUCTION, "BLOCK", EN_HI),
    R("UTIL_OFFICER_CALL",
      (r"\b(?:call|contact|whatsapp)\b.{0,30}\b(?:electricity|bijli|discom)\s+(?:officer|office|department|helpline)\b|\b(?:jvvnl|avvnl|jdvvnl|jaipur\s+discom|ajmer\s+discom|jodhpur\s+discom)\b",
       r"बिजली\s*(?:अधिकारी|विभाग|ऑफिसर).{0,30}(?:कॉल|संपर्क|फोन)"),
      C.UTILITY_BILL_SCAM, 1.4, "Discoms do not ask you to call an 'electricity officer' on a mobile number.", "डिस्कॉम कभी निजी नंबर पर बिजली अधिकारी को कॉल करने को नहीं कहता।",
      "Use the helpline printed on your bill.", T.AUTHORITY_IMPERSONATION, "AUTHORITY", ("en", "hi")),

    # --- government impersonation ---------------------------------------------------
    R("GOV_NAME",
      (r"\b(?:pm\s+kisan|pm\s+awas|aadhaar|epfo|income\s+tax|it\s+department|rbi|uidai|trai|ministry|jan\s*aadhaar|sso\s+id|e-?mitra|bhamashah|ration\s+card|gas\s+subsidy|pension)\b",
       r"जन\s*आधार|पीएम\s*किसान|आयकर|आधार\s*कार्ड|राशन\s*कार्ड|ई-?मित्र|एसएसओ|भामाशाह|पेंशन"),
      C.GOVERNMENT_IMPERSONATION, 0.6, "Government names are copied to gain trust.", "सरकारी नाम का उपयोग भरोसा जीतने के लिए किया जाता है।",
      "Verify only on the official government website or e-Mitra.", T.AUTHORITY_IMPERSONATION, "AUTHORITY", ("en", "hi")),
    R("GOV_ID_THREAT",
      (r"\b(?:jan\s*aadhaar|sso\s*id|aadhaar|ration\s+card|pm\s+kisan|pension|pan\s+card|voter\s+id)\b.{0,50}\b(?:block\w*|cancel\w*|suspend\w*|deactivat\w*|expir\w*|band|update\s+now|verify\s+now)\b",
       r"(?:जन\s*आधार|आधार|राशन\s*कार्ड|पेंशन|पैन\s*कार्ड|एसएसओ).{0,40}(?:रद्द|बंद|निरस्त|ब्लॉक|अपडेट\s*करें)"),
      C.GOVERNMENT_IMPERSONATION, 1.8, "Threats to cancel a government ID or benefit push you onto fake pages.", "सरकारी पहचान या योजना रद्द करने की धमकी नकली पेज पर ले जाने के लिए होती है।",
      "Check only on rajasthan.gov.in portals or at an e-Mitra kiosk.", T.FEAR_INDUCTION, "BLOCK", ("en", "hi")),
    R("GOV_TAX_REFUND",
      (r"\b(?:income\s+tax|it)\s+refund\b|\btax\s+refund\b.{0,40}\b(?:click|link|claim|approved|credited)\b|\brefund\s+(?:of|amount)\b.{0,30}\b(?:approved|pending)\b.{0,40}\b(?:link|click|account\s+details)\b",
       r"(?:आयकर|टैक्स)\s*रिफंड"),
      C.GOVERNMENT_IMPERSONATION, 2.0, "Tax-refund messages with links are used to steal bank details.", "टैक्स रिफंड के लिंक वाले संदेश बैंक विवरण चुराने के लिए होते हैं।",
      "Check refunds only on incometax.gov.in after logging in yourself.", T.TOO_GOOD_TO_BE_TRUE, "REWARD", ("en", "hi")),

    # --- digital arrest --------------------------------------------------------------
    R("DA_EXPLICIT",
      (r"\bdigital\s*arrest\b|\b(?:online|virtual|video)\s+arrest\b",
       r"डिजिटल\s*(?:अरेस्ट|गिरफ़?्तारी)"),
      C.DIGITAL_ARREST, 4.0, "There is no 'digital arrest' in Indian law. Police never arrest anyone on a video call.", "भारतीय कानून में 'डिजिटल अरेस्ट' जैसा कुछ नहीं है। पुलिस वीडियो कॉल पर गिरफ्तार नहीं करती।",
      "Disconnect, tell your family, and report the number at 1930.", T.AUTHORITY_IMPERSONATION, "ARREST", ("en", "hi"),
      "I4C / MHA public advisory on 'digital arrest' (2024)"),
    R("DA_AGENCY_THREAT",
      (r"\b(?:cbi|ed|enforcement\s+directorate|ncb|narcotics(?:\s+bureau)?|customs|trai|cyber\s+(?:crime\s+)?(?:cell|police|branch)|crime\s+branch|mumbai\s+police|delhi\s+police|interpol|supreme\s+court|high\s+court|court)\b.{0,90}\b(?:arrest\w*|warrant|money\s+laundering|drugs?|narcotics?|parcel|case\s+(?:has\s+been\s+)?(?:registered|filed|booked)|fir|illegal|seized|aadhaar\s+(?:misused|linked))\b",
       r"\b(?:police|cbi|ed)\b.{0,40}\b(?:case\s+darj|giraftar|giraftari|arrest\s+ho)",
       r"(?:सीबीआई|पुलिस|ईडी|नारकोटिक्स|एनसीबी|कस्टम|क्राइम\s*ब्रांच|अदालत|कोर्ट|ट्राई).{0,70}(?:गिरफ़?्तार|वारंट|केस\s*दर्ज|मनी\s*लॉन्ड्रिंग|ड्रग्स|एफआईआर|अवैध)"),
      C.DIGITAL_ARREST, 2.6, "Callers posing as CBI, ED, customs or police threaten arrest to extort money.", "सीबीआई, ईडी, कस्टम या पुलिस बनकर गिरफ्तारी की धमकी देकर पैसे ऐंठे जाते हैं।",
      "Real agencies do not threaten arrest by phone or ask for money. Disconnect and call 1930.", T.AUTHORITY_IMPERSONATION, "ARREST", EN_HI,
      "I4C / MHA public advisory on 'digital arrest' (2024)"),
    R("DA_STAY_ON_CALL",
      (r"\b(?:do\s*n[o']?t|don't|never)\s+(?:disconnect|cut|end|leave)\s+(?:the\s+)?(?:call|video|line)\b|\bstay\s+on\s+(?:the\s+)?(?:video\s+)?call\b|\bvideo\s+call\b.{0,40}\b(?:statement|verification|interrogation|investigation|enquiry)\b",
       r"\bcall\s+(?:mat|na)\s+(?:kaatna|kato|katna)\b",
       r"कॉल\s*(?:न|ना|मत)\s*(?:काटें|काटना|काटो)|वीडियो\s*कॉल.{0,30}(?:बयान|जांच|पूछताछ)"),
      C.DIGITAL_ARREST, 2.4, "Keeping you on a video call stops you from checking with anyone.", "आपको वीडियो कॉल पर रोके रखना ताकि आप किसी से पूछ न सकें, यही ठगी का तरीका है।",
      "End the call. No investigation happens on a video call.", T.FEAR_INDUCTION, "ISOLATE", EN_HI,
      "I4C / MHA public advisory on 'digital arrest' (2024)"),
    R("DA_SAFE_ACCOUNT",
      (r"\b(?:transfer|move|deposit|send)\b.{0,40}\b(?:safe|secure|rbi|verification|government|escrow|supervision)\s+account\b|\bfor\s+(?:fund\s+|money\s+)?verification\b.{0,40}\b(?:transfer|deposit|send)\b|\b(?:bail|settlement|clearance)\s+(?:amount|money)\b",
       r"\b(?:bail|zamanat)\s+(?:amount|rashi|ke\s+liye)\b.{0,40}\b(?:transfer|bhej|jama)\w*\b",
       r"सत्यापन\s*के\s*लिए.{0,25}(?:पैसे|रकम|राशि|ट्रांसफर)|(?:सुरक्षित|आरबीआई)\s*खाते|(?:जमानत|ज़मानत)\s*(?:राशि|रकम).{0,30}(?:ट्रांसफर|भेज|जमा)"),
      C.DIGITAL_ARREST, 2.8, "No agency asks you to move money to a 'safe' or 'verification' account.", "कोई एजेंसी 'सुरक्षित' या 'सत्यापन' खाते में पैसे भेजने को नहीं कहती।",
      "Do not transfer any money. Call 1930 now.", T.AUTHORITY_IMPERSONATION, "MONEY_DEMAND", ("en", "hi"),
      "I4C / MHA public advisory on 'digital arrest' (2024)"),
    R("DA_DRUG_PARCEL",
      (r"\b(?:parcel|package|courier|shipment)\b.{0,60}\b(?:drugs?|narcotics?|mdma|ganja|passports?|illegal\s+items?|contraband)\b|\b(?:drugs?|narcotics?)\b.{0,40}\b(?:parcel|package|courier)\b",
       r"(?:पार्सल|कूरियर).{0,40}(?:ड्रग्स|नशीले|अवैध)|ड्रग्स.{0,30}पार्सल"),
      C.DIGITAL_ARREST, 2.2, "A 'parcel with drugs in your name' is the opening line of digital-arrest scams.", "'आपके नाम के पार्सल में ड्रग्स' डिजिटल अरेस्ट ठगी की शुरुआत होती है।",
      "Disconnect. Couriers and police do not settle cases by phone.", T.FEAR_INDUCTION, "ARREST", ("en", "hi")),
    R("DA_SIM_DISCONNECT",
      (r"\b(?:your|aapka)\s+(?:mobile\s+)?(?:number|sim)\b.{0,50}\b(?:disconnect\w*|block\w*|band)\b.{0,50}\b(?:2\s*hours|two\s+hours|illegal|trai|complaint)\b",
       r"(?:आपका\s*)?(?:नंबर|सिम).{0,30}(?:बंद|ब्लॉक).{0,30}(?:2\s*घंटे|ट्राई|शिकायत)"),
      C.DIGITAL_ARREST, 2.0, "'TRAI will block your number in 2 hours' is a scripted opening for extortion calls.", "'2 घंटे में आपका नंबर बंद होगा' कहकर ठगी की शुरुआत की जाती है।",
      "TRAI does not call to block numbers. Disconnect.", T.FEAR_INDUCTION, "ARREST", ("en", "hi")),

    # --- malicious apps (APKs sent by message) --------------------------------------
    R("APP_APK_FILE",
      (r"\.apk\b|\bapk\s+(?:file|download|link)\b|\bdownload\b.{0,30}\bapk\b",
       r"एपीके|\.apk"),
      C.MALICIOUS_APP, 2.4, "An app file sent by message can read your SMS and steal OTPs.", "संदेश से भेजी गई ऐप फ़ाइल आपके SMS और OTP चुरा सकती है।",
      "Never install .apk files sent on WhatsApp or SMS. Use only the Play Store.", T.AUTHORITY_IMPERSONATION, "APK", ("en", "hi"),
      "CERT-In / state police advisories on malicious APKs"),
    R("APP_CHALLAN",
      (r"\b(?:e-?challan|traffic\s+challan|rto|parivahan|vahan)\b.{0,60}\b(?:\.apk|apk|download|install|app)\b",
       r"चालान.{0,40}(?:ऐप|डाउनलोड|एपीके|इंस्टॉल)"),
      C.MALICIOUS_APP, 2.2, "Challans never come as an app to install.", "चालान कभी इंस्टॉल करने वाले ऐप के रूप में नहीं आता।",
      "Check challans only on echallan.parivahan.gov.in.", T.AUTHORITY_IMPERSONATION, "APK", ("en", "hi")),
    R("APP_INVITE_REWARD",
      (r"\b(?:wedding|shaadi|marriage|invitation|invite|card|pm\s*kisan|reward\s+points?|bank|yono|customer\s+support)\b.{0,60}\b(?:\.apk|apk\s+file)\b",
       r"(?:शादी|निमंत्रण|पीएम\s*किसान|इनाम).{0,40}(?:एपीके|\.apk)"),
      C.MALICIOUS_APP, 2.0, "Wedding-invite and reward APKs are a known Indian malware lure.", "शादी के निमंत्रण या इनाम वाले APK एक जाना-माना मैलवेयर तरीका है।",
      "Do not open the file. Ask the sender by phone.", T.RECIPROCITY_TRAP, "APK", ("en", "hi")),
    R("APP_INSTALL_FOR",
      (r"\b(?:install|download)\s+(?:this|the|our|below)?\s*(?:app|application)\b.{0,40}\b(?:to|for)\s+(?:get|receive|claim|verify|update|refund|kyc|loan|support)\b|\b(?:install|download)\b.{0,30}\bapp\b.{0,30}\b(?:from\s+(?:this|the)\s+link|link\s+below|this\s+link)\b",
       r"\bapp\s+(?:download|install)\s+kar\w*\b.{0,30}\blink\b",
       r"ऐप\s*(?:डाउनलोड|इंस्टॉल)\s*(?:करें|करके).{0,30}(?:पाएं|प्राप्त|रिफंड|अपडेट)"),
      C.MALICIOUS_APP, 1.4, "Being told to install an app to get a refund or update is a malware lure.", "रिफंड या अपडेट के लिए ऐप इंस्टॉल करवाना मैलवेयर का तरीका है।",
      "Install apps only from the Play Store, and never at a caller's request.", T.AUTHORITY_IMPERSONATION, "APK", ("en", "hi")),

    # --- sextortion -------------------------------------------------------------------
    R("SEX_THREAT",
      (r"\b(?:video|photos?|pics?|clip|recording|screenshots?)\b.{0,40}\b(?:viral|leak\w*|upload\w*|youtube|send\s+to\s+(?:your\s+)?(?:family|contacts|friends|wife|husband))\b|\b(?:nude|naked|obscene|private\s+video|sextortion)\b",
       r"\bviral\s+kar\s+(?:denge|dunga|dungi|doonga)\b",
       r"अश्लील|न्यूड|वायरल\s*कर|वीडियो.{0,30}(?:वायरल|परिवार\s*को\s*भेज|लीक)"),
      C.SEXTORTION, 3.0, "Threats to publish private content are used to force payment.", "निजी सामग्री फैलाने की धमकी देकर पैसे मांगना ब्लैकमेल है।",
      "Do not pay or reply. Keep evidence, block, and report at 1930.", T.FEAR_INDUCTION, "THREAT", EN_HI),
    R("TAC_PAY_OR_ELSE",
      (r"\b(?:pay|send|transfer)\b.{0,40}\bor\s+(?:else|we\s+will|i\s+will|your)\b|\bsend\s+money\s+or\b",
       r"\b(?:paise|paisa)\s+(?:bhejo|do|de\s+do)\s+(?:warna|nahi\s+to)\b",
       r"पैसे\s*(?:भेजो|दो|भेजें)\s*(?:वरना|नहीं\s*तो)"),
      C.UNKNOWN, 1.4, "A 'pay or else' demand is extortion.", "'पैसे दो वरना' जैसी मांग ब्लैकमेल है।",
      "Do not pay under threat. Report it.", T.FEAR_INDUCTION, "THREAT", EN_HI),

    # --- romance / gift ---------------------------------------------------------------
    R("ROM_MONEY",
      (r"\b(?:love\s+you|my\s+love|romance|dating|girlfriend|boyfriend|fianc[eé]e?|darling|sweetheart|soulmate|dear\s+friend\s+from)\b.{0,120}\b(?:customs|fee|money|gift|parcel|bitcoin|crypto|transfer|clearance)\b",),
      C.ROMANCE_SCAM, 2.0, "A new online relationship asking for money or fees is high risk.", "ऑनलाइन रिश्ते में पैसे या फीस मांगना जोखिम का संकेत है।",
      "Do not send money or documents to an online contact.", T.RECIPROCITY_TRAP, "ROMANCE"),
    R("ROM_GIFT_CUSTOMS",
      (r"\bgift\b.{0,60}\b(?:customs|clearance|airport|duty)\b",
       r"\bgift\b.{0,60}\bcustoms\s+fee\b|\bcustoms\s+fee\b.{0,40}\b(?:transfer|bhej|jaldi)\w*\b",
       r"गिफ्ट.{0,40}(?:कस्टम|एयरपोर्ट|ड्यूटी)"),
      C.ROMANCE_SCAM, 2.0, "A 'gift stuck at customs' asking for fees is a known romance scam.", "कस्टम में फँसे गिफ्ट के लिए फीस मांगना जानी-पहचानी ठगी है।",
      "Do not pay customs fees for a gift from an online contact.", T.RECIPROCITY_TRAP, "GIFT_FEE", ("en", "hi", "hinglish")),

    # --- courier ------------------------------------------------------------------------
    R("COURIER_HELD",
      (r"\b(?:fedex|dhl|blue\s*dart|india\s+post|courier|parcel|package|shipment|consignment)\b.{0,60}\b(?:held|on\s+hold|returned|undelivered|could\s+not\s+be\s+delivered|duty|customs|charges?|fee|address\s+(?:is\s+)?(?:incomplete|incorrect|update)|re-?deliver\w*|re-?schedul\w*)\b",
       r"पार्सल.{0,40}(?:रोका|होल्ड|शुल्क|पता\s*(?:अधूरा|गलत|अपडेट))"),
      C.COURIER_SCAM, 1.6, "Unexpected parcel holds or redelivery fees are used to steal card details.", "पार्सल रुकने या दोबारा डिलीवरी शुल्क के बहाने कार्ड विवरण चुराया जाता है।",
      "Track parcels only on the courier's official website.", T.FEAR_INDUCTION, "COURIER", ("en", "hi")),

    # --- marketplace ----------------------------------------------------------------------
    R("MKT_ARMY_BUYER",
      (r"\b(?:army|crpf|bsf|cisf|itbp|military|air\s+force|navy|defence)\s+(?:officer|jawan|man|personnel|person|staff)\b.{0,120}\b(?:olx|transfer\w*|posting|advance|qr|buy|sell|sofa|bike|car|scooty|furniture|rent|flat|room)\b",
       r"\b(?:army|fauji)\s+(?:wala|hoon|hu)\b",
       r"(?:आर्मी|सेना|फौजी|फ़ौजी).{0,80}(?:ट्रांसफर|पोस्टिंग|एडवांस|क्यूआर|किराए|बेच)"),
      C.MARKETPLACE_FRAUD, 2.6, "'Army officer on transfer' buyers and sellers are a well-known OLX scam.", "'ट्रांसफर पर आर्मी अफसर' बनकर खरीद-बिक्री की ठगी आम है।",
      "Meet in person; never scan a QR or pay an advance to a stranger.", T.AUTHORITY_IMPERSONATION, "MARKET", EN_HI),
    R("MKT_ADVANCE",
      (r"\b(?:olx|quikr|marketplace|facebook\s+marketplace)\b.{0,80}\b(?:advance|qr|scan|token\s+amount|pay\s+first)\b",),
      C.MARKETPLACE_FRAUD, 1.6, "Asking for an advance or a QR scan on a marketplace deal is a common trick.", "मार्केटप्लेस सौदे में एडवांस या QR स्कैन मांगना आम चाल है।",
      "Pay only on delivery, in person.", T.TOO_GOOD_TO_BE_TRUE, "MARKET"),

    # --- phishing credentials ---------------------------------------------------------
    R("PHISH_LOGIN",
      (r"\b(?:login|log\s+in|sign\s+in|verify|re-?activate|unlock|update)\b.{0,30}\b(?:at|on|via|using|here)\b\s*:?\s*(?:https?://|www\.|[a-z0-9-]+\.(?:in|com|xyz|top|cyou|online|site|info|net|co))",),
      C.PHISHING_LINK, 1.4, "Being sent to a link to log in or verify is how credentials are stolen.", "लिंक पर लॉगिन या वेरिफाई करवाकर पासवर्ड चुराए जाते हैं।",
      "Open the official app yourself instead of the link.", T.AUTHORITY_IMPERSONATION, "LINK"),

    # --- guards: legitimate structures (negative weights) -------------------------
    R("GUARD_BANK_ALERT",
      (r"\b(?:debited|credited|withdrawn|spent)\b.{0,80}\b(?:a/c|acct|account|card)\b\s*(?:no\.?\s*)?(?:ending\s+(?:with\s+)?)?(?:xx+|\*+)\s*\d{3,4}\b",
       r"\b(?:avl\.?\s*bal|available\s+balance|avbl\s+bal)\b",
       r"(?:डेबिट|क्रेडिट|जमा|निकासी).{0,60}(?:खाता|खाते)\s*(?:XX|xx|\*+)\d{3,4}"),
      C.UNKNOWN, -2.0, "Matches the structure of a genuine bank transaction alert.", "यह असली बैंक लेनदेन सूचना जैसा है।",
      "If you did not make this transaction, call the number on your card.", None, "LEGIT_ALERT", ("en", "hi"), "Reviewed hard-negative guard"),
    R("GUARD_OTP_NOTICE",
      (r"\b(?:otp|one\s+time\s+password|verification\s+code)\b.{0,100}\b(?:do\s+not|don't|never|not\s+to)\s+(?:share|disclose|tell)\b|\b(?:do\s+not|don't|never)\s+share\b.{0,40}\b(?:otp|code|pin)\b",
       r"(?:ओटीपी|OTP).{0,60}(?:किसी\s*(?:के\s*)?(?:साथ|को)\s*(?:साझा|शेयर|न\s*बताएं)|साझा\s*न\s*करें)"),
      C.UNKNOWN, -1.8, "An OTP message that warns you not to share it is the normal, genuine format.", "जो OTP संदेश उसे साझा न करने की चेतावनी देता है, वह सामान्य असली संदेश है।",
      "Never share the code, even if someone calls claiming to be the bank.", None, "LEGIT_OTP", ("en", "hi"), "Reviewed hard-negative guard"),
    R("GUARD_ADVISORY",
      (r"\b(?:never|will\s+never|does\s+not|do(?:es)?\s+not|don't|no)\s+(?:ask|call|request|send|such\s+thing|police\s+officer)\b.{0,50}\b(?:otp|pin|password|cvv|kyc|details|money|link|video\s+call|digital\s+arrest)\b"
       r"|\b(?:beware|be\s+alert|stay\s+alert|awareness|fraudsters?\s+are|scammers?\s+are|is\s+a\s+red\s+flag|are\s+a\s+red\s+flag)\b"
       r"|\breport\s+(?:it\s+)?(?:at|to|on)\s+(?:1930|cybercrime)\b"
       r"|\b(?:do\s+not|don't|never)\s+(?:click|install|share|open)\b.{0,60}\b(?:unknown|any|apk|link)\b"
       r"|\bcheck\s+(?:if|whether)\b.{0,60}\b(?:registered|sebi|rbi|official)\b",
       r"\bkabhi\s+(?:nahi|nahin)\s+(?:mangta|maangta|mangte|maangte|puchta|karti|karta)\b"
       r"|\b(?:na|nahi|nahin|mat)\s+kar(?:ein|o|iye|na)\b(?!.{0,40}\b(?:turant|abhi|jaldi)\b)"
       r"|\b(?:fraud|thagi|scam)\s+(?:ka|ke|hone)\b.{0,30}\b(?:sign|nishani|1930|report)\b"
       r"|\b(?:check|verify)\s+kar(?:o|ein|na)\b",
       r"कभी\s*(?:भी\s*)?(?:नहीं\s*)?(?:मांगत\w*|माँगत\w*|पूछत\w*|करत\w*)"
       r"|सावधान|सतर्क|जागरूक|धोखाधड़ी\s*का\s*संकेत|फर्जी\s*संदेशों\s*से"
       r"|(?:कभी|किसी|अनजान|अज्ञात|कोई\s*भी|फर्जी|नकली)[^।\n]{0,45}(?:\u0928|\u092e\u0924)\s*(?:करें|करो|कीजिए|खोलें|दें|बताएं|बताएँ)"
       r"|(?:क्लिक|इंस्टॉल|शेयर|साझा|डाउनलोड|भुगतान)\s*(?:\u0928|\u092e\u0924)\s*(?:करें|करो|कीजिए)"
       r"|(?:जाँचें|जांचें|अवश्य\s*जाँच)"),
      C.UNKNOWN, -3.2, "Reads like an official safety advisory rather than a request.", "यह किसी आधिकारिक सुरक्षा सलाह जैसा है, कोई मांग नहीं।",
      "Follow the advisory; verify any request through official channels.", None, "LEGIT_ADVISORY", EN_HI, "Reviewed hard-negative guard"),
    R("GUARD_POLICE_SENDER",
      (r"^\s*(?:rajasthan\s+police|jaipur\s+police|cyber\s+cell|i4c|rbi|npci|trai)\s*[:\-]",
       r"-\s*(?:rbi|sbi|hdfc\s+bank|icici\s+bank|axis\s+bank|jvvnl|avvnl|india\s+post|rajasthan\s+police)\s*$",
       r"^\s*(?:राजस्थान\s*पुलिस|जयपुर\s*पुलिस|साइबर\s*सेल|आरबीआई)\s*[:\-]|-\s*(?:आरबीआई|राजस्थान\s*पुलिस)\s*$"),
      C.UNKNOWN, -1.8, "Signed by an organisation in the way its real bulk messages are.", "यह संदेश उसी तरह हस्ताक्षरित है जैसे असली सरकारी संदेश होते हैं।",
      "Still verify anything that asks for money or details.", None, "LEGIT_SENDER", EN_HI, "Reviewed hard-negative guard"),
    R("GUARD_PLANNED_OUTAGE",
      (r"\b(?:scheduled|planned)\s+(?:power\s+)?(?:maintenance|outage|shutdown)\b|\b(?:power|supply)\s+(?:will\s+be\s+)?(?:interrupted|unavailable)\b.{0,60}\bmaintenance\b",
       r"\bmaintenance\s+ke\s+(?:kaaran|karan|wajah)\b",
       r"रखरखाव\s*(?:के\s*कारण|कार्य)|नियोजित\s*(?:कटौती|शटडाउन)"),
      C.UNKNOWN, -2.4, "Describes planned maintenance with a time window, not a payment demand.", "यह नियोजित रखरखाव की सूचना है, भुगतान की मांग नहीं।",
      "No action is needed for a scheduled maintenance notice.", None, "LEGIT_OUTAGE", EN_HI, "Reviewed hard-negative guard"),
    R("GUARD_DELIVERY_OTP",
      (r"\b(?:share|give)\b.{0,30}\b(?:otp|code|pin)\b.{0,40}\b(?:only\s+)?(?:with|to)\s+(?:the\s+)?(?:delivery\s+(?:agent|partner|executive|boy)|driver|captain)\b",),
      C.UNKNOWN, -1.4, "Delivery and ride apps ask you to show a code to the agent at your door.", "डिलीवरी या राइड ऐप दरवाज़े पर एजेंट को कोड दिखाने को कहते हैं।",
      "Share delivery codes only in person with the agent at your door.", None, "LEGIT_OTP", ("en",), "Reviewed hard-negative guard"),
)


DEFAULT_ACTIONS: dict[ScamCategory, list[str]] = {
    C.OTP_THEFT: ["Do not share any OTP, PIN, CVV, password, or screen-sharing code.", "End the conversation and contact the company through its official app or website.", "If you shared details or lost money, call 1930 immediately."],
    C.PHISHING_LINK: ["Do not open the link or install any app from it.", "Verify the request through the organisation's official app or website.", "Block and report the sender if the message is unsolicited."],
    C.KYC_SCAM: ["Do not use the link or number in the message.", "Check your account only through the official bank or telecom app.", "If you entered banking details or lost money, call 1930 immediately."],
    C.UPI_FRAUD: ["Do not approve collect requests or send money to verify an account.", "Open your payment app directly to check your account status.", "If money was lost, call 1930 immediately and notify your bank."],
    C.DIGITAL_ARREST: ["Disconnect the call. No police, CBI, ED or customs officer arrests anyone on a video call.", "Do not transfer money to any 'safe' or 'verification' account.", "Tell your family and report the number at 1930 or cybercrime.gov.in."],
    C.MALICIOUS_APP: ["Do not open or install the .apk file.", "If it is already installed, turn on flight mode, uninstall it and call your bank.", "If money was lost, call 1930 immediately."],
    C.SEXTORTION: ["Do not pay; paying never ends the threats.", "Keep screenshots, block the account and report at 1930 or cybercrime.gov.in.", "Talk to someone you trust; you are the victim, not the offender."],
    C.MARKETPLACE_FRAUD: ["Do not scan a QR or pay an advance to a buyer or seller you have not met.", "Complete deals in person, paying only on delivery.", "Report the listing to the platform and at 1930 if money was lost."],
    C.FAKE_JOB: ["Real jobs never ask for a fee, deposit or 'prepaid task'.", "Leave the group and do not send any more money.", "If money was lost, call 1930 immediately."],
    C.UTILITY_BILL_SCAM: ["Do not call the number in the message.", "Check your bill on the discom's official app or website, or dial 1912.", "If you paid or installed an app, call 1930."],
}

GENERIC_ACTIONS = ["Do not act on the message until you verify it through an official channel.", "Do not share passwords, OTPs, PINs, CVVs, or banking details.", "Block and report the sender if the message was unsolicited or misleading."]

RULES_BY_ID: dict[str, ScamSignalRule] = {rule.rule_id: rule for rule in SCAM_SIGNAL_RULES}
assert len(RULES_BY_ID) == len(SCAM_SIGNAL_RULES), "duplicate rule_id"
