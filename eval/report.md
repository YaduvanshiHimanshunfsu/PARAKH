# PARAKH evaluation report

Generated 2026-11-24 11:15 UTC by `scripts/evaluate.py`. Offline: rule engine only, no AI key, no network.

> The golden set is team-written synthetic data modelled on public police and CERT-In advisory patterns. Add real R4C / cyber-cell samples before quoting these numbers externally.

## Headline (test split)

| Metric | Value | Phase B target |
|---|---|---|
| `messages.macro_f1` | 0.649 | 0.85 |
| `messages.scam_precision` | 1.0 | 0.92 |
| `messages.risky_recall` | 0.979 |  |
| `messages.safe_specificity` | 0.959 |  |
| `messages.risky_recall_hi_hinglish` | 1.0 | 0.85 |
| `urls.phishing_recall` | 0.833 |  |
| `urls.official_false_positives` | 0 | 0 |
| `identifiers.micro_f1` | 0.884 | 0.9 |
| `websites.accuracy` | 0.75 |  |
| `apks.accuracy` | 1.0 |  |

Split sizes (test): messages 97, URLs 36, identifiers 22, websites 8, APKs 5.

## Messages (all items)

Confusion matrix (rows = truth, columns = predicted):

| truth \ predicted | SCAM | SUSPICIOUS | SAFE |
|---|---|---|---|
| SCAM | 127 | 4 | 2 |
| SUSPICIOUS | 2 | 5 | 5 |
| SAFE | 3 | 5 | 147 |

| Language | n | risky recall | false-alarm rate |
|---|---|---|---|
| en | 153 | 0.944 | 0.012 |
| hi | 72 | 0.943 | 0.081 |
| hinglish | 75 | 0.974 | 0.108 |

| Category | n | accuracy (risky vs safe) |
|---|---|---|
| ADVISORY | 23 | 0.826 |
| APPOINTMENT | 5 | 1.0 |
| BANK_ALERT | 20 | 0.85 |
| BETTING_GAMBLING | 6 | 1.0 |
| COURIER_SCAM | 4 | 1.0 |
| DELIVERY | 8 | 1.0 |
| DIGITAL_ARREST | 15 | 0.933 |
| EDUCATION | 5 | 1.0 |
| FAKE_JOB | 14 | 0.929 |
| GOVERNMENT_IMPERSONATION | 7 | 1.0 |
| GOVT | 16 | 1.0 |
| HEALTH | 5 | 1.0 |
| INVESTMENT_FRAUD | 7 | 1.0 |
| KYC_SCAM | 20 | 1.0 |
| LOAN_APP_FRAUD | 13 | 0.769 |
| LOTTERY_PRIZE | 4 | 1.0 |
| MALICIOUS_APP | 12 | 1.0 |
| MARKETPLACE_FRAUD | 3 | 1.0 |
| OTP | 8 | 1.0 |
| OTP_THEFT | 4 | 1.0 |
| PERSONAL | 24 | 1.0 |
| PHISHING_LINK | 4 | 1.0 |
| PONZI_MLM | 7 | 1.0 |
| PROMO | 10 | 1.0 |
| ROMANCE_SCAM | 2 | 1.0 |
| SEXTORTION | 3 | 1.0 |
| TECH_SUPPORT | 3 | 1.0 |
| TRAVEL | 8 | 1.0 |
| UNKNOWN | 2 | 0.0 |
| UPI_FRAUD | 4 | 1.0 |
| UTILITY | 16 | 0.938 |
| UTILITY_BILL_SCAM | 11 | 1.0 |
| WORK | 7 | 1.0 |

Category label match on SCAM items: 0.91

### Missed scams (7)

- `m028` [hi, DIGITAL_ARREST] मैं सीबीआई से बोल रहा हूँ। आपके आधार से मनी लॉन्ड्रिंग का केस जुड़ा है। आप डिजिटल अरेस्ट में हैं, वीडियो कॉल बंद न करें 
- `m054` [hi, LOAN_APP_FRAUD] लोन नहीं चुकाया तो आपकी फोटो आपके सभी संपर्कों को भेज दी जाएगी। दो घंटे में भुगतान करें।
- `m136` [en, LOAN_APP_FRAUD] Need a personal loan? Quick approval, low interest. Reply LOAN to get a call back.
- `m137` [en, FAKE_JOB] Hiring now! Online work, flexible hours, good pay. Send your name and city to get details.
- `m139` [en, UNKNOWN] Hello dear, I got your number from a friend. Can we talk on WhatsApp? I have a business proposal.
- `m142` [hinglish, LOAN_APP_FRAUD] Personal loan chahiye? Jaldi approval, kam byaj. LOAN likh ke reply karo.
- `m144` [en, UNKNOWN] Your account shows unusual activity. If this was not you, contact support.

### False alarms on safe messages (8)

- `s006` [en] → SUSPICIOUS: Your ICICI Bank Credit Card XX2210 has been used for Rs 3,499 at FLIPKART on 12-Nov. If not done by you, block the card 
- `s068` [hi] → SCAM: राजस्थान पुलिस: कोई भी पुलिस अधिकारी वीडियो कॉल पर डिजिटल अरेस्ट नहीं करता। ठगी होने पर तुरंत 1930 पर कॉल करें।
- `s088` [hi] → SUSPICIOUS: आपके अनुरोध पर कार्ड ब्लॉक कर दिया गया है। नया कार्ड आपके पंजीकृत पते पर भेजा जाएगा।
- `s093` [hi] → SUSPICIOUS: ऑनलाइन नौकरी के नाम पर पैसे मांगने वालों से सावधान रहें। असली कंपनियाँ नौकरी के लिए शुल्क नहीं लेतीं।
- `s103` [hinglish] → SUSPICIOUS: Rajasthan Police: koi bhi police video call par digital arrest nahi karti. Thagi hone par turant 1930 par call karein.
- `s104` [hinglish] → SCAM: Bijli katne ke fake message se savdhan rahein. Discom kabhi personal mobile number par call karne ko nahi kehta.
- `s108` [hinglish] → SCAM: Vaishali Nagar me 27 Nov ko 10 se 2 baje tak maintenance ke liye bijli band rahegi.
- `s129` [hinglish] → SUSPICIOUS: Aapke request par card block kar diya gaya hai, naya card registered address par aayega.

## URLs (all items)

Phishing recall 0.85, precision 1.0, official false positives 0 / 60.

Official or legitimate sites flagged:


Phishing URLs missed:

- `https://richplan-invest.xyz/join` (scheme) → LOW ['HIGH_RISK_TLD']
- `https://bet777.vip/register` (scheme) → LOW ['HIGH_RISK_TLD']
- `https://quickcash-loan.top/app.apk` (scheme) → LOW ['HIGH_RISK_TLD']
- `https://colour-prediction-win.online` (scheme) → LOW ['HIGH_RISK_TLD']
- `https://double-money-plan.site` (scheme) → LOW ['HIGH_RISK_TLD']
- `https://task-earn-daily.live/join` (scheme) → LOW ['HIGH_RISK_TLD']
- `https://aviator-hack-predictor.top` (scheme) → LOW ['HIGH_RISK_TLD']
- `https://instant-loan-noncibil.shop/apply` (scheme) → LOW ['HIGH_RISK_TLD']
- `https://google-pay-cashback.store` (lookalike) → LOW ['HIGH_RISK_TLD']

## Identifiers (all items)

| Type | precision | recall | F1 | support |
|---|---|---|---|---|
| BANK_ACCOUNT | 1.0 | 1.0 | 1.0 | 3 |
| CRYPTO_BTC | 1.0 | 1.0 | 1.0 | 2 |
| CRYPTO_ETH | 1.0 | 1.0 | 1.0 | 3 |
| CRYPTO_TRON | 0.0 | 0.0 | 0.0 | 3 |
| DOMAIN | 0.846 | 0.786 | 0.815 | 14 |
| EMAIL | 1.0 | 1.0 | 1.0 | 2 |
| FIREBASE_DB | 0.0 | 0.0 | 0.0 | 1 |
| IFSC | 1.0 | 1.0 | 1.0 | 4 |
| IMEI | 0.0 | 0.0 | 0.0 | 2 |
| IP | 0.75 | 1.0 | 0.857 | 3 |
| PACKAGE | 1.0 | 1.0 | 1.0 | 2 |
| PHONE | 0.909 | 0.714 | 0.8 | 14 |
| TELEGRAM | 1.0 | 0.429 | 0.6 | 7 |
| TELEGRAM_BOT | 0.0 | 0.0 | 0.0 | 2 |
| UPI | 1.0 | 1.0 | 1.0 | 11 |
| URL | 0.875 | 1.0 | 0.933 | 7 |

Mismatches:

- `i005` missing ['PHONE:+923001234567'] extra []
- `i006` missing ['PHONE:+14155550132'] extra []
- `i007` missing ['PHONE:+971501234567'] extra []
- `i008` missing ['PHONE:+911412741234'] extra []
- `i010` missing ['DOMAIN:sbi-kyc-help.cyou'] extra []
- `i013` missing ['DOMAIN:task-earn.sbs'] extra []
- `i023` missing ['TELEGRAM:t.me/richplansupport'] extra []
- `i024` missing ['TELEGRAM:t.me/task_earn_admin'] extra []
- `i025` missing ['TELEGRAM:t.me/sureshottips2026'] extra []
- `i029` missing ['CRYPTO_TRON:TKArzRcd5hxJZZ6QtCppxs3D3M7UqPTq65'] extra []
- `i030` missing ['CRYPTO_TRON:TAzXbaDyfDaC66AsmF3QYs11NpRyot9uR9'] extra []
- `i031` missing ['TELEGRAM_BOT:7012345678'] extra ['PHONE:+917012345678']
- `i032` missing ['TELEGRAM_BOT:6543210987'] extra ['DOMAIN:api.telegram.org', 'URL:https://api.telegram.org/bot6543210987:aafklmnopqrstuvwxyzabcdefghijklmnop/sendmessage']
- `i033` missing ['IMEI:490154203237518'] extra []
- `i034` missing ['IMEI:356938035643809'] extra []
- `i035` missing ['FIREBASE_DB:quickcash-abc.firebaseio.com'] extra []
- `i044` missing ['DOMAIN:bit.ly'] extra []
- `i050` missing [] extra ['DOMAIN:wa.me']
- `n016` missing [] extra ['IP:1.2.3.4']
- `i058` missing ['TELEGRAM:t.me/cashloanagent'] extra []
- `i059` missing ['CRYPTO_TRON:TKArzRcd5hxJZZ6QtCppxs3D3M7UqPTq65'] extra []

## Websites (all items)

Accuracy 0.833.

- `w006` SCAM → LOW (28) ['INSTANT_LOAN_NO_CHECKS']
- `w009` SCAM → LOW (0) []
- `w015` SCAM → LOW (16) ['MISSING_LEGITIMACY_MARKERS']
- `w022` SAFE → HIGH (72) ['REFERRAL_CHAIN_INCOME', 'JOINING_PACKAGE_FEE', 'MISSING_LEGITIMACY_MARKERS']
- `w025` SAFE → MEDIUM (41) ['PAGE_COLLECTS_PAYMENT_IDENTIFIER', 'MISSING_LEGITIMACY_MARKERS']

## APKs (all items, synthetic)

Accuracy 0.9; benign apps flagged HIGH: 2.

- `a015` SAFE → HIGH (100) ['PERM_READ_SMS', 'PERM_RECEIVE_SMS', 'PERM_READ_CONTACTS', 'PERM_SEND_SMS', 'COMBO_LOAN_APP_HARVESTING', 'COMBO_OTP_EXFILTRATION', 'UNSIGNED_OR_UNREADABLE_SIGNATURE']
- `a018` SAFE → HIGH (71) ['PERM_READ_CONTACTS', 'PERM_READ_CALL_LOG', 'UNSIGNED_OR_UNREADABLE_SIGNATURE']
