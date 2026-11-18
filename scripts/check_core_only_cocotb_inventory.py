#!/usr/bin/env python3
"""Fail-closed cocotb release inventory; does not certify design acceptance."""
import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "hw/soc/core-only-cocotb-inventory.json"

def network(path):
    name = path.rsplit("/", 1)[1]
    name = name.removeprefix("Makefile.").removeprefix("test_").removesuffix(".py")
    return name.startswith(("soc_pcie_", "pcie_")) or name in ("soc_eth", "gen12_record_cdc")

def validate(root, manifest):
    if manifest.get("schema") != 1 or manifest.get("profile") != "core-only":
        raise ValueError("Invalid release inventory schema/profile")
    retained, excluded = manifest["retained"], manifest["excluded"]
    for entries in (retained, excluded):
        if not isinstance(entries, list) or any(not isinstance(p, str) or "|" in p or "\n" in p for p in entries):
            raise ValueError("Invalid inventory paths")
        if entries != sorted(set(entries)):
            raise ValueError("Duplicate or unordered inventory")
    if set(retained) & set(excluded):
        raise ValueError("Ambiguous release inventory")
    if any(not network(p) for p in excluded) or any(network(p) for p in retained):
        raise ValueError("Unexpected PCIe/Ethernet scope classification")
    actual = set()
    for directory in ("hw/tb", "hw/soc/tb/cocotb"):
        for p in (root / directory).iterdir():
            n = p.name
            if p.is_file() and (n == "Makefile" or n.startswith("Makefile.") or n.startswith("test_") and n.endswith(".py")):
                actual.add(p.relative_to(root).as_posix())
    if actual != set(retained + excluded):
        raise ValueError("Unreviewed inventory delta: " + repr(sorted(actual ^ set(retained + excluded))))
    if not retained:
        raise ValueError("Empty retained scope")
    return excluded

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--excluded", action="store_true")
    args = parser.parse_args()
    manifest = json.loads(MANIFEST.read_text())
    excluded = validate(ROOT, manifest)
    if args.excluded:
        print("|".join(excluded))
    else:
        print(json.dumps({"profile": "core-only", "retained_files": len(manifest["retained"]),
                          "excluded_files": len(excluded), "accepted": False}))

if __name__ == "__main__":
    main()
