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
import re
from pathlib import Path
import tempfile

from transistor_schematic import digest, read_cdl, reachable_cdl

GLOBAL = re.compile(r"^\s*(\*)?\.GLOBAL(?:\s+(.*?))?\s*$", re.I)
NODE = re.compile(r"[A-Za-z0-9_!./<>\[\]:+-]+")
BLOCK = re.compile(r"^\.SUBCKT\b.*?^\.ENDS[^\n]*", re.M | re.S | re.I)


def read_io_cdl_text(path):
    """Reject newline conversion before a claim of verbatim body retention."""
    text = Path(path).read_bytes().decode("utf-8")
    if "\r" in text:
        raise ValueError("CDL input must use LF newlines; CRLF conversion is not implicit")
    return text


def global_line(line):
    """Return explicitly declared names, or None for an unrelated line."""
    match = GLOBAL.fullmatch(line.rstrip("\r\n"))
    if match is None:
        return None
    names = (match[2] or "").split()
    if not names or any(not NODE.fullmatch(name) for name in names):
        raise ValueError("Unsupported CDL global declaration: " + line.rstrip())
    if len({name.casefold() for name in names}) != len(names):
        raise ValueError("Duplicate CDL global name: " + line.rstrip())
    return names


def parse_io_cdl(text):
    """Retain explicit globals and reuse the existing strict CDL body reader."""
    if "\r" in text:
        raise ValueError("CDL input must use LF newlines; CRLF conversion is not implicit")
    for chunk in BLOCK.findall(text):
        if any(global_line(line) is not None for line in chunk.splitlines()[1:]):
            raise ValueError("CDL globals must be declared outside subcircuits")
    globals_ = []
    for line in BLOCK.sub("", text).splitlines():
        names = global_line(line)
        if names is not None:
            for name in names:
                previous = next((old for old in globals_ if old.casefold() == name.casefold()), None)
                if previous is not None and previous != name:
                    raise ValueError("Ambiguous global-name case: " + name)
                if previous is None:
                    globals_.append(name)
        elif line.strip() and not line.lstrip().startswith("*"):
            raise ValueError("Unsupported CDL outside subcircuits: " + line)
    # The general reader deliberately rejects globals to prevent their silent
    # loss. Read only a temporary, comment-marked view after retaining them
    # above; the selected output renders these declarations explicitly again.
    body_view = "".join("* " + line if global_line(line) is not None else line
                        for line in text.splitlines(keepends=True))
    with tempfile.TemporaryDirectory(prefix=".nssoc-io-cdl-", dir=Path.cwd()) as directory:
        source = Path(directory) / "body.cdl"
        source.write_text(body_view)
        definitions, _ = read_cdl([source])
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
