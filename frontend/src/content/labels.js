// Human labels for backend enums (app/schemas.py). Keys must match exactly;
// src/content/labels.test.js keeps them in step with the API contract.

export const SCAM_CATEGORY = {
  UPI_FRAUD: ['UPI payment fraud', 'यूपीआई भुगतान ठगी'],
  KYC_SCAM: ['Bank KYC scam', 'बैंक केवाईसी ठगी'],
  GOVERNMENT_IMPERSONATION: ['Pretending to be government or police', 'सरकार या पुलिस बनकर ठगी'],
  LOTTERY_PRIZE: ['Fake lottery or prize', 'नकली लॉटरी या इनाम'],
  FAKE_JOB: ['Fake job or task scam', 'नकली नौकरी या टास्क ठगी'],
  INVESTMENT_FRAUD: ['Investment fraud', 'निवेश ठगी'],
  OTP_THEFT: ['OTP theft', 'ओटीपी चोरी'],
  PHISHING_LINK: ['Phishing link', 'फ़िशिंग लिंक'],
  COURIER_SCAM: ['Courier or parcel scam', 'कूरियर / पार्सल ठगी'],
  TECH_SUPPORT: ['Fake tech support', 'नकली टेक सपोर्ट'],
  ROMANCE_SCAM: ['Romance or friendship scam', 'दोस्ती / रोमांस ठगी'],
  LOAN_APP_FRAUD: ['Predatory loan app', 'फर्जी लोन ऐप'],
  PONZI_MLM: ['Ponzi or chain scheme', 'पोंज़ी / चेन योजना'],
  BETTING_GAMBLING: ['Illegal betting or gambling', 'अवैध सट्टा / जुआ'],
  UTILITY_BILL_SCAM: ['Electricity or utility bill scam', 'बिजली / बिल ठगी'],
  UNKNOWN: ['Not a known scam type', 'ज्ञात प्रकार नहीं'],
}

export const TACTIC = {
  FALSE_URGENCY: ['False urgency', 'झूठी जल्दबाज़ी'],
  AUTHORITY_IMPERSONATION: ['Pretends to be an authority', 'अधिकारी होने का दिखावा'],
  FEAR_INDUCTION: ['Creates fear', 'डर पैदा करना'],
  TOO_GOOD_TO_BE_TRUE: ['Too good to be true', 'सच होने के लिए बहुत अच्छा'],
  OTP_SOCIAL_ENGINEERING: ['Asks for OTP or PIN', 'ओटीपी या पिन माँगना'],
  PROCESSING_FEE_TRAP: ['Asks for a fee first', 'पहले शुल्क माँगना'],
  SOCIAL_PROOF_FABRICATION: ['Fake proof from “others”', 'दूसरों का नकली सबूत'],
  RECIPROCITY_TRAP: ['Small favour, big ask', 'छोटा एहसान, बड़ी माँग'],
}

export const EXPOSURE = {
  RECEIVED_ONLY: ['I only received it', 'केवल संदेश मिला'],
  CLICKED_LINK: ['I opened the link', 'मैंने लिंक खोला'],
  SHARED_PERSONAL_INFO: ['I shared personal details', 'मैंने निजी जानकारी दी'],
  SHARED_SECRET: ['I shared an OTP, PIN or password', 'मैंने ओटीपी / पिन / पासवर्ड बताया'],
  INSTALLED_APP_OR_SCREEN_SHARE: ['I installed an app or shared my screen', 'मैंने ऐप इंस्टॉल किया / स्क्रीन साझा की'],
  SENT_MONEY: ['I sent money', 'मैंने पैसे भेजे'],
}

export const SAFE_ACTION = {
  CLICK_LINK: ['Open the link', 'लिंक खोलना', 'link'],
  CALL_NUMBER: ['Call the number', 'नंबर पर कॉल', 'call'],
  PAY_MONEY: ['Pay money', 'पैसे भेजना', 'payments'],
  INSTALL_APP: ['Install the app', 'ऐप इंस्टॉल करना', 'mobile_arrow_down'],
  SHARE_OTP: ['Share an OTP', 'ओटीपी बताना', 'password'],
  SCAN_OR_PAY_QR: ['Scan or pay a QR', 'क्यूआर स्कैन / भुगतान', 'qr_code_scanner'],
  OPEN_ATTACHMENT: ['Open an attachment', 'अटैचमेंट खोलना', 'attach_file'],
}

export const SAFETY_DECISION = {
  STOP_NOW: { level: 'HIGH', label: 'Stop now', hindi: 'अभी रुकें' },
  VERIFY_FIRST: { level: 'MEDIUM', label: 'Verify first', hindi: 'पहले जाँचें' },
  LOWER_RISK_STILL_VERIFY: { level: 'LOW', label: 'Lower risk — still verify', hindi: 'कम जोखिम — फिर भी जाँचें' },
}

export const AUTH_STATUS = {
  PASS: ['Pass', 'LOW'],
  FAIL: ['Fail', 'HIGH'],
  SOFTFAIL: ['Soft fail', 'MEDIUM'],
  NEUTRAL: ['Neutral', 'UNKNOWN'],
  NONE: ['None', 'UNKNOWN'],
  NOT_PRESENT: ['Not present', 'UNKNOWN'],
  NOT_VERIFIABLE: ['Not verifiable', 'UNKNOWN'],
  ERROR: ['Error', 'UNKNOWN'],
}

export const EMAIL_TYPE = {
  PHISHING: 'Phishing',
  IMPERSONATION: 'Impersonation',
  BUSINESS_EMAIL_COMPROMISE: 'Business email compromise',
  MALWARE_DELIVERY: 'Malware delivery',
  MARKETING_OR_NEWSLETTER: 'Marketing or newsletter',
  TRANSACTIONAL: 'Transactional',
  PERSONAL_OR_UNKNOWN: 'Personal or unknown',
}

export const IDENTIFIER_NAME = {
  UPI: 'UPI ID',
  PHONE: 'phone number',
  BANK_ACCOUNT: 'bank account',
  IFSC: 'IFSC code',
  DOMAIN: 'website',
  URL: 'link',
  EMAIL: 'email address',
  TELEGRAM: 'Telegram handle',
  IP: 'IP address',
  CRYPTO_BTC: 'Bitcoin wallet',
  CRYPTO_ETH: 'Ethereum wallet',
  PACKAGE: 'app package',
  CERT_SHA256: 'signing certificate',
  ICON_PHASH: 'app icon',
}

export function label(table, key, fallback = key) {
  const value = table[key]
  if (!value) return fallback
  return Array.isArray(value) ? value[0] : value.label ?? value
}

export function hindiLabel(table, key) {
  const value = table[key]
  if (!value) return ''
  return Array.isArray(value) ? value[1] : value.hindi ?? ''
}
