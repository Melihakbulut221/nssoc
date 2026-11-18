#!/usr/bin/env python3
"""Verify complementary base/full pin-level interfaces, including CAN/SpaceWire."""
import ast
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET

ROOT = Path.cwd().resolve()
OUT = ROOT / "hw/soc/out/core-only-interface-profiles"
TB = ROOT / "hw/soc/tb/cocotb"
FULL_ONLY = {
    "spacewire_packets_timecodes_and_disconnect",
    "spacewire_credit_backpressure_preserves_order",
    "can_two_node_standard_frame_and_byte_lanes",
    "can_extended_id_eight_bytes_and_remote_frame",
    "can_bank_aliases_preserve_full_width_write_decode",
    "can_basic_mode_frame_uses_separate_tx_rx_windows",
}
BASE_ONLY = {"disabled_optional_slots_return_errors"}

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    assert os.environ.get("GITHUB_ACTIONS") == "true", "Cloud-only"
    OUT.mkdir(parents=True, exist_ok=False)
    result = dict(source_head=os.environ["GITHUB_SHA"], status="RUNNING",
                  accepted=False, physical_signoff=False, profiles={})
    def save():
        (OUT / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    try:
        tree = ast.parse((TB / "test_soc_interfaces.py").read_text())
        names = {n.name for n in tree.body if isinstance(n, ast.AsyncFunctionDef)
                 and any(isinstance(d, ast.Call) and isinstance(d.func, ast.Attribute)
                         and d.func.attr == "test" for d in n.decorator_list)}
        assert len(names) == 14 and FULL_ONLY | BASE_ONLY <= names
        tracked = subprocess.check_output([
            "git", "ls-files", "-z", "hw/soc/rtl", "hw/soc/tb/cocotb",
            "hw/soc/flow", "scripts/check_core_only_interface_profiles.py"])
        before = {p: sha(ROOT / p) for p in tracked.decode().split("\0") if p}
        result["source_sha256"] = before
        save()
        sys.path.insert(0, str(ROOT / "hw/soc/flow"))
        from interface_profile import resolve
        all_passed = set()
        for profile in ("base", "full"):
            env = dict(os.environ, SOC_INTERFACE_PROFILE=profile, SOC_RELEASE_PROFILE="core-only")
            with (OUT / (profile + "-prepare.log")).open("w") as log:
                subprocess.run(["make", "soc-interfaces-prepare", "SOC_INTERFACE_PROFILE=" + profile,
                                "INTERFACE_PYTHON=" + sys.executable],
                               env=env, stdout=log, stderr=subprocess.STDOUT, check=True, timeout=1200)
            bundle, define = resolve(profile)
            bundle_hash = sha(bundle)
            manifest = json.loads(bundle.with_suffix(".json").read_text())
            xml = OUT / (profile + ".xml")
            assert not xml.exists()
            command = ["make", "-C", str(TB), "-f", "Makefile.soc_interfaces",
                       "SOC_INTERFACE_PROFILE=" + profile, "SIM_BUILD=" + str(OUT / (profile + "-sim")),
                       "COCOTB_RESULTS_FILE=" + str(xml)]
            with (OUT / (profile + "-simulation.log")).open("w") as log:
                proc = subprocess.run(command, env=env, stdout=log, stderr=subprocess.STDOUT, timeout=1200)
            entry = dict(command=command, returncode=proc.returncode, bundle_sha256=bundle_hash,
                         bundle_manifest=manifest, compile_define=define)
            result["profiles"][profile] = entry
            save()
            assert proc.returncode == 0, (profile, proc.returncode)
            cases = list(ET.parse(xml).getroot().iter("testcase"))
            assert len(cases) == len(names)
            assert {c.get("name") for c in cases} == names
            failed = {c.get("name") for c in cases if c.find("failure") is not None or c.find("error") is not None}
            skipped = {c.get("name") for c in cases if c.find("skipped") is not None}
            expected_skips = FULL_ONLY if profile == "base" else BASE_ONLY
            assert not failed and skipped == expected_skips, (profile, failed, skipped)
            passed = names - skipped
            if profile == "full": assert FULL_ONLY <= passed
            entry.update(passed=sorted(passed), skipped=sorted(skipped), xml_sha256=sha(xml))
            assert sha(resolve(profile)[0]) == bundle_hash
            all_passed |= passed
            save()
        assert all_passed == names
        assert all(sha(ROOT / p) == h for p, h in before.items())
        result.update(status="ALL_14_INTERFACE_CASES_COVERED_ACROSS_BASE_AND_FULL",
                      sources_unchanged=True, union_passed=sorted(all_passed),
                      scope="Pin-level APB peripheral RTL with actual prepared bundles; not CPU/netlist/padframe signoff")
    except BaseException as error:
        result.update(status="FAIL_OR_ERROR", error=repr(error))
        raise
    finally:
        result["outputs"] = {str(p.relative_to(OUT)): sha(p) for p in OUT.rglob("*")
                             if p.is_file() and p.name != "result.json"}
        save()

if __name__ == "__main__":
    main()
