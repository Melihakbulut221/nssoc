#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Isolated producer repair for already-distributed intrinsic ground capacitance.

Original runtime and PDK files are never modified. Derived Magic C sources retain
LicenseRef-Magic-1985. This does not qualify coupling, RC corners or full-chip PEX.
"""

import argparse
import hashlib
from pathlib import Path

SOURCES = {
    "resis.h": "c676aa5ff52aa53717e684c61f205ddd2acad3cd390f0be1b7a21787055a6797",
    "ResReadExt.c": "74abdd6322fb23af5bd4324a8212816946fbd6b1be06b300fb5c5e4ed9903a5b",
    "ResPrint.c": "16c67f5e32919d23399bb04d5ae1c85a85c5e536c1b596fbcd5dc6de77a7f26f",
}


def patch(name, raw):
    if name not in SOURCES or hashlib.sha256(raw).hexdigest() != SOURCES[name]:
        raise ValueError("Unknown exact Magic source; no patch applied")
    text = raw.decode()
    changes = {
        "resis.h": [
            (
                "    float\t\tcapacitance;",
                "    double\t\tintrinsic_capacitance; /* Original NODE C, excluding coupling. */\n    float\t\tcapacitance;",
            )
        ],
        "ResReadExt.c": [
            (
                "    node->capacitance += MagAtof(argv[NODES_NODECAP]);",
                "    node->capacitance += MagAtof(argv[NODES_NODECAP]);\n    node->intrinsic_capacitance += MagAtof(argv[NODES_NODECAP]);",
            ),
            (
                "\tnode->capacitance = 0;",
                "\tnode->capacitance = 0;\n\tnode->intrinsic_capacitance = 0;",
            ),
        ],
        "ResPrint.c": [
            (
                '    /* Create "rnode" entries for each subnode */',
                """    /* A retained original name keeps its NODE ground C in ext2spice.
     * This successful replacement network already distributes that intrinsic
     * C through its rnodes. Retire only the original intrinsic contribution
     * with the native subcap adjustment; do not subtract coupling C, kill a
     * retained port, or change repeated-rnode additive semantics.
     */
    if ((ResOptionsFlags & ResOpt_DoExtFile) && !DoKillNode && !NeedFix
            && nodelist != NULL && node->intrinsic_capacitance != 0.0)
        fprintf(outextfile, "subcap \\"%s\\" %.17g\\n", nodename,
                -node->intrinsic_capacitance);

    /* Create "rnode" entries for each subnode */""",
            )
        ],
    }
    for old, new in changes[name]:
        if text.count(old) != 1:
            raise ValueError("Native source anchor not unique")
        text = text.replace(old, new)
    return text.encode()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--source-dir", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    if a.out.exists():
        ap.error("Fresh output directory required")
    result = {n: patch(n, (a.source_dir / n).read_bytes()) for n in SOURCES}
    a.out.mkdir(parents=True)
    for n, data in result.items():
        (a.out / n).write_bytes(data)
    print("ISOLATED_MAGIC_INTRINSIC_CAP_RETIREMENT_SOURCE_REQUIRES_NATIVE_CONTROLS")


if __name__ == "__main__":
    main()
