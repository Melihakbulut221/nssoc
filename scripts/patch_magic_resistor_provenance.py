#!/usr/bin/env python3
"""Exact source-only Magic 8.3.623 diagnostic derivation; never builds or runs Magic.

On a hosted runner:
  python scripts/patch_magic_resistor_provenance.py --magic-source DIR --output NEW_DIR

DIR must be the qualified, already patched Magic source. NEW_DIR must not exist.
Only five derived source files and a receipt are written. The input tree is not
changed. A separately reviewed build/extraction controller must copy the derived
files, rebuild the complete binary, and qualify native-output equivalence.
No network, acquisition, compiler, simulation, or authorization API is provided.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
PINS = "scripts/cdr-resistor-physical-provenance-pins.json"
SPEC = "scripts/magic-resistor-physical-provenance-patch.json"


def require(value, message):
    if not value:
        raise AssertionError(message)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def secure(root, relative):
    p = PurePosixPath(relative)
    require(isinstance(relative, str) and p.as_posix() == relative
            and not p.is_absolute() and all(x not in ("", ".", "..") for x in p.parts),
            "unsafe source path")
    target = root
    for item in p.parts:
        target = target / item
        require(not target.is_symlink(), "source symlink: " + relative)
    require(target.is_file(), "missing regular source: " + relative)
    return target


def exact(raw, record, label):
    require(type(record["bytes"]) is int and len(raw) == record["bytes"]
            and digest(raw) == record["sha256"], "source bytes: " + label)


def source_guard(root=ROOT):
    pins = json.loads(secure(root, PINS).read_bytes())
    require(pins["schema"] == 1 and pins["scope"] == "source-only-resistor-diagnostic",
            "source manifest identity")
    for key in ("native_build_qualified", "native_output_equivalence_qualified",
                "extraction_qualified", "physical_ownership_proved",
                "electrical_acceptance", "physical_acceptance", "full_phy_accepted"):
        require(pins[key] is False, "unqualified diagnostic scope: " + key)
    for path, record in pins["files"].items():
        exact(secure(root, path).read_bytes(), record, path)
    spec = json.loads(secure(root, SPEC).read_bytes())
    require(spec["schema"] == 1
            and spec["upstream"]["commit"] == "fd12c39c37f26a0fe6e04698b1011e31b8bd3229"
            and len(spec["files"]) == 5 and len(spec["rules"]) == 11,
            "exact diagnostic derivation")
    return pins, spec


def insertion(root, rule):
    require(set(rule) in ({"path", "anchor", "position", "insertion"},
                          {"path", "anchor", "position", "payload"}),
            "exact insertion rule shape")
    require(rule["position"] in ("before", "after"), "insertion position")
    raw = (secure(root, rule["payload"]).read_bytes() if "payload" in rule
           else rule["insertion"].encode("utf-8"))
    require(bool(raw) and bool(rule["anchor"]), "empty insertion")
    return raw


def transform(sources, root=ROOT, reverse=False):
    """Byte-level derivation with exact five-file pre/post identities."""
    _, spec = source_guard(root)
    require(set(sources) == set(spec["files"]), "complete five-source map")
    current = dict(sources)
    for path, record in spec["files"].items():
        exact(current[path], record["after" if reverse else "before"], path)
    rules = list(reversed(spec["rules"])) if reverse else spec["rules"]
    for rule in rules:
        path = rule["path"]
        anchor = rule["anchor"].encode("utf-8")
        added = insertion(root, rule)
        joined = added + anchor if rule["position"] == "before" else anchor + added
        old, new = (joined, anchor) if reverse else (anchor, joined)
        require(current[path].count(old) == 1, "unique source seam: " + path)
        current[path] = current[path].replace(old, new)
    for path, record in spec["files"].items():
        exact(current[path], record["before" if reverse else "after"], path)
    return current


def inspect_source(source_root, root=ROOT):
    """Read/authenticate five exact derivation inputs, without mutation."""
    _, spec = source_guard(root)
    source_root = Path(source_root)
    require(source_root.is_dir() and not source_root.is_symlink(),
            "native source root")
    census = {}
    for path, record in spec["required_native_sources"].items():
        raw = secure(source_root, path).read_bytes()
        exact(raw, record, path)
        census[path] = dict(bytes=len(raw), sha256=digest(raw))
    before = {path: secure(source_root, path).read_bytes() for path in spec["files"]}
    after = transform(before, root)
    require(transform(after, root, reverse=True) == before, "reverse byte proof")
    return after, census


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--magic-source", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    after, census = inspect_source(args.magic_source)
    # No output path or source mutation occurs before all five inputs pass.
    require(not args.output.exists() and not args.output.is_symlink(),
            "output must be new")
    require(args.output.resolve() != args.magic_source.resolve()
            and args.magic_source.resolve() not in args.output.resolve().parents,
            "output outside native source")
    args.output.mkdir(parents=False, exist_ok=False)
    produced = {}
    for path, raw in after.items():
        target = args.output / path
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("xb") as handle:
            handle.write(raw)
        produced[path] = dict(bytes=len(raw), sha256=digest(raw))
    receipt = dict(schema=1, status="DERIVED_SOURCE_ONLY_NOT_BUILT",
                   source_census=census, derived_sources=produced,
                   source_reverse_bytes_equal=True, numerical_statements_changed=False,
                   source_controls_executed=False, native_build_executed=False,
                   native_output_equivalence_qualified=False,
                   physical_ownership_proved=False, physical_acceptance=False,
                   electrical_acceptance=False, full_phy_accepted=False)
    raw = (json.dumps(receipt, sort_keys=True, indent=2) + "\n").encode()
    with (args.output / "derivation-receipt.json").open("xb") as handle:
        handle.write(raw)
    print(raw.decode(), end="")


if __name__ == "__main__":
    main()
