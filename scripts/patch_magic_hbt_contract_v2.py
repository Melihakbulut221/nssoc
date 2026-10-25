#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Isolated Magic HBT contact/search corrections; not multiplicity or PEX approval.

ExtBasic.c remains under its upstream UC Regents permissive notice. This patch
must be applied only to a private copy, recompiled and relinked. The technology
overlay represents the existing PCell emitter-window contact convention; it
does not add a fabricated CONT mask or alter the source GDS.
"""

import argparse
import hashlib
from pathlib import Path

PINS = {
    "ExtBasic.c": "af8677dd211d49841dab8423179c588adc582c53de9d8c00371bedd479e6b0db",
    "ihp-sg13g2.tech": "5ce21ab6a4c487d9115fe42d289af5fa0ba1612c4c2f5a3c9cc153fffbd1a967",
    "ihp-sg13g2-cifin.tech": "f536a548ec16644fcd474bc9f25af7e301c6488ba8cc1bc25a8a8147b48ff002",
}
EDITS = {
    "ExtBasic.c": [
        ("    Tile *t;\n    struct LT1 *t_next;", "    Tile *t;\n    TileType dinfo;\n    struct LT1 *t_next;"),
        ("    newdevtile->t = tile;", "    newdevtile->t = tile;\n    newdevtile->dinfo = dinfo;"),
        ("extTransFindSubs(lt->t, reg->treg_dinfo, tmask, def,", "extTransFindSubs(lt->t, lt->dinfo, tmask, def,"),
    ],
    "ihp-sg13g2.tech": [
        ("  active gemitterc,gemitc,gecontact,gec", "  active gemitter,gemit,ge\n  active gemitterc,gemitc,gecontact,gec"),
        ("  nec\t   nemitter   metal1", "  nec\t   nemitter   metal1\n  gec      gemitter   metal1"),
    ],
    "ihp-sg13g2-cifin.tech": [
        (" layer nemitter DIFFMASK\n and lvnpnarea", " layer gemitter DIFFMASK\n and lvnpnarea"),
    ],
}


def patch(name, data):
    if name not in PINS or hashlib.sha256(data).hexdigest() != PINS[name]:
        raise ValueError("Wrong immutable source for HBT v2 patch")
    text = data.decode()
    for old, new in EDITS[name]:
        if text.count(old) != 1:
            raise ValueError("Missing or ambiguous patch anchor")
        text = text.replace(old, new)
    inverse = text
    for old, new in reversed(EDITS[name]):
        inverse = inverse.replace(new, old)
    if inverse.encode() != data:
        raise ValueError("Patch touched bytes outside exact substitutions")
    return text.encode()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    value = patch(args.source.name, args.source.read_bytes())
    with args.output.open("xb") as stream:
        stream.write(value)


if __name__ == "__main__":
    main()
