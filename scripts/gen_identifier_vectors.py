"""Regenerate tests/fixtures/identifier_vectors.json from the server extractor.

The frontend previews identifiers with a JavaScript port of the server
extractor (frontend/src/lib/identifiers.js). Both implementations are pinned to
this one vectors file:

* tests/test_identifier_vectors.py   — server output must equal the file
* frontend/src/lib/identifiers.test.js — client output must equal the file

Run after an intentional extractor change, review the diff, then commit:

    python scripts/gen_identifier_vectors.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.services.identifier_extractor import extract_identifiers  # noqa: E402

# Only the types the client previews; see CLIENT_TYPES in identifiers.js.
CLIENT_TYPES = ("URL", "EMAIL", "TELEGRAM", "CRYPTO_ETH", "IFSC", "UPI", "PHONE", "IP", "DOMAIN")

TEXTS: tuple[tuple[str, str], ...] = (
    ("ponzi_sms", "RichPlan Investment: Guaranteed 10% daily returns! Pay richplan@ybl or call 9812345670. Join https://t.me/RichPlanOfficial"),
    ("kyc_sms", "Dear customer your SBI KYC will be blocked in 24 hours. Verify at https://sbi-verify-kyc.in/urgent or call +91 98765 43210."),
    ("discom_sms", "Dear consumer, electricity power will be disconnected tonight at 9:30 PM. Pay Rs 10 on http://sbi-verify-kyc.in or UPI discom.bill98@ybl"),
    ("email_vs_upi", "Write to support@richplan-invest.xyz or pay winner@paytm today."),
    ("ip_url", "Download http://45.133.1.9/quickcash.apk now, support 9123456780"),
    ("private_ip", "Router at 192.168.1.1 and server 10.0.0.5 are internal; real host 185.220.101.44"),
    ("version_string", "App version 2.4.1.0 build ok, contact 9988776655."),
    ("ifsc_bank", "Transfer to A/c 918273645501 IFSC SBIN0001428 beneficiary RichPlan"),
    ("eth_wallet", "Deposit USDT ERC20 to 0x52908400098527886E0F7030069857D2E4169EE7 for 2x returns"),
    ("telegram_only", "Join our VIP group t.me/joinchat/AbCdEf123 for sure-shot tips"),
    ("bare_domain", "Visit richplan-invest.xyz/join or bet777.vip for bonus"),
    ("phone_formats", "Call 98123-45670 or +919812345670 or 091 98123 45670."),
    ("sentence_end_phone", "For help call 9876543210."),
    ("hindi_mixed", "आपका खाता बंद हो जाएगा। तुरंत KYC करें: https://sbi-kyc-help.in/verify या कॉल करें 9876501234"),
    ("no_identifiers", "Hello, the meeting is at 5 pm tomorrow. See you there."),
)


def build() -> list[dict]:
    vectors = []
    for name, text in TEXTS:
        found = [
            {"type": item.type.value, "value": item.value}
            for item in extract_identifiers(text, include_context=False)
            if item.type.value in CLIENT_TYPES
        ]
        vectors.append({"name": name, "text": text, "expected": found})
    return vectors


def main() -> None:
    target = ROOT / "tests" / "fixtures" / "identifier_vectors.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = {"client_types": list(CLIENT_TYPES), "vectors": build()}
    target.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"wrote {len(payload['vectors'])} vectors to {target.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
