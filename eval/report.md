# PARAKH evaluation report

Generated 2026-11-24 06:24 UTC by `scripts/evaluate.py`. Offline: rule engine only, no AI key, no network.

> The golden set is team-written synthetic data modelled on public police and CERT-In advisory patterns. Add real R4C / cyber-cell samples before quoting these numbers externally.

## Headline (test split)

| Metric | Value | Phase B target |
|---|---|---|
| `messages.macro_f1` | 0.37 | 0.85 |
| `messages.scam_precision` | 0.75 | 0.92 |
| `messages.risky_recall` | 0.625 |  |
| `messages.safe_specificity` | 0.918 |  |
| `messages.risky_recall_hi_hinglish` | 0.368 | 0.85 |
| `urls.phishing_recall` | 0.5 |  |
| `urls.official_false_positives` | 9 | 0 |
| `identifiers.micro_f1` | 0.884 | 0.9 |
| `websites.accuracy` | 0.75 |  |
| `apks.accuracy` | 1.0 |  |

Split sizes (test): messages 97, URLs 36, identifiers 22, websites 8, APKs 5.

## Messages (all items)

Confusion matrix (rows = truth, columns = predicted):

| truth \ predicted | SCAM | SUSPICIOUS | SAFE |
|---|---|---|---|
| SCAM | 32 | 45 | 56 |
| SUSPICIOUS | 0 | 0 | 12 |
| SAFE | 5 | 4 | 146 |

| Language | n | risky recall | false-alarm rate |
|---|---|---|---|
| en | 153 | 0.722 | 0.099 |
| hi | 72 | 0.171 | 0.0 |
| hinglish | 75 | 0.5 | 0.027 |

| Category | n | accuracy (risky vs safe) |
|---|---|---|
| ADVISORY | 23 | 0.739 |
| APPOINTMENT | 5 | 1.0 |
| BANK_ALERT | 20 | 0.95 |
| BETTING_GAMBLING | 6 | 0.833 |
| COURIER_SCAM | 4 | 0.5 |
| DELIVERY | 8 | 1.0 |
| DIGITAL_ARREST | 15 | 0.0 |
| EDUCATION | 5 | 1.0 |
| FAKE_JOB | 14 | 0.429 |
| GOVERNMENT_IMPERSONATION | 7 | 0.714 |
| GOVT | 16 | 1.0 |
| HEALTH | 5 | 1.0 |
| INVESTMENT_FRAUD | 7 | 0.286 |
| KYC_SCAM | 20 | 0.6 |
| LOAN_APP_FRAUD | 13 | 0.615 |
| LOTTERY_PRIZE | 4 | 0.75 |
| MALICIOUS_APP | 12 | 1.0 |
| MARKETPLACE_FRAUD | 3 | 0.333 |
| OTP | 8 | 0.75 |
| OTP_THEFT | 4 | 0.5 |
| PERSONAL | 24 | 1.0 |
| PHISHING_LINK | 4 | 0.0 |
| PONZI_MLM | 7 | 0.714 |
| PROMO | 10 | 1.0 |
| ROMANCE_SCAM | 2 | 1.0 |
| SEXTORTION | 3 | 0.333 |
| TECH_SUPPORT | 3 | 1.0 |
| TRAVEL | 8 | 1.0 |
| UNKNOWN | 2 | 0.0 |
| UPI_FRAUD | 4 | 0.75 |
| UTILITY | 16 | 1.0 |
| UTILITY_BILL_SCAM | 11 | 0.455 |
| WORK | 7 | 1.0 |

Category label match on SCAM items: 0.398

### Missed scams (68)

- `m009` [en, KYC_SCAM] Dear SBI user, 7,450 reward points expire today. Redeem now at sbi-rewards-point.xyz by entering your card details.
- `m010` [en, KYC_SCAM] PNB: Your credit card limit is being reduced. To stop it, verify card number, expiry and CVV at pnb-card-limit.click
- `m011` [hi, KYC_SCAM] प्रिय ग्राहक, आपका SBI खाता 24 घंटे में बंद कर दिया जाएगा। तुरंत KYC अपडेट करें sbi-kyc-help.cyou
- `m013` [hi, KYC_SCAM] आपका पैन कार्ड लिंक नहीं है, खाता ब्लॉक किया जा रहा है। ओटीपी बताकर अभी सत्यापन करें: 9876543210
- `m015` [hi, KYC_SCAM] आपका डेबिट कार्ड बंद होने वाला है। कार्ड नंबर और सीवीवी भेजें ताकि कार्ड चालू रहे।
- `m017` [hinglish, KYC_SCAM] Sir aapka account band ho jayega, OTP bata dijiye abhi verify kar dete hain. Bank se bol raha hoon.
- `m018` [hinglish, KYC_SCAM] Aapke paytm wallet ki KYC pending hai, 2 ghante me wallet band. Call karein 9123456780 par turant.
- `m019` [hinglish, KYC_SCAM] Aapka credit card limit kam ho raha hai, rokne ke liye card number aur CVV is link par bharein pnb-limit-help.in
- `m021` [en, DIGITAL_ARREST] This is Inspector from CBI Mumbai. Your Aadhaar is linked to a money laundering case. You are under digital arrest, do n
- `m022` [en, DIGITAL_ARREST] FedEx: A parcel in your name containing drugs and fake passports was seized by customs. Press 9 to speak to Mumbai Crime
- `m023` [en, DIGITAL_ARREST] TRAI notice: Your mobile number is involved in illegal activity and will be disconnected in 2 hours. A case is registere
- `m024` [en, DIGITAL_ARREST] Enforcement Directorate: An arrest warrant is issued against you in a money laundering case. Stay on Skype video call an
- `m025` [en, DIGITAL_ARREST] NCB officer speaking. Your courier to Taiwan had 200 grams of MDMA. You are under digital arrest until verification. Sen
- `m026` [en, DIGITAL_ARREST] Supreme Court order: Your bank accounts are under investigation. Transfer your balance to the court safe account for aud
- `m027` [en, DIGITAL_ARREST] Delhi Police cyber cell: your SIM was used for harassment complaints. Join the video statement now or a warrant will be 
- `m028` [hi, DIGITAL_ARREST] मैं सीबीआई से बोल रहा हूँ। आपके आधार से मनी लॉन्ड्रिंग का केस जुड़ा है। आप डिजिटल अरेस्ट में हैं, वीडियो कॉल बंद न करें 
- `m029` [hi, DIGITAL_ARREST] आपके नाम से भेजे गए पार्सल में ड्रग्स मिले हैं। कस्टम विभाग ने केस दर्ज किया है। गिरफ्तारी से बचने के लिए तुरंत सुरक्षा 
- `m030` [hi, DIGITAL_ARREST] ट्राई: आपका नंबर अवैध गतिविधियों में शामिल है, 2 घंटे में बंद होगा। पुलिस अधिकारी से बात करने के लिए 1 दबाएँ।
- `m031` [hi, DIGITAL_ARREST] प्रवर्तन निदेशालय: आपके विरुद्ध गिरफ्तारी वारंट जारी हुआ है। किसी को न बताएँ, वीडियो कॉल पर बने रहें और जमानत राशि ट्रां
- `m032` [hinglish, DIGITAL_ARREST] Main CBI officer bol raha hoon, aapke Aadhaar se money laundering case juda hai. Aap digital arrest me ho, video call ba
- `m033` [hinglish, DIGITAL_ARREST] Aapke naam ka parcel customs ne pakda hai usme drugs mile hain. Arrest se bachna hai to abhi security deposit bhejo.
- `m034` [hinglish, DIGITAL_ARREST] TRAI se call hai, aapka number 2 ghante me band hoga kyunki illegal activity me use hua hai. Police se baat karne ke liy
- `m035` [hinglish, DIGITAL_ARREST] ED ka warrant nikla hai aapke naam par. Kisi ko mat batana, Skype par bane raho aur bail amount transfer karo.
- `m036` [en, FAKE_JOB] Hi, I am Priya from HR. Part time job, rate hotels on Google Maps and earn Rs 3000 per day. Reply YES on WhatsApp.
- `m039` [en, FAKE_JOB] Your first 3 tasks are complete and Rs 450 credited. For the next merchant task deposit Rs 5000, you will get Rs 7500 ba
- `m042` [hi, FAKE_JOB] घर बैठे कमाएँ ₹3000 रोज़! सिर्फ़ होटल को रेटिंग दें और स्क्रीनशॉट भेजें। पार्ट टाइम जॉब के लिए टेलीग्राम पर जुड़ें।
- `m043` [hi, FAKE_JOB] आपका चयन वर्क फ्रॉम होम नौकरी के लिए हुआ है। आईडी सक्रिय करने के लिए ₹1500 पंजीकरण शुल्क जमा करें।
- `m044` [hi, FAKE_JOB] अगला टास्क पूरा करने के लिए ₹5000 जमा करें, एक घंटे में ₹8000 वापस मिलेंगे।
- `m047` [hinglish, FAKE_JOB] Aapke 3 task complete ho gaye, ab next task ke liye 10000 deposit karo, 15000 wapas milega aaj hi.
- `m054` [hi, LOAN_APP_FRAUD] लोन नहीं चुकाया तो आपकी फोटो आपके सभी संपर्कों को भेज दी जाएगी। दो घंटे में भुगतान करें।
- `m055` [hi, LOAN_APP_FRAUD] बिना दस्तावेज़ ₹50000 का तुरंत लोन। प्रोसेसिंग शुल्क ₹999 जमा करें और राशि खाते में पाएं।
- `m057` [hinglish, LOAN_APP_FRAUD] Loan time par nahi chukaya, ab tumhare saare contacts ko photo bhej denge. 2 ghante me payment karo.
- `m063` [en, INVESTMENT_FRAUD] IPO allotment guaranteed through our institutional account. Deposit funds in our trading app and get 300% returns.
- `m065` [hi, PONZI_MLM] गारंटीड रिटर्न! रोज़ाना 10% मुनाफ़ा। हर नए सदस्य पर रेफरल बोनस। जॉइनिंग पैकेज ₹5000 जमा करें richplan@ybl
- `m066` [hi, INVESTMENT_FRAUD] हमारे वीआईपी ट्रेडिंग ग्रुप से जुड़ें, हर हफ्ते पक्का मुनाफ़ा। संस्थागत खाते से आईपीओ आवंटन की गारंटी।
- `m067` [hi, PONZI_MLM] 30 दिन में पैसा डबल! लेवल इनकम और डाउनलाइन कमीशन। आज ही अपनी आईडी एक्टिवेट करें।
- `m069` [hinglish, INVESTMENT_FRAUD] VIP stock tips group join karo, pakka profit har hafte. Institutional account se IPO allotment guaranteed.
- `m074` [hi, BETTING_GAMBLING] आईपीएल सट्टा आईडी 2 मिनट में! 100% पक्की जीत, तुरंत निकासी और पहले डिपॉज़िट पर बोनस।
- `m080` [en, UTILITY_BILL_SCAM] AVVNL alert: smart meter update pending. Install the Bijli Update app from this link or supply will stop tonight.
- `m082` [hi, UTILITY_BILL_SCAM] प्रिय उपभोक्ता, पिछला बिल अपडेट न होने से आज रात 9:30 बजे आपकी बिजली काट दी जाएगी। तुरंत बिजली अधिकारी से संपर्क करें 99

### False alarms on safe messages (9)

- `s003` [en] → SCAM: 123456 is your OTP for login to SBI YONO. Valid for 3 minutes. Do not share this OTP with anyone. -SBI
- `s005` [en] → SCAM: Use 739204 as one time password for your Axis Bank transaction of Rs 1,200 at SWIGGY. Never share your OTP with anyone.
- `s020` [en] → SCAM: Rajasthan Police: Never share OTP, PIN or CVV with anyone. Police never conducts a digital arrest over video call. Repor
- `s021` [en] → SUSPICIOUS: RBI says: banks never ask for your KYC details or OTP over phone, SMS or email. Do not click on unknown links.
- `s023` [en] → SUSPICIOUS: Alert: fraudsters are sending fake electricity disconnection messages. Discoms never ask you to call a personal mobile n
- `s053` [en] → SUSPICIOUS: Card blocked as requested by you on 22-Nov. A replacement card will be dispatched to your registered address. -HDFC Bank
- `s146` [en] → SUSPICIOUS: Rajasthan Police advisory: sextortion callers record video calls to blackmail. Do not pay; report at 1930 and preserve s
- `s147` [en] → SCAM: Guaranteed returns are a red flag. Check if an investment advisor is registered with SEBI before investing.
- `s154` [hinglish] → SCAM: Guaranteed return ka vaada fraud ka sign hai, invest karne se pehle SEBI registration check karo.

## URLs (all items)

Phishing recall 0.633, precision 0.521, official false positives 35 / 60.

Official or legitimate sites flagged:

- `https://police.rajasthan.gov.in` → MEDIUM ['BRAND_LIKE_DOMAIN']
- `https://rajasthan.gov.in` → MEDIUM ['BRAND_LIKE_DOMAIN']
- `https://sso.rajasthan.gov.in/signin` → MEDIUM ['CREDENTIAL_OR_KYC_LURE', 'BRAND_LIKE_DOMAIN']
- `https://cybercrime.gov.in` → MEDIUM ['BRAND_LIKE_DOMAIN']
- `https://uidai.gov.in` → MEDIUM ['BRAND_LIKE_DOMAIN']
- `https://myaadhaar.uidai.gov.in` → MEDIUM ['BRAND_LIKE_DOMAIN']
- `https://www.incometax.gov.in/iec/foportal/` → MEDIUM ['BRAND_LIKE_DOMAIN']
- `https://www.epfindia.gov.in` → MEDIUM ['BRAND_LIKE_DOMAIN']
- `https://parivahan.gov.in` → MEDIUM ['BRAND_LIKE_DOMAIN']
- `https://echallan.parivahan.gov.in` → MEDIUM ['BRAND_LIKE_DOMAIN']
- `https://sancharsaathi.gov.in` → MEDIUM ['BRAND_LIKE_DOMAIN']
- `https://www.sebi.gov.in` → MEDIUM ['BRAND_LIKE_DOMAIN']
- `https://www.india.gov.in` → MEDIUM ['BRAND_LIKE_DOMAIN']
- `https://www.mygov.in` → MEDIUM ['BRAND_LIKE_DOMAIN']
- `https://www.digilocker.gov.in` → MEDIUM ['BRAND_LIKE_DOMAIN']
- `https://pmkisan.gov.in` → MEDIUM ['BRAND_LIKE_DOMAIN']
- `https://www.indiapost.gov.in` → MEDIUM ['BRAND_LIKE_DOMAIN']
- `https://energy.rajasthan.gov.in` → MEDIUM ['BRAND_LIKE_DOMAIN']
- `https://jaipur.rajasthan.gov.in` → MEDIUM ['BRAND_LIKE_DOMAIN']
- `https://www.passportindia.gov.in` → MEDIUM ['BRAND_LIKE_DOMAIN']
- `https://www.onlinesbi.sbi` → MEDIUM ['BRAND_LIKE_DOMAIN']
- `https://www.sbicard.com` → MEDIUM ['BRAND_LIKE_DOMAIN']
- `https://www.hdfcbank.com` → MEDIUM ['CREDENTIAL_OR_KYC_DOMAIN']
- `https://www.icicibank.com` → MEDIUM ['CREDENTIAL_OR_KYC_DOMAIN']
- `https://www.axisbank.com` → MEDIUM ['CREDENTIAL_OR_KYC_DOMAIN']
- `https://www.bankofbaroda.in` → MEDIUM ['CREDENTIAL_OR_KYC_DOMAIN']
- `https://www.firstpost.com` → MEDIUM ['BRAND_LIKE_DOMAIN']
- `https://www.irs-tax-help.example` → MEDIUM ['BRAND_LIKE_DOMAIN']
- `https://www.pineapple-recipes.com` → MEDIUM ['BRAND_LIKE_DOMAIN']
- `https://www.governmentjobs-guide.org` → MEDIUM ['BRAND_LIKE_DOMAIN']
- `https://www.jiosaavn.com` → MEDIUM ['BRAND_LIKE_DOMAIN']
- `https://www.taxishop.in` → MEDIUM ['BRAND_LIKE_DOMAIN']
- `https://www.rajeduboard.rajasthan.gov.in` → MEDIUM ['DEEP_SUBDOMAIN_CHAIN', 'BRAND_LIKE_DOMAIN']
- `https://emitra.rajasthan.gov.in` → MEDIUM ['BRAND_LIKE_DOMAIN']
- `https://janaadhaar.rajasthan.gov.in` → MEDIUM ['BRAND_LIKE_DOMAIN']

Phishing URLs missed:

- `https://pnb-card-limit.click` (lookalike) → LOW ['HIGH_RISK_TLD']
- `https://jvvnl-bill-pay.in` (lookalike) → LOW []
- `https://echallan-parivahan-pay.in/challan` (lookalike) → LOW []
- `https://mparivahan-challan.top/download` (lookalike) → LOW ['HIGH_RISK_TLD']
- `https://indiapost-redeliver.top` (lookalike) → LOW ['HIGH_RISK_TLD']
- `https://onlinesbl.in` (typosquat) → LOW []
- `https://paytrn.com/kyc` (typosquat) → LOW ['CREDENTIAL_OR_KYC_LURE']
- `https://phonepay.co.in` (typosquat) → LOW []
- `https://jvvn1.in` (typosquat) → LOW []
- `https://rnicrosoft-support.com` (typosquat) → LOW []
- `https://arnazon-offers.in` (typosquat) → LOW []
- `https://richplan-invest.xyz/join` (scheme) → LOW ['HIGH_RISK_TLD']
- `https://bet777.vip/register` (scheme) → LOW []
- `https://quickcash-loan.top/app.apk` (scheme) → LOW ['HIGH_RISK_TLD']
- `https://colour-prediction-win.online` (scheme) → LOW []
- `https://double-money-plan.site` (scheme) → LOW []
- `https://task-earn-daily.live/join` (scheme) → LOW []
- `https://aviator-hack-predictor.top` (scheme) → LOW ['HIGH_RISK_TLD']
- `https://instant-loan-noncibil.shop/apply` (scheme) → LOW []
- `https://google-pay-cashback.store` (lookalike) → LOW []
- `https://rajasthan-police-challan.xyz` (lookalike) → LOW ['HIGH_RISK_TLD']
- `https://sebi-registered-advisor.club` (lookalike) → LOW []

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
