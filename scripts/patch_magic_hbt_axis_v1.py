#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Isolated npn13g2 dimension-label correction; not device/PEX qualification.

Native Magic measures the long and short emitter axes as width and length.
The foundry npn13g2 model names those dimensions le and we, respectively.
Only these two exact technology parameter bindings are changed. Emitter
connectivity, Nx multiplicity, taps and RC remain separate unresolved contracts.
"""

import argparse
import hashlib
import json
from pathlib import Path

SOURCE_SHA256 = "dd7fda10b81f82416bdad9671286350ebf76fb42b67006bd5c90d77fc6bd6ebb"
OLD_LINES = (
    " device msubcircuit npn13g2 npn gec *ndiff space/w error w1=we l1=le",
    " device bjt npn13g2 npn gec *ndiff space/w error w1=we l1=le",
)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def patch(data):
    if digest(data) != SOURCE_SHA256:
        raise ValueError("Exact frozen original Magic extraction technology required")
    text = data.decode()
    for old in OLD_LINES:
        if text.splitlines().count(old) != 1:
            raise ValueError("Exact single npn13g2 style binding required")
        text = text.replace(old + "\n", old.replace("w1=we l1=le", "w1=le l1=we") + "\n")
    changed = text.encode()
    restore = text
    for old in OLD_LINES:
        restore = restore.replace(old.replace("w1=we l1=le", "w1=le l1=we") + "\n", old + "\n")
    if restore.encode() != data or changed == data:
        raise ValueError("Technology overlay changed unrelated bytes")
    return changed


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists() or args.source.resolve() == args.out.resolve():
        parser.error("Fresh separate output required; original PDK must remain unchanged")
    original = args.source.read_bytes()
    changed = patch(original)
    args.out.write_bytes(changed)
    if args.source.read_bytes() != original:
        raise ValueError("Original technology changed during overlay")
    print(json.dumps(dict(status="ISOLATED_AXIS_LABEL_OVERLAY_ONLY", original_sha256=digest(original),
                          changed_sha256=digest(changed), changed_style_bindings=2,
                          emitter_connectivity_qualified=False, multiplicity_qualified=False,
                          qualified_pex=False), indent=2))


if __name__ == "__main__":
    main()
