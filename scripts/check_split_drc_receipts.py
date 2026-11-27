# SPDX-License-Identifier: Apache-2.0
"""Check split KLayout reports against an independently prepared coverage manifest.

The manifest identifies top, GDS/deck SHA-256 and switches, maps table names to
required report categories, and gives the GDS and deck paths. Worker receipts
bind a table, exit status, run identity and report digest. A valid collection
with any markers exits nonzero. The manifest must enumerate the intended deck.
"""
import argparse
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def check(manifest, rows, directory, report_directory):
    identity = manifest["identity"]
    if not identity.get("top") or not identity.get("switches"):
        raise ValueError("missing top or switches")
    for key in ("gds", "deck"):
        if digest(directory / manifest[key]) != identity[key + "_sha256"]:
            raise ValueError(f"{key} digest mismatch")

    tables = manifest["tables"]
    if not {"offgrid", "angle"} <= tables.keys():
        raise ValueError("missing geometry tables in manifest")
    counts = {}
    reports = set()
    for row in rows:
        table = row["table"]
        report = (report_directory / row["report"]).resolve(strict=True)
        if table not in tables or table in counts or report in reports:
            raise ValueError(f"unexpected or repeated worker/report: {table}")
        if row["exit"] != 0 or row["identity"] != identity or digest(report) != row["sha256"]:
            raise ValueError(f"failed worker or provenance mismatch: {table}")
        reports.add(report)
        root = ET.parse(report).getroot()
        if (root.tag != "report-database" or root.findtext("top-cell") != identity["top"]
                or root.find("items") is None):
            raise ValueError(f"incomplete report: {table}")
        categories = {node.text for node in root.findall(".//categories/category/name")}
        required = tables[table]
        if not isinstance(required, list) or not required or not set(required) <= categories:
            raise ValueError(f"missing planned categories: {table}")
        counts[table] = len(root.findall("items/item"))
    if counts.keys() != tables.keys():
        raise ValueError(f"missing tables: {sorted(tables.keys() - counts.keys())}")
    return counts


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("receipts", type=Path)
    args = parser.parse_args()
    counts = check(json.loads(args.manifest.read_text()), json.loads(args.receipts.read_text()),
                   args.manifest.parent, args.receipts.parent)
    print(json.dumps(counts, sort_keys=True))
    raise SystemExit(int(any(counts.values())))
