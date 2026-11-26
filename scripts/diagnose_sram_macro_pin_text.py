"""Duplicate exactly four native SRAM TEXT elements onto Metal1 text in a new GDS."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import struct

def records(data):
    pos = 0
    while pos < len(data):
        size, kind = struct.unpack_from(">HH", data, pos)
        if size < 4 or size % 2 or pos + size > len(data):
            raise ValueError("Invalid GDS record length")
        yield kind, data[pos:pos+size]
        pos += size
        if kind == 0x0400:
            if any(data[pos:]):
                raise ValueError("Unexpected bytes after ENDLIB")
            yield None, data[pos:]
            return

def project(data, leaf, crossed):
    output = bytearray()
    inventory, elements = [], Counter()
    cell = None
    element = None
    for kind, raw in records(data):
        output.extend(raw)
        if kind == 0x0606:
            cell = raw[4:].rstrip(b"\0").decode()
        if kind == 0x0c00:
            element = []
        if element is not None:
            element.append((kind, raw))
        if kind == 0x1100:
            elements[cell] += 1
            if cell == leaf and element:
                fields = dict(element)
                layer = int.from_bytes(fields[0x0d02][4:], "big")
                purpose = int.from_bytes(fields[0x1602][4:], "big")
                if (layer, purpose) == (8, 2):
                    name = fields[0x1906][4:].rstrip(b"\0").decode()
                    xy = struct.unpack(">ii", fields[0x1003][4:])
                    inventory.append((name, xy))
                    new = {"A":"Z","Z":"A"}.get(name, name) if crossed else name
                    extra = bytearray()
                    for key, record in element:
                        if key == 0x1602:
                            record = record[:4] + struct.pack(">H", 25)
                        if key == 0x1906 and new != name:
                            record = record[:4] + new.encode() + b"\0"
                        extra.extend(record)
                    output.extend(extra)
            element = None
    if sorted(x[0] for x in inventory) != ["A","VDD!","VSS!","Z"]:
        raise ValueError(f"Unexpected original pin inventory: {inventory}")
    return bytes(output), inventory, elements

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("leaf", choices=["RSC_IHPSG13_CINVX2","RSC_IHPSG13_WLDRVX8"])
    parser.add_argument("output", type=Path)
    parser.add_argument("--crossed", action="store_true")
    args = parser.parse_args()
    data = args.source.read_bytes()
    out, pins, counts = project(data, args.leaf, args.crossed)
    # Verify the written stream independently by removing the four added elements.
    rebuilt = bytearray()
    block = None
    current = None
    removed = 0
    for kind, raw in records(out):
        if kind == 0x0606:
            current = raw[4:].rstrip(b"\0").decode()
        if kind == 0x0c00 and current == args.leaf:
            block = []
        if block is None:
            rebuilt.extend(raw)
        else:
            block.append((kind,raw))
            if kind == 0x1100:
                fields = dict(block)
                if fields[0x0d02][4:] == b"\0\x08" and fields[0x1602][4:] == b"\0\x19":
                    removed += 1
                else:
                    rebuilt.extend(b"".join(record for _,record in block))
                block = None
    if removed != 4 or rebuilt != data:
        raise ValueError("Original hierarchy, elements or labels changed")
    with args.output.open("xb") as stream:
        stream.write(out)
    print(json.dumps(dict(original_sha256=hashlib.sha256(data).hexdigest(), copy_sha256=hashlib.sha256(out).hexdigest(), pins=pins, populated_cells=len(counts), original_elements=sum(counts.values()), removed_for_byte_exact_check=removed)))
