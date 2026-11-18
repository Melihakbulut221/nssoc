#!/usr/bin/env python3
"""Boot the authenticated detailed-route netlist, without modifying producer inputs.

Cloud only. Functional, zero-delay native models; not equivalence or SDF signoff.
"""
import base64
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
from cloud_core_only_postgrt import (ROOT, api, sha, completed, restore_mapping,
    restore_cts, qualify_sources, current_path)
from cloud_core_only_clock_probe import restore_cts8
from cloud_core_only_clock_refine import restore_clock_split, restore_previous
from cloud_core_only_detailed_route import restore_refinement
from cloud_core_only_routed_extraction import restore_route, RUN, HEAD

OUT = ROOT / "hw/soc/out/core-only-routed-boot"
BOOT_HEAD = "31cb1846a8cf0eb683344e24c27a25438c22a75c"
QUAL_HEAD = "603c4d763128a3c238363c7d15e153eccff565e4"
HARNESS = {
    "flow/sim_logic_boot_gl.py": "d66bd9fbe6aa0e1ce66370b10cf40e94bcc5d5550819b2f1094c2c942bcd0613",
    "tb/tb_soc_logic_boot_gl.v": "42b97d8dd4d8434c87ba11d8e4dc2d16892f7cfb6d57672695d915d068b271ae",
    "tb/mapped_system_mbist_boot_monitor.v": "b1f67afb5b86a75f2fd195a4d756d638793af776939c109aaf59d4d7c6f2802e",
}

def source(path, head):
    obj = api("contents/" + path + "?ref=" + head)
    assert obj["encoding"] == "base64"
    return base64.b64decode(obj["content"])

def main():
    assert os.environ.get("GITHUB_ACTIONS") == "true"
    OUT.mkdir(parents=True, exist_ok=False)
    result = dict(source_head=os.environ["GITHUB_SHA"], status="PREPARING",
        accepted=False, final_timing_complete=False, equivalence_proven=False,
        routed_boot_passed=False, sdf_applied=False)
    def save():
        (OUT/"result.json").write_text(json.dumps(result, indent=2)+"\n")
    try:
        qualify_sources()
        mapping, mapmeta = restore_mapping()
        cts, ctsmeta, config, initial = restore_cts()
        assert cts["source_binding"]["netlist_sha256"] == mapping["outputs"]["synthesis/soc_top.netlist.v"]
        cts8, cts8meta, config, initial = restore_cts8(config)
        split, splitmeta, initial = restore_clock_split()
        previous, prevmeta, initial = restore_previous()
        refined, refmeta, initial = restore_refinement()
        routed, routemeta, initial = restore_route()
        state = json.loads(initial.read_text())
        netlist = current_path(state["nl"])
        result["source_binding"] = dict(route_run=RUN, route_head=HEAD,
            route_state=str(initial), routed_netlist=str(netlist),
            routed_netlist_sha256=sha(netlist),
            original_netlist_sha256=mapping["outputs"]["synthesis/soc_top.netlist.v"],
            artifacts=mapmeta+ctsmeta+[cts8meta, splitmeta, prevmeta]+refmeta+routemeta)
        completed(44239505985, QUAL_HEAD)
        completed(44239816779, BOOT_HEAD)
        sandbox = OUT/"harness/soc"
        for relative, digest in HARNESS.items():
            path = "hw/soc/"+relative
            data = source(path, BOOT_HEAD)
            assert hashlib.sha256(data).hexdigest() == digest, path
            assert data == source(path, QUAL_HEAD), path
            dest = sandbox/relative
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(data)
        flash = ROOT/"hw/soc/tb/flash_w25q128jv.v"
        assert flash.read_bytes() == source("hw/soc/tb/flash_w25q128jv.v", BOOT_HEAD)
        shutil.copy2(flash, sandbox/"tb/flash_w25q128jv.v")
        original = ROOT/"hw/soc/out/core-only-mainchip"
        synthesis = OUT/"simulation-input/synthesis"
        synthesis.mkdir(parents=True)
        shutil.copytree(original/"synthesis/boot-rom", synthesis/"boot-rom")
        shutil.copy2(netlist, synthesis/"soc_top.netlist.v")
        assert sha(synthesis/"soc_top.netlist.v") == sha(netlist)
        firmware = original/"rtl"
        inputs = [netlist, synthesis/"soc_top.netlist.v", flash, Path(__file__)]
        inputs += [p for p in sandbox.rglob("*") if p.is_file()]
        inputs += [p for p in (synthesis/"boot-rom").rglob("*") if p.is_file()]
        inputs += [p for p in firmware.rglob("*") if p.is_file()]
        protected = {str(p):sha(p) for p in inputs}
        result["protected_inputs"] = protected
        result["qualified_harness"] = dict(head=BOOT_HEAD, qualification_head=QUAL_HEAD, hashes=HARNESS)
        subprocess.run(["python3", "hw/soc/flow/prepare_ihp_native_boot.py"], check=True)
        command = ["python3", str(sandbox/"flow/sim_logic_boot_gl.py"),
            "--simulator", "iverilog", "--cycles", "4000000", "--timeout", "14400",
            "--pcie-profile", "off", "--mbist-profile", "system-only",
            "--nm", "/usr/bin/riscv64-linux-gnu-nm", "--synthesis", str(synthesis),
            "--firmware", str(firmware), "--pdk",
            str(ROOT/"hw/soc/tools/ihp-native-boot-c4b8b4e/ihp-sg13g2"),
            "--output", str(OUT/"simulation")]
        result.update(status="SIMULATING_ROUTED_NETLIST", command=command);save()
        with (OUT/"native.log").open("w") as log:
            result["returncode"] = subprocess.call(command, stdout=log, stderr=subprocess.STDOUT)
        boot = json.loads((OUT/"simulation/result.json").read_text())
        result["boot_result"] = boot
        assert result["returncode"] == 0 and boot["passed"] and boot["sources_unchanged"]
        assert all(sha(p)==h for p,h in protected.items())
        # Recheck original source binding too; no qualified harness is copied over RTL/flow sources.
        assert all(sha(ROOT/p)==h for p,h in mapping["source_binding"]["before"].items())
        result.update(status="PASS_ROUTED_NATIVE_FUNCTIONAL_BOOT_REQUIRES_PHYSICAL_SIGNOFF",
            routed_boot_passed=True, sources_unchanged=True)
    except BaseException as error:
        result.update(status="FAIL_OR_INCOMPLETE", error=repr(error));raise
    finally:
        result["outputs"] = {str(p.relative_to(OUT)):sha(p) for p in OUT.rglob("*")
            if p.is_file() and p!=OUT/"result.json" and p.suffix in (".json", ".log", ".v")}
        save()

if __name__ == "__main__":
    main()
