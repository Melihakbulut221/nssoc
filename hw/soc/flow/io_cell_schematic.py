#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Select I/O CDL cells without losing explicitly declared substrate globals.

CDL ``*.GLOBAL`` metadata and SPICE ``.GLOBAL`` declarations have the same
explicit intent here. No global is inferred from an exclamation mark in a
node name. Device bodies are preserved verbatim; this is not an LVS verdict.
"""
import argparse
import json
from pathlib import Path

from transistor_schematic import digest, global_line, parse_cdl_text, read_cdl_text, reachable_cdl


def read_io_cdl_text(path):
    """Reject newline conversion before a claim of verbatim body retention."""
    return read_cdl_text(path)


def parse_io_cdl(text):
    """Keep the public I/O API while sharing the full-chip retaining reader."""
    definitions, _, globals_ = parse_cdl_text(text)
    return definitions, globals_


def select_io_cdl(text, top):
    definitions, globals_ = parse_io_cdl(text)
    selected = reachable_cdl(definitions, [top])
    prefix = ".GLOBAL " + " ".join(globals_) + "\n" if globals_ else ""
    output = prefix + "\n\n".join(selected.values()) + "\n"
    actual, actual_globals = parse_io_cdl(output)
    if actual != selected or actual_globals != globals_:
        raise ValueError("Selected CDL changed a device body or explicit global")
    return output, selected, globals_


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--top", required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args()
    if args.output.resolve() == args.receipt.resolve():
        parser.error("Output and receipt must use distinct paths")
    if args.output.exists() or args.receipt.exists():
        parser.error("Choose fresh output and receipt paths")
    source_hash = digest(args.source)
    output, selected, globals_ = select_io_cdl(read_io_cdl_text(args.source), args.top)
    if digest(args.source) != source_hash:
        raise ValueError("CDL source changed")
    with args.output.open("x") as stream:
        stream.write(output)
    receipt = dict(status="EXPLICIT_GLOBALS_AND_SELECTED_DEVICE_BODIES_PRESERVED",
                   top=args.top, source_sha256=source_hash,
                   output_sha256=digest(args.output), globals=globals_,
                   selected_subcircuits=list(selected),
                   scope="Explicit vendor globals only; no device, node or parameter body changed. "
                         "No physical substrate/supply connection or LVS pass is established.",
                   lvs_accepted=False, manufacturing_approval=False)
    with args.receipt.open("x") as stream:
        json.dump(receipt, stream, indent=2)
        stream.write("\n")
    print(receipt["status"])


if __name__ == "__main__":
    main()
