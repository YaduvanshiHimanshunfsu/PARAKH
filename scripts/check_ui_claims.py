"""Fail if the frontend contains claims PARAKH cannot make, or third-party loads.

planversionalpha.md H.1: the Stitch designs contained phrases such as
"ISO 27001 Certified", "Section 91 CrPC", "Safe Certificate", hot-linked images
and CDN scripts. This gate keeps them from creeping back into the real app.

    python scripts/check_ui_claims.py            # scans frontend/src (+ dist if built)
    python scripts/check_ui_claims.py path ...   # scans the given paths

Exit code 1 lists every hit with file and line. design/stitch is reference
material and is never scanned.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PATHS = (ROOT / "frontend" / "src", ROOT / "frontend" / "dist", ROOT / "frontend" / "index.html")
TEXT_SUFFIXES = {".js", ".jsx", ".ts", ".tsx", ".json", ".css", ".html", ".md", ".svg"}

# (pattern, why it is banned)
BANNED: tuple[tuple[str, str], ...] = (
    (r"ISO\s*27001", "not certified"),
    (r"\bCrPC\b", "replaced by BNSS 2023 (§94 production, §106 seizure)"),
    (r"\b65\s*B\b", "replaced by BSA 2023 §63"),
    (r"\bIPC\b", "replaced by BNS 2023"),
    (r"live\s+integration", "no live CCTNS / I4C / 1930 integration exists"),
    (r"NPCI\s+(?:verified|registry|mule|lien|cross[- ]?check)", "no NPCI access"),
    (r"\bsmali\b|androguard|dynamic\s+emulation|docker\s+sandbox", "APK analysis is static only"),
    (r"deep\s*fake|acoustic\s+ai|spectral\s+probe", "no voice deepfake detection"),
    (r"safe\s+certificate|verification\s+certificate|verified\s+as\s+legitimate", "an automated tool cannot certify safety"),
    (r"verified\s+by\s+rajasthan\s+police|certified\s+by\s+i4c", "results are automated, not officer-verified"),
    (r"DLT\s+whitelist(?:ed)?\s+verified|DLT\s+entity\s+id", "no TRAI DLT access"),
    (r"lh3\.googleusercontent\.com", "hot-linked image (needs internet, misleading)"),
    (r"cdn\.tailwindcss\.com", "CDN script (offline demo, CSP)"),
    (r"fonts\.(?:googleapis|gstatic)\.com", "third-party font load (offline demo, CSP)"),
)
COMPILED = tuple((re.compile(pattern, re.IGNORECASE), reason) for pattern, reason in BANNED)


def iter_files(paths):
    for path in paths:
        if path.is_file():
            yield path
        elif path.is_dir():
            for file in path.rglob("*"):
                if file.is_file() and file.suffix in TEXT_SUFFIXES and "node_modules" not in file.parts:
                    yield file


def scan(paths) -> list[str]:
    hits: list[str] = []
    for file in iter_files(paths):
        if file.name == "check_ui_claims.py":
            continue
        try:
            text = file.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for number, line in enumerate(text.splitlines(), 1):
            for pattern, reason in COMPILED:
                match = pattern.search(line)
                if match:
                    hits.append(f"{file.relative_to(ROOT) if file.is_relative_to(ROOT) else file}:{number}: "
                                f"'{match.group(0)}' — {reason}")
    return hits


def main(argv: list[str]) -> int:
    paths = [Path(arg).resolve() for arg in argv] or [p for p in DEFAULT_PATHS if p.exists()]
    hits = scan(paths)
    for hit in hits:
        print(hit)
    print(f"{len(hits)} banned claim(s) found." if hits else "No banned claims found.")
    return 1 if hits else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
