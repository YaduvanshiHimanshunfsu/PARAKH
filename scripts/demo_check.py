"""Live demo smoke check (planversionalpha.md A.3).

Sends the exact demo inputs in eval/demo_cases.json to a running PARAKH server
over HTTP and checks each verdict. Run on every rehearsal and on demo morning;
any failure is a blocker.

    python -m uvicorn app.main:app --port 8000          # in another terminal
    python scripts/demo_check.py                        # all cases
    python scripts/demo_check.py --skip-phase-b         # only cases expected to pass today
    python scripts/demo_check.py --base-url http://127.0.0.1:8000

Before the demo, switch Wi-Fi off and clear GEMINI_API_KEY to prove the offline
rule path (DECISIONS.md B-1).
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
CASES = json.loads((ROOT / "eval" / "demo_cases.json").read_text(encoding="utf-8"))["cases"]


def post_json(base: str, path: str, payload: dict) -> dict:
    request = urllib.request.Request(
        f"{base}{path}",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))


def post_file(base: str, path: str, field: str, filename: str, data: bytes) -> dict:
    boundary = uuid.uuid4().hex
    body = (
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"{field}\"; filename=\"{filename}\"\r\n"
        f"Content-Type: application/vnd.android.package-archive\r\n\r\n"
    ).encode("utf-8") + data + f"\r\n--{boundary}--\r\n".encode("utf-8")
    request = urllib.request.Request(
        f"{base}{path}",
        data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def run_case(base: str, case: dict) -> tuple[bool, str]:
    kind, expect = case["kind"], case["expect"]
    if kind == "message":
        result = post_json(base, "/api/v1/parakh/analyze", {"message": case["input"], "language": "auto"})
        got = result["verdict"]
        return got in expect["verdict_in"], f"{got} ({result['scam_category']}, {result['analysis_source']})"
    if kind == "url":
        result = post_json(base, "/api/v1/parakh/url/analyze", {"url": case["input"]})
        got = result["risk_level"]
        return got in expect["risk_in"], f"{got} {[s['code'] for s in result['signals']]}"
    if kind == "qr":
        result = post_json(base, "/api/v1/parakh/qr/analyze", {"payload": case["input"]})
        got = result["decision"]
        return got in expect["decision_in"], f"{got} ({result['payload_kind']})"
    if kind == "email":
        result = post_json(base, "/api/v1/parakh/email/analyze", case["input"])
        got = result["verdict"]
        return got in expect["verdict_in"], f"{got} ({result['email_type']})"
    if kind == "apk":
        from tests.apk_fixtures import build_apk

        spec = case["input"]
        data = build_apk(
            package=spec["package"],
            label=spec["label"],
            permissions=tuple(f"android.permission.{p}" for p in spec["permissions"]),
            target_sdk=spec["target_sdk"],
            dex_strings=tuple(spec["dex_strings"]),
        )
        result = post_file(base, "/api/v1/parakh/apk/analyze", "apk", f"{case['id']}.apk", data)
        got = result["risk_level"]
        return got in expect["risk_in"], f"{got} ({result['risk_score']})"
    return False, f"unknown kind {kind}"


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--skip-phase-b", action="store_true", help="skip cases that need Phase B fixes")
    args = parser.parse_args(argv)
    base = args.base_url.rstrip("/")

    try:
        health = json.loads(urllib.request.urlopen(f"{base}/api/v1/health", timeout=5).read())
    except (urllib.error.URLError, OSError) as exc:
        print(f"Server not reachable at {base}: {exc}")
        return 2
    if health.get("provider_configured"):
        print("Note: an AI provider key is configured; the offline rule path is not what is being tested.")

    failures = 0
    skipped = 0
    for case in CASES:
        if args.skip_phase_b and case.get("phase_b"):
            skipped += 1
            continue
        started = time.perf_counter()
        try:
            ok, detail = run_case(base, case)
        except (urllib.error.URLError, OSError, KeyError, ValueError) as exc:
            ok, detail = False, f"error: {exc}"
        ms = round((time.perf_counter() - started) * 1000)
        tag = "PASS" if ok else ("FAIL*" if case.get("phase_b") else "FAIL")
        failures += not ok
        print(f"{tag:6} {case['id']:22} {ms:5} ms  {detail}")
    total = len(CASES) - skipped
    print(f"\n{total - failures}/{total} passed" + (f", {skipped} Phase B case(s) skipped" if skipped else "")
          + ("" if not failures else "  (* = known Phase B gap)"))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
