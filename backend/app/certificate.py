"""Certificates bind an exact balancing result to the certified input.

The fingerprint is a canonical JSON hash of the *input* (ordered compounds,
role and composition), so the UI can tell whether a displayed certificate
still matches the editor contents.  Any edit changes the fingerprint and the
old certificate must be revoked immediately.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Sequence


def input_fingerprint(compounds: Sequence[dict]) -> str:
    canonical = json.dumps(
        compounds,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]


def issue_certificate(compounds: Sequence[dict], result: dict) -> dict:
    return {
        "certificateId": (
            "CERT-" + input_fingerprint(compounds).upper()
        ),
        "issuedAt": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "inputFingerprint": input_fingerprint(compounds),
        "status": result["status"],
        "reason": result["reason"],
    }
