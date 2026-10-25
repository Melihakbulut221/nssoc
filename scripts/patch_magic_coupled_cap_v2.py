#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Isolated v2: separate intrinsic ground C from retained explicit coupling.

The old intrinsic-retirement method is frozen. Derived Magic sources retain
LicenseRef-Magic-1985. Only unsimplified, non-lumped signal export is changed;
this is not a general network-reduction or qualified-PEX implementation.
"""

import argparse
import hashlib
import importlib.util
from pathlib import Path

OLD_PATH = Path(__file__).with_name("patch_magic_intrinsic_cap_retirement.py")
OLD_SHA = "724ef105e825797b0d2d6229e7891954ef09d6aca4c3fa6233bb16dd20b871f6"
SOURCES = {
    "resis.h": "c676aa5ff52aa53717e684c61f205ddd2acad3cd390f0be1b7a21787055a6797",
    "ResReadExt.c": "74abdd6322fb23af5bd4324a8212816946fbd6b1be06b300fb5c5e4ed9903a5b",
    "ResPrint.c": "16c67f5e32919d23399bb04d5ae1c85a85c5e536c1b596fbcd5dc6de77a7f26f",
    "ResRex.c": "d0bb591eddc40a3df7e4cb4f7990b0819f9f68d2388523d9fdca4f6e62f3832c",
    "ResSimple.c": "d2c33f04269609d5483add1c1c5714321bf09a55037a1c2e441954e9ae5e671f",
}


def old_method():
    if hashlib.sha256(OLD_PATH.read_bytes()).hexdigest() != OLD_SHA:
        raise ValueError("Frozen v1 method changed")
    spec = importlib.util.spec_from_file_location("frozen_intrinsic_retirement", OLD_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def patch(name, raw):
    if name not in SOURCES or hashlib.sha256(raw).hexdigest() != SOURCES[name]:
        raise ValueError("Unknown exact Magic source; no v2 patch applied")
    old = old_method()
    text = (old.patch(name, raw) if name in old.SOURCES else raw).decode()
    changes = {
        "resis.h": [(
            "    float\trg_nodecap;",
            "    float\trg_nodecap; /* Legacy total load, including coupling. */\n"
            "    float\trg_intrinsiccap; /* Ground component only for unreduced export. */",
        )],
        "ResRex.c": [(
            "    resisdata->rg_nodecap = 0.0;",
            "    resisdata->rg_nodecap = 0.0;\n    resisdata->rg_intrinsiccap = 0.0;",
        ), (
            "    resisdata->rg_nodecap = node->capacitance;",
            "    resisdata->rg_nodecap = node->capacitance;\n"
            "    resisdata->rg_intrinsiccap = node->intrinsic_capacitance;",
        )],
        "ResSimple.c": [(
            "    (void) ResDistributeCapacitance(ResNodeList, resisdata->rg_nodecap);",
            """    /* Explicit mutual capacitors remain in the original .ext.  Only
     * intrinsic ground C belongs in ground rnodes.  Limit this experimental
     * separation to the branch that returns before Tdi/reduction below;
     * preserve the legacy total load and all other operating modes.
     */
    if ((ResOptionsFlags & (ResOpt_DoExtFile | ResOpt_Signal))
            == (ResOpt_DoExtFile | ResOpt_Signal)
            && (ResOptionsFlags & (ResOpt_Simplify | ResOpt_DoLumpFile)) == 0)
    {
        TxPrintf("NSSOC_V2_INTRINSIC_DISTRIBUTION %s total=%g intrinsic=%g\\n",
                ResCurrentNode, resisdata->rg_nodecap, resisdata->rg_intrinsiccap);
        (void) ResDistributeCapacitance(ResNodeList, resisdata->rg_intrinsiccap);
    }
    else
        (void) ResDistributeCapacitance(ResNodeList, resisdata->rg_nodecap);""",
        )],
    }
    for before, after in changes.get(name, []):
        if text.count(before) != 1:
            raise ValueError("Native v2 source anchor is not unique")
        text = text.replace(before, after)
    return text.encode()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        parser.error("Fresh output directory required")
    result = {name: patch(name, (args.source_dir / name).read_bytes()) for name in SOURCES}
    args.out.mkdir(parents=True)
    for name, raw in result.items():
        (args.out / name).write_bytes(raw)
    print("EXPERIMENTAL_V2_SOURCE_REQUIRES_NATIVE_COUPLED_MATRIX_VALIDATION")


if __name__ == "__main__":
    main()
