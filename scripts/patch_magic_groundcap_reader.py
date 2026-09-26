#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Write the isolated Magic 8.3.623 reader experiment to a new source file.

This two-line change includes intrinsic node C in the extresist distribution.
It does not fix coupling retention, spatial accuracy, scale handling or PDK
qualification. Never modifies the installed tool, source file or PDK.
"""

import argparse
import hashlib
from pathlib import Path

SOURCE_SHA256 = {
    "30d2e85324d33b7f20074697518e37eeaf1398f921ad5854ea683323bc5497ae",
    # Same upstream reader with the independently audited port-alias repair.
    "0a5405a8d8bef2402cd7933f2720197a67c2bf6aece5db8aa323d3811f3a3060",
}


def patch(source):
    if hashlib.sha256(source).hexdigest() not in SOURCE_SHA256:
        raise ValueError("Unknown source version; refusing unverified reader patch")
    text = source.decode()
    define = "#define\t\tNODES_NODEX\t\t4"
    node = "node = ResExtInitNode(entry);\n\n    node->location.p_x = atoi(argv[NODES_NODEX]);"
    if text.count(define) != 1 or text.count(node) != 1:
        raise ValueError("Unexpected native source structure")
    return (
        text.replace(define, "#define\t\tNODES_NODECAP\t\t3\n" + define)
        .replace(
            node,
            "node = ResExtInitNode(entry);\n"
            "    node->capacitance += MagAtof(argv[NODES_NODECAP]);\n\n"
            "    node->location.p_x = atoi(argv[NODES_NODEX]);",
        )
        .encode()
    )


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--source", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    result = patch(args.source.read_bytes())
    with args.output.open("xb") as f:
        f.write(result)
    print("EXPERIMENTAL_READER_SOURCE_ONLY", hashlib.sha256(result).hexdigest())


if __name__ == "__main__":
    main()
