"""The server extractor must match the shared identifier vectors.

The same file pins the frontend preview (frontend/src/lib/identifiers.test.js),
so a change on either side that is not mirrored on the other fails a test.
After an intentional extractor change run `python scripts/gen_identifier_vectors.py`
and review the diff.
"""

import json
from pathlib import Path

import pytest

from app.services.identifier_extractor import extract_identifiers

VECTORS = json.loads(
    (Path(__file__).parent / "fixtures" / "identifier_vectors.json").read_text(encoding="utf-8")
)
CLIENT_TYPES = set(VECTORS["client_types"])


@pytest.mark.parametrize("vector", VECTORS["vectors"], ids=lambda v: v["name"])
def test_server_extractor_matches_shared_vectors(vector: dict) -> None:
    found = [
        {"type": item.type.value, "value": item.value}
        for item in extract_identifiers(vector["text"], include_context=False)
        if item.type.value in CLIENT_TYPES
    ]
    assert found == vector["expected"]
