#!/usr/bin/env python3
"""Hosted source-only controls. Does not compile or execute Magic.

  python scripts/check_magic_resistor_provenance.py --output REPORT.json
"""
from __future__ import annotations
import argparse
import copy
import json
import tempfile
from pathlib import Path
import patch_magic_resistor_provenance as p


def controls():
    positive, refused = [], []
    pins, spec = p.source_guard()
    positive.append("authentic_source_guard")
    before = {name: p.secure(p.ROOT, item["snapshot"]).read_bytes()
              for name, item in spec["files"].items()}
    after = p.transform(before)
    assert p.transform(after, reverse=True) == before
    # Source proof only: all original bytes survive in exact order.
    for path in before:
        cursor = 0
        for line in before[path].splitlines(keepends=True):
            at = after[path].find(line, cursor)
            assert at >= cursor
            cursor = at + len(line)
    positive.append("actual_five_file_forward_reverse_bytes")
    for path in before:
        for mode in ("missing", "changed_byte", "wrong_direction"):
            bad = dict(before)
            if mode == "missing":
                del bad[path]
            elif mode == "changed_byte":
                bad[path] += b"\n/* deliberate hosted source mutation */\n"
            else:
                bad[path] = after[path]
            try:
                p.transform(bad)
            except AssertionError:
                refused.append(mode + ":" + path)
            else:
                raise AssertionError("source mutation admitted")
    with tempfile.TemporaryDirectory(prefix="magic-provenance-source-control-") as directory:
        root = Path(directory)
        native = root / "input"
        native.mkdir()
        for name, raw in before.items():
            dest = native / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(raw)
        derived, census = p.inspect_source(native)
        assert derived == after and len(census) == 5
        positive.append("actual_five_file_source_inspection")
        target = native / "resis/ResPrint.c"
        target.unlink()
        target.symlink_to(p.secure(p.ROOT, spec["files"]["resis/ResPrint.c"]["snapshot"]))
        try:
            p.inspect_source(native)
        except AssertionError as error:
            assert "symlink" in str(error)
            refused.append("symlink_native_source")
        else:
            raise AssertionError("source symlink admitted")
        target.unlink()
        try:
            p.inspect_source(native)
        except AssertionError as error:
            assert "missing regular source" in str(error)
            refused.append("missing_native_source")
        else:
            raise AssertionError("missing native source admitted")
        projected = root / "protected-projection"
        projected.mkdir()
        for name in [p.PINS, *pins["files"]]:
            raw = p.secure(p.ROOT, name).read_bytes()
            dest = projected / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(raw)
        p.source_guard(projected)
        positive.append("complete_source_projection")
        for name in (p.SPEC, "scripts/magic_resistor_provenance_trace.inc"):
            dest = projected / name
            raw = dest.read_bytes()
            dest.write_bytes(raw + b"\n")
            try:
                p.source_guard(projected)
            except AssertionError as error:
                assert "source bytes" in str(error)
                refused.append("protected_payload_corruption:" + name)
            else:
                raise AssertionError("corrupt patch payload admitted")
            finally:
                dest.write_bytes(raw)
    assert len(positive) == 4 and len(refused) == 19
    return dict(schema=1, status="PASS_RESISTOR_PROVENANCE_SOURCE_CONTROLS",
                positive=positive, positive_count=len(positive),
                refusals=refused, refusal_count=len(refused),
                synthetic_native_execution=False, native_executed=False,
                c_compilation_executed=False, native_output_equivalence_qualified=False,
                physical_ownership_proved=False, physical_acceptance=False,
                electrical_acceptance=False, full_phy_accepted=False,
                note="Authentic source-byte controls only; no runtime struct, native trace, "
                     "numerical output equivalence, build, or extraction qualification.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    error = None
    try:
        report = controls()
    except BaseException as exc:
        error = exc
        report = dict(schema=1, status="FAIL_RESISTOR_PROVENANCE_SOURCE_CONTROLS",
                      error=repr(exc), native_executed=False,
                      native_output_equivalence_qualified=False,
                      physical_acceptance=False, full_phy_accepted=False)
    raw = json.dumps(report, indent=2, sort_keys=True) + "\n"
    print(raw, end="", flush=True)
    try:
        with args.output.open("x", encoding="utf-8") as handle:
            handle.write(raw)
    except BaseException:
        if error is None:
            raise
    if error is not None:
        raise error


if __name__ == "__main__":
    main()
