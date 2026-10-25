# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Restore exact frozen failure evidence from permanent cloud release assets.

No Actions artifact or run API is needed: those records can expire. Both release
objects are byte-pinned, and the original ZIP result must equal its frozen proof.
Run only on the hosted worker; this writes the two original preservation files.
"""
import hashlib
import io
import json
from pathlib import Path
import subprocess
import zipfile


def asset(identifier, size, digest):
    data = subprocess.check_output([
        "gh", "api", f"repos/Melihakbulut221/nssoc/releases/assets/{identifier}",
        "-H", "Accept: application/octet-stream",
    ])
    assert len(data) == size, "Permanent failure evidence size differs"
    assert hashlib.sha256(data).hexdigest() == digest, "Permanent failure evidence digest differs"
    return data


def main():
    digest = "929624b1906214472f59794d7ce78e6f27798881d1dbfe3e1f06337104ce089a"
    raw = asset(642644297, 24396, digest)
    proof = asset(642644376, 19876,
        "64ccdca37fa8bee5c772195661530eee19d83c126d04858a089fb1468e3f7304")
    receipt = json.loads(proof)
    assert receipt["status"] == "PRESERVED_ORIGINAL_FAILED_CAPTURE_NOT_ACCEPTED"
    assert receipt["source_run"] == 38680055040
    assert receipt["source_head"] == "af836358f7a85bd0c8231f1d0aa719ed150b8f1d"
    assert receipt["artifact"]["id"] == 11947829260
    assert receipt["artifact"]["digest"] == "sha256:" + digest
    assert receipt["artifact"]["workflow_run"]["id"] == receipt["source_run"]
    with zipfile.ZipFile(io.BytesIO(raw)) as packed:
        result = json.loads(packed.read("result.json"))
        assert result == receipt["result"]
        assert result["status"] == "FAIL_OR_ERROR" and result["boundary_pins"] is True
    Path("failed-boundary-38680055040.zip").write_bytes(raw)
    Path("failed-boundary-38680055040.json").write_bytes(proof)
    print("PASS_PERMANENT_ORIGINAL_FAILED_CAPTURE_BYTE_EXACT_NOT_PHYSICAL_ACCEPTANCE")


if __name__ == "__main__":
    main()
