from __future__ import annotations

"""Reviewed offline scam-signal rules used when live AI is unavailable.

These rules are a safety net, not a claim that a sender is criminal. Each rule
is intentionally explainable, version-controlled, and limited to observable
message patterns so PARAKH remains useful during an AI-provider outage.
"""

from dataclasses import dataclass

from app.schemas import PsychologicalTactic, ScamCategory


@dataclass(frozen=True)
class ScamSignalRule:
    pattern: str
    category: ScamCategory
    risk_weight: int
    simple_explanation: str
    hindi_explanation: str
    safe_action: str
    tactic: PsychologicalTactic | None = None


SCAM_SIGNAL_RULES: tuple[ScamSignalRule, ...] = (
    ScamSignalRule(r"\b(?:kyc|verify (?:your )?account|update (?:your )?details)\b", ScamCategory.KYC_SCAM, 22, "Unexpected account verification can be used to steal details.", "अचानक KYC या अकाउंट वेरिफिकेशन का संदेश धोखाधड़ी हो सकता है।", "Open the official bank or telecom app yourself; do not use this message's link.", PsychologicalTactic.AUTHORITY_IMPERSONATION),
    ScamSignalRule(r"\b(?:blocked?|suspend(?:ed)?|service (?:will be )?stop(?:ped)?)\b", ScamCategory.KYC_SCAM, 24, "A threat to block an account is meant to create fear.", "खाता बंद होने की धमकी देकर डराया जा रहा है।", "Do not rush. Check the account only in the official app.", PsychologicalTactic.FEAR_INDUCTION),
    ScamSignalRule(r"\b(?:within|in)\s+(?:\d+|one|two|24)\s*(?:hours?|hrs?)\b|\b(?:urgent|immediately|last date|today only)\b", ScamCategory.UNKNOWN, 18, "Pressure to act quickly can stop you from checking safely.", "जल्दी करने का दबाव आपको जांच करने से रोक सकता है।", "Pause and verify through an independently known official channel.", PsychologicalTactic.FALSE_URGENCY),
    ScamSignalRule(r"\b(?:share|send|tell|provide|give)\b.{0,35}\b(?:otp|one[ -]?time password|cvv|pin|password)\b", ScamCategory.OTP_THEFT, 62, "A real bank or payment app will not ask you to reveal an OTP, PIN, CVV, or password.", "बैंक या पेमेंट ऐप आपसे OTP, PIN, CVV या पासवर्ड नहीं मांगता।", "End the conversation. Do not share any security secret.", PsychologicalTactic.OTP_SOCIAL_ENGINEERING),
    ScamSignalRule(r"\b(?:upi|gpay|phonepe|paytm)\b.{0,55}\b(?:collect|request|approve|pin|receive money|refund)\b", ScamCategory.UPI_FRAUD, 44, "A UPI collect request or PIN can make you pay; receiving money does not need a PIN.", "पैसे पाने के लिए UPI PIN नहीं डालना पड़ता; collect request मंजूर करने से भुगतान हो सकता है।", "Do not approve the request or enter your UPI PIN.", PsychologicalTactic.OTP_SOCIAL_ENGINEERING),
    ScamSignalRule(r"\b(?:scan|qr code|qr)\b.{0,55}\b(?:receive|refund|cashback|money|payment|pin)\b", ScamCategory.UPI_FRAUD, 38, "A QR code can start a payment. It is not needed to receive money.", "QR कोड स्कैन करने से भुगतान शुरू हो सकता है; पैसे पाने के लिए QR स्कैन नहीं करना पड़ता।", "Do not scan the QR code or enter a UPI PIN.", PsychologicalTactic.TOO_GOOD_TO_BE_TRUE),
    ScamSignalRule(r"\b(?:anydesk|teamviewer|quicksupport|remote access|screen share|share screen)\b", ScamCategory.TECH_SUPPORT, 48, "Remote-access apps can let a stranger view or control your device.", "रिमोट एक्सेस ऐप से कोई आपके फोन को देख या कंट्रोल कर सकता है।", "Do not install the app or share your screen; disconnect if access was already given.", PsychologicalTactic.AUTHORITY_IMPERSONATION),
    ScamSignalRule(r"\b(?:won|winner|lucky draw|kbc|lottery|prize)\b", ScamCategory.LOTTERY_PRIZE, 32, "Unexpected prizes are commonly used to demand money or personal details.", "अचानक इनाम या लॉटरी का संदेश अक्सर धोखाधड़ी होता है।", "Do not pay a fee or share details to claim a prize.", PsychologicalTactic.TOO_GOOD_TO_BE_TRUE),
    # Advance-fee demands are a cross-cutting tactic, not a category: a
    # registration fee appears in fake-job, lottery, loan and Ponzi scams alike.
    # Categorised UNKNOWN so it contributes risk without overriding a rule that
    # actually identifies the fraud family.
    ScamSignalRule(r"\b(?:registration fee|joining fee|advance fee|pay.{0,18}(?:fee|charge))\b", ScamCategory.UNKNOWN, 34, "A fee demanded before you receive anything is a common scam pattern.", "कुछ मिलने से पहले फीस मांगना आम धोखाधड़ी का तरीका है।", "Do not pay a fee to receive a prize, refund, or job.", PsychologicalTactic.PROCESSING_FEE_TRAP),
    ScamSignalRule(r"\b(?:processing fee|claim fee|prize money fee)\b", ScamCategory.LOTTERY_PRIZE, 34, "A small fee to unlock a large reward is a common scam pattern.", "बड़े इनाम के लिए छोटी फीस मांगना आम धोखाधड़ी का तरीका है।", "Do not pay a fee to receive a prize.", PsychologicalTactic.PROCESSING_FEE_TRAP),
    ScamSignalRule(r"\b(?:work from home|youtube videos?|like videos?|data entry|earn.{0,25}(?:per hour|daily)|task job)\b", ScamCategory.FAKE_JOB, 32, "Easy-income task offers can turn into payment or deposit scams.", "आसान कमाई या task job के नाम पर पैसे मांगे जा सकते हैं।", "Do not pay a deposit or move the conversation to an unknown app.", PsychologicalTactic.TOO_GOOD_TO_BE_TRUE),
    ScamSignalRule(r"\b(?:telegram|trading group|guaranteed returns?|95% accurate|crypto signals?|double your money)\b", ScamCategory.INVESTMENT_FRAUD, 34, "Guaranteed returns and exclusive groups are high-risk investment signals.", "गारंटीड रिटर्न और secret trading group निवेश धोखाधड़ी के संकेत हैं।", "Do not transfer money for guaranteed returns.", PsychologicalTactic.SOCIAL_PROOF_FABRICATION),
    ScamSignalRule(r"\b(?:pm kisan|pm awas|aadhaar|epfo|income tax refund|rbi|uidai)\b", ScamCategory.GOVERNMENT_IMPERSONATION, 22, "Government names can be copied to gain trust.", "सरकारी नाम का उपयोग भरोसा जीतने के लिए किया जा सकता है।", "Verify only through the official government website or app.", PsychologicalTactic.AUTHORITY_IMPERSONATION),
    ScamSignalRule(r"\b(?:customs|courier|parcel|fedex|package|delivery).{0,45}\b(?:held|duty|charge|release|police case)\b", ScamCategory.COURIER_SCAM, 30, "Unexpected parcel or customs charges should be verified independently.", "कूरियर या कस्टम शुल्क का अचानक संदेश जांचे बिना न मानें।", "Use the courier's official tracking website, not the message link.", PsychologicalTactic.FEAR_INDUCTION),
    ScamSignalRule(r"\b(?:customer care|helpline|support number).{0,45}\b(?:bank|upi|paytm|phonepe|amazon|microsoft)\b", ScamCategory.TECH_SUPPORT, 30, "Search-result and message customer-care numbers can be fake.", "मैसेज या search result में मिला customer care नंबर नकली हो सकता है।", "Call only the number shown in the official app or official website.", PsychologicalTactic.AUTHORITY_IMPERSONATION),
    # Requires genuine relationship language. Matching a bare "parcel ... customs"
    # misread ordinary courier scams as romance fraud.
    ScamSignalRule(r"\b(?:love you|my love|romance|dating|girlfriend|boyfriend|fiance[e]?|darling|sweetheart|soulmate)\b.{0,120}\b(?:customs|fee|money|gift|parcel|bitcoin|crypto|transfer)\b", ScamCategory.ROMANCE_SCAM, 34, "A new online relationship asking for money or fees is high risk.", "ऑनलाइन रिश्ते में पैसे या फीस मांगना जोखिम का संकेत है।", "Do not send money or identity documents to an online contact.", PsychologicalTactic.RECIPROCITY_TRAP),
    ScamSignalRule(r"\b(?:sextortion|nude|private video|viral video|send money or)\b", ScamCategory.ROMANCE_SCAM, 48, "Threats to publish private content are used to force payment.", "निजी सामग्री फैलाने की धमकी देकर पैसे मांगना ब्लैकमेल है।", "Do not pay or continue the chat; preserve evidence and report it.", PsychologicalTactic.FEAR_INDUCTION),
    ScamSignalRule(r"\b(?:click (?:here|this link)|open (?:this )?link|wa\.me/|bit\.ly/)\b", ScamCategory.PHISHING_LINK, 18, "Unexpected links can lead to fake login or payment pages.", "अनजान लिंक नकली login या payment page पर ले जा सकता है।", "Do not open the link; type the official website yourself.", PsychologicalTactic.FALSE_URGENCY),

    # --- PS01 rule packs -------------------------------------------------
    # Predatory instant-loan apps, Ponzi/MLM referral schemes, illegal betting
    # platforms, and utility-disconnection lures. Added for the Rajasthan Police
    # problem statement; each stays explainable and regex-observable.

    # Instant-loan app lures
    ScamSignalRule(r"\b(?:instant|quick|turant)\s+(?:personal\s+)?loan\b|\bloan\s+in\s+(?:\d+\s*)?(?:minutes?|mins?|hours?)\b", ScamCategory.LOAN_APP_FRAUD, 36, "Instant-loan offers with no checks are a common predatory-app lure.", "बिना जांच के तुरंत लोन का वादा अक्सर धोखाधड़ी वाले ऐप का संकेत है।", "Borrow only from an RBI-regulated lender; check the RBI list before installing any loan app.", PsychologicalTactic.TOO_GOOD_TO_BE_TRUE),
    ScamSignalRule(r"\b(?:no\s+(?:cibil|credit\s+check|documents?|paperwork)|only\s+aadhaar|aadhaar\s+(?:card\s+)?se\s+loan)\b", ScamCategory.LOAN_APP_FRAUD, 42, "No credit check and Aadhaar-only approval indicate an unregulated lender.", "बिना CIBIL या दस्तावेज़ के लोन देने वाले ऐप अक्सर गैर-कानूनी होते हैं।", "Do not share Aadhaar or grant contact and SMS permissions to an unverified loan app.", PsychologicalTactic.TOO_GOOD_TO_BE_TRUE),
    ScamSignalRule(r"\b(?:download|install)\s+(?:our\s+)?(?:loan\s+)?app\b.{0,40}\b(?:apk|link|now)\b|\.apk\b", ScamCategory.LOAN_APP_FRAUD, 44, "An APK offered outside the Play Store can carry a data-harvesting loan app.", "Play Store के बाहर से APK इंस्टॉल करना खतरनाक है; यह आपका डेटा चुरा सकता है।", "Do not install APK files sent by message. Use only the official app store.", PsychologicalTactic.AUTHORITY_IMPERSONATION),
    ScamSignalRule(r"\b(?:loan\s+recovery|recovery\s+agent|your\s+contacts?\s+will\s+be\s+(?:informed|called)|photo\s+will\s+be\s+(?:sent|shared))\b", ScamCategory.LOAN_APP_FRAUD, 52, "Threatening to contact your phonebook is an illegal loan-app harassment tactic.", "आपके contacts को फोन करने या फोटो भेजने की धमकी गैर-कानूनी वसूली है।", "Do not pay under threat. Preserve screenshots and report the harassment at cybercrime.gov.in or 1930.", PsychologicalTactic.FEAR_INDUCTION),

    # Ponzi / MLM referral schemes
    ScamSignalRule(r"\b(?:referral\s+(?:bonus|income|commission)|refer\s+and\s+earn|downline|upline|level\s+income|binary\s+(?:plan|income)|matrix\s+plan)\b", ScamCategory.PONZI_MLM, 46, "Income that depends on recruiting others is the defining feature of a Ponzi or MLM scheme.", "दूसरों को जोड़ने पर मिलने वाली कमाई Ponzi या MLM योजना की पहचान है।", "Do not join or deposit. Income that requires recruiting new members collapses by design.", PsychologicalTactic.SOCIAL_PROOF_FABRICATION),
    ScamSignalRule(r"\b(?:joining\s+(?:fee|package|amount)|registration\s+package|activate\s+your\s+id|id\s+activation)\b", ScamCategory.PONZI_MLM, 40, "An upfront joining package to start earning is a classic Ponzi entry fee.", "कमाई शुरू करने के लिए joining fee माँगना Ponzi योजना का सामान्य तरीका है।", "Do not pay a joining or activation fee to start earning.", PsychologicalTactic.PROCESSING_FEE_TRAP),
    ScamSignalRule(r"\b(?:guaranteed|assured|fixed)\s+(?:returns?|profit|income|roi)\b|\b(?:\d{1,3}\s*%\s*(?:daily|per\s+day|monthly|guaranteed))\b|\bdouble\s+your\s+(?:money|investment)\b", ScamCategory.PONZI_MLM, 50, "No legitimate investment can guarantee a fixed or daily return.", "कोई भी वैध निवेश रोज़ाना या निश्चित मुनाफ़े की गारंटी नहीं दे सकता।", "Treat guaranteed-return claims as fraud. Verify any scheme with SEBI or RBI before paying.", PsychologicalTactic.TOO_GOOD_TO_BE_TRUE),

    # Illegal betting and gambling
    ScamSignalRule(r"\b(?:betting\s+id|bet\s+id|fancy\s+rate|satta|teer\s+result|colou?r\s+prediction|aviator\s+game)\b", ScamCategory.BETTING_GAMBLING, 44, "Betting IDs and prediction games are used by illegal gambling operations.", "Betting ID और prediction game अवैध सट्टेबाज़ी का हिस्सा हैं।", "Do not deposit money. Online betting of this kind is illegal in most Indian states.", PsychologicalTactic.TOO_GOOD_TO_BE_TRUE),
    ScamSignalRule(r"\b(?:deposit\s+bonus|welcome\s+bonus|instant\s+withdrawal|100%\s*(?:winning|sure)\s*(?:tips?|prediction)|sure\s+shot\s+tips?)\b", ScamCategory.BETTING_GAMBLING, 38, "Guaranteed winnings and deposit bonuses are used to pull users into betting platforms.", "पक्की जीत और deposit bonus के वादे सट्टेबाज़ी में फँसाने के लिए होते हैं।", "Do not deposit. Guaranteed winning tips do not exist.", PsychologicalTactic.SOCIAL_PROOF_FABRICATION),

    # Electricity / utility disconnection lures
    ScamSignalRule(r"\b(?:electricity|power|bijli)\b.{0,60}\b(?:disconnect(?:ed|ion)?|cut\s+off|band\s+ho)\b|\bupdate\s+(?:your\s+)?meter\b", ScamCategory.UTILITY_BILL_SCAM, 40, "Threats to cut electricity tonight are a widespread Indian phishing lure.", "आज रात बिजली काटने की धमकी एक आम ठगी का तरीका है।", "Check your bill only in the official electricity board app or website; do not call the number in the message.", PsychologicalTactic.FEAR_INDUCTION),
)


DEFAULT_ACTIONS: dict[ScamCategory, list[str]] = {
    ScamCategory.OTP_THEFT: ["Do not share any OTP, PIN, CVV, password, or screen-sharing code.", "End the conversation and contact the company through its official app or website.", "If you shared details or lost money, call 1930 immediately."],
    ScamCategory.PHISHING_LINK: ["Do not open the link or install any app from it.", "Verify the request through the organisation's official app or website.", "Block and report the sender if the message is unsolicited."],
    ScamCategory.KYC_SCAM: ["Do not use the link or number in the message.", "Check your account only through the official bank or telecom app.", "If you entered banking details or lost money, call 1930 immediately."],
    ScamCategory.UPI_FRAUD: ["Do not approve collect requests or send money to verify an account.", "Open your payment app directly to check your account status.", "If money was lost, call 1930 immediately and notify your bank."],
}

GENERIC_ACTIONS = ["Do not act on the message until you verify it through an official channel.", "Do not share passwords, OTPs, PINs, CVVs, or banking details.", "Block and report the sender if the message was unsolicited or misleading."]

