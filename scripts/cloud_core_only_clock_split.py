#!/usr/bin/env python3
"""Cloud-only targeted clock split with complete original-terminal preservation checks."""
from collections import deque
import json
import os
from pathlib import Path
import subprocess
from bootstrap_flow import verify
from cloud_core_only_postgrt import (
    ROOT, MAP_RUN, MAP_HEAD, CTS_RUN, CTS_HEAD, GUARD_RUN, GUARD_HEAD,
    sha, current_path, restore_mapping, restore_cts, qualify_sources, fresh_corner_metrics,
)
from cloud_core_only_clock_probe import restore_cts8
OUT = ROOT / "hw/soc/out/core-only-clock-split"

def main():
    assert os.environ.get("GITHUB_ACTIONS") == "true", "Cloud-only runner"
    OUT.mkdir(parents=True, exist_ok=False)
    report = dict(source_head=os.environ["GITHUB_SHA"], status="RUNNING",
                  accepted=False, final_timing_complete=False, mapped_boot_passed=False,
                  parasitics="split/electrical/timing: placement estimates; routing: global-route estimates; detailed extraction required",
                  phases={})
    def save():
        (OUT / "result.json").write_text(json.dumps(report, indent=2) + "\n")
    try:
        qualify_sources()
        mapping, map_artifacts = restore_mapping()
        cts, cts_artifacts, config, initial = restore_cts()
        assert cts["source_binding"]["netlist_sha256"] == mapping["outputs"]["synthesis/soc_top.netlist.v"]
        report["source_binding"] = dict(mapping_run=MAP_RUN, mapping_head=MAP_HEAD,
                                        cts_run=CTS_RUN, cts_head=CTS_HEAD,
                                        guard_run=GUARD_RUN, guard_head=GUARD_HEAD,
                                        artifacts=map_artifacts + cts_artifacts,
                                        cts_odb_sha256=cts["cts_odb_sha256"])
        previous, cts8_meta, config, initial = restore_cts8(config)
        report["source_binding"]["cts8_run"] = 44246559242
        report["source_binding"]["cts8_artifact"] = cts8_meta
        report["baseline_corners"] = previous["phases"]["timing"]["corners"]
        app = Path(os.environ["CLOUD_APPIMAGE"])
        verify(app, "x86_64")
        flow = ROOT / "hw/soc/pnr/core_only_clock_split_flow.py"
        paths = [Path(__file__), flow, ROOT / "scripts/cloud_core_only_clock_probe.py", ROOT / "scripts/cloud_core_only_postgrt.py", ROOT / "hw/soc/flow/core_only_clock_split.tcl", ROOT / "hw/soc/pnr/core_only_globalroute_flow.py", ROOT / "hw/soc/pnr/core_only_postcts_flow.py", ROOT / "hw/soc/pnr/interface_flow.py",
                 ROOT / "hw/soc/flow/check_timing_derate.tcl", config,
                 config.parent / "physical.sdc", initial,
                 current_path(json.loads(initial.read_text())["odb"])]
        protected = {str(p): sha(p) for p in paths}
        report["protected_inputs"] = protected
        save()
        for phase, flow_name, after in [
                ("split", "CoreOnlyClockSplitTrial", "splitafter"),
                ("electrical", "CoreOnlyElectricalTrial", "electricalafter"),
                ("timing", "CoreOnlyTimingTrial", "timingafter"),
                ("routing", "CoreOnlyClockSplitRoute", "splitrouted")]:
            directory = OUT / phase
            directory.mkdir(parents=True, exist_ok=False)
            command = [str(app), "python", str(flow), "--flow", flow_name,
                       "--pdk-root", str(ROOT / "hw/soc/tools/ciel-corrpre"),
                       "--pdk", "ihp-sg13g2", "--scl", "sg13g2_stdcell",
                       "--force-run-dir", str(directory),
                       "--with-initial-state", str(initial), str(config)]
            entry = dict(command=command, status="RUNNING", accepted=False)
            report["phases"][phase] = entry
            save()
            with (OUT / (phase + ".log")).open("w") as log:
                code = subprocess.call(command, stdout=log, stderr=subprocess.STDOUT)
            entry["returncode"] = code
            entry["status"] = "NATIVE_FLOW_FAILED" if code else "MEASURING_OUTPUTS"
            save()
            if code:
                with (OUT / (phase + ".log")).open() as log:
                    print("".join(deque(log, maxlen=60)), flush=True)
                raise RuntimeError(phase + " native flow failed")
            entry["corners"] = {}
            for corner, corner_name in (("slow", "nom_slow_1p08V_125C"),
                                        ("typical", "nom_typ_1p20V_25C"),
                                        ("fast", "nom_fast_1p32V_m40C")):
                states = list(directory.glob("*-nssoc-coreonly" + after + corner + "/state_out.json"))
                assert len(states) == 1, (phase, corner, states)
                fresh, native_metrics = fresh_corner_metrics(states[0], corner_name)
                entry["corners"][corner] = dict(state=str(states[0].relative_to(OUT)),
                                                corner_name=corner_name,
                                                metrics_source=str(native_metrics.relative_to(OUT)),
                                                metrics_sha256=sha(native_metrics), metrics=fresh)
                if corner == "fast":
                    initial = states[0]
            assert all(sha(p) == digest for p, digest in protected.items())
            entry["status"] = "TRIAL_COMPLETE_NOT_SIGNOFF"
            entry["output_state"] = str(initial.relative_to(OUT))
            save()
        report.update(status="CLOCK_SPLIT_ROUTED_REQUIRES_DETAILED_ROUTE_AND_SIGNOFF",
                      sources_unchanged=True, output_state=str(initial.relative_to(OUT)))
    except BaseException as error:
        for entry in report["phases"].values():
            if entry["status"] in ("RUNNING", "MEASURING_OUTPUTS"):
                entry.update(status="FAIL_OR_ERROR", error=repr(error))
        report.update(status="FAIL_OR_ERROR", error=repr(error))
        raise
    finally:
        report["outputs"] = {str(p.relative_to(OUT)): sha(p) for p in OUT.rglob("*")
                             if p.is_file() and p != OUT / "result.json"}
        save()

if __name__ == "__main__":
    main()

