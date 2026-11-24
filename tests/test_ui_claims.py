"""The H.1 honesty gate must pass on the real frontend and catch the Stitch claims."""

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("check_ui_claims", ROOT / "scripts" / "check_ui_claims.py")
check = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(check)


def test_frontend_source_has_no_banned_claims() -> None:
    paths = [p for p in (ROOT / "frontend" / "src", ROOT / "frontend" / "index.html") if p.exists()]
    assert check.scan(paths) == []


def test_gate_catches_what_the_stitch_designs_contained() -> None:
    stitch = ROOT / "design" / "stitch"
    if not stitch.exists():
        return
    hits = check.scan([stitch])
    joined = "\n".join(hits)
    for phrase in ("ISO 27001", "CrPC", "cdn.tailwindcss.com", "fonts.googleapis.com"):
        assert phrase.lower() in joined.lower(), phrase
