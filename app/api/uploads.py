from __future__ import annotations

"""Bounded reading of uploaded APKs, shared by the officer and citizen routes.

APK routes are exempt from the global request-size middleware, so this is the
only ceiling they have (DECISIONS.md ADR-004).
"""

from fastapi import HTTPException, UploadFile, status

_CHUNK_BYTES = 1_048_576


async def read_apk_upload(upload: UploadFile, limit: int) -> bytes:
    chunks: list[bytes] = []
    total = 0
    try:
        while chunk := await upload.read(_CHUNK_BYTES):
            total += len(chunk)
            if total > limit:
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail=f"The APK exceeds the {limit // 1_000_000} MB upload limit.",
                )
            chunks.append(chunk)
    finally:
        await upload.close()

    if total == 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="The uploaded file is empty."
        )
    return b"".join(chunks)
