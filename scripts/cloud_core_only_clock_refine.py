#!/usr/bin/env python3
"""Post-GRT repair of the routed candidate with zero clock fanout violations."""
from collections import deque
import json
import os
from pathlib import Path
import stat
import subprocess
from bootstrap_flow import verify
from cloud_core_only_postgrt import (
    ROOT, MAP_RUN, MAP_HEAD, CTS_RUN, CTS_HEAD, GUARD_RUN, GUARD_HEAD,
    sha, completed, archive, safe_path, put, current_path,
    restore_mapping, restore_cts, qualify_sources, fresh_corner_metrics,
)
from cloud_core_only_clock_probe import restore_cts8
OUT = ROOT / "hw/soc/out/core-only-clock-refine"


def restore_clock_split():
    run = completed(44253264552, "45932c71e85db517f87e01f2a7f6b80cd1bc045c")
    native, metadata = archive(run, "core-only-clock-split-native-44253264552")
    assert metadata["id"] == 14406590032
    assert metadata["digest"] == "sha256:05aa32fcffadd1bfed7e2641a1968682dc651ad27e83dcc9bb71d9959015056e"
    raw = native.read("result.json")
    report = json.loads(raw)
    assert report["source_head"] == run["head_sha"]
    assert report["status"] == "CLOCK_SPLIT_ROUTED_REQUIRES_DETAILED_ROUTE_AND_SIGNOFF"
    assert report["sources_unchanged"] and not report["accepted"]
    assert report["source_binding"]["cts8_run"] == 44246559242
    root = ROOT / "hw/soc/out/core-only-clock-split"
    restored = set()
    for info in native.infolist():
        if info.is_dir() or info.filename == "result.json":
            continue
        assert not stat.S_ISLNK(info.external_attr >> 16)
        name = info.filename
        assert name in report["outputs"] and name not in restored
        put(safe_path(root, name), native.read(info), report["outputs"][name])
        restored.add(name)
    assert restored == set(report["outputs"])
    root.joinpath("result.json").write_bytes(raw)
    for name, digest in report["protected_inputs"].items():
        assert sha(current_path(name)) == digest, name
    for phase in report["phases"].values():
        for entry in phase["corners"].values():
            metrics, path = fresh_corner_metrics(safe_path(root, entry["state"]), entry["corner_name"])
            assert sha(path) == entry["metrics_sha256"] and metrics == entry["metrics"]
    for entry in report["phases"]["routing"]["corners"].values():
        assert entry["metrics"]["design__max_fanout_violation__count"] == 0
    logs = list((root / "split").glob("1-*/*.log"))
    assert len(logs) == 1
    text = logs[0].read_text()
    assert text.count("CORE_CLOCK_ECO_VERIFIED all_original_terminals_checked added_cells=2 added_nets=2 root_loads=2 branch_loads=8,8") == 2
    assert len([line for line in text.splitlines() if line.startswith("CORE_CLOCK_ECO_MOVE ")]) == 16
    initial = safe_path(root, report["output_state"])
    state = json.loads(initial.read_text())
    for key in ("odb", "nl", "def", "sdc"):
        if state.get(key):
            p = current_path(state[key])
            assert root in p.parents, (key, p)
            assert sha(p) == report["outputs"][str(p.relative_to(root))]
    return report, metadata, initial


def restore_previous():
    run = completed(44256809783, "0a055a1269f48e386e01b95eada858ae25671429")
    native, metadata = archive(run, "core-only-clock-postgrt-native-44256809783")
    assert metadata["id"] == 14407012633
    assert metadata["digest"] == "sha256:9a3e8c9c4a4def31a992bc9711b8222961ff3aaf468817af206185df8914cbe4"
    raw = native.read("result.json")
    report = json.loads(raw)
    assert report["source_head"] == run["head_sha"]
    assert report["status"] == "CLOCK_POSTGRT_COMPLETE_REQUIRES_DETAILED_ROUTE_AND_SIGNOFF"
    assert report["sources_unchanged"] and not report["accepted"]
    assert report["source_binding"]["clock_split_run"] == 44253264552
    root = ROOT / "hw/soc/out/core-only-clock-postgrt"
    restored = set()
    for info in native.infolist():
        if info.is_dir() or info.filename == "result.json":
            continue
        assert not stat.S_ISLNK(info.external_attr >> 16)
        name = info.filename
        assert name in report["outputs"] and name not in restored
        put(safe_path(root, name), native.read(info), report["outputs"][name])
        restored.add(name)
    assert restored == set(report["outputs"])
    root.joinpath("result.json").write_bytes(raw)
    for name, digest in report["protected_inputs"].items():
        assert sha(current_path(name)) == digest, name
    for phase in report["phases"].values():
        for entry in phase["corners"].values():
            metrics, path = fresh_corner_metrics(safe_path(root, entry["state"]), entry["corner_name"])
            assert sha(path) == entry["metrics_sha256"] and metrics == entry["metrics"]
    for entry in report["phases"]["timing"]["corners"].values():
        assert entry["metrics"]["design__max_fanout_violation__count"] == 0
        assert entry["metrics"]["timing__hold_vio__count"] == 0
    initial = safe_path(root, report["output_state"])
    state = json.loads(initial.read_text())
    for key in ("odb", "nl", "def", "sdc"):
        if state.get(key):
            p = current_path(state[key])
            assert root in p.parents, (key, p)
            assert sha(p) == report["outputs"][str(p.relative_to(root))]
    return report, metadata, initial


def main():
    assert os.environ.get("GITHUB_ACTIONS") == "true", "Cloud-only runner"
    OUT.mkdir(parents=True, exist_ok=False)
    report = dict(source_head=os.environ["GITHUB_SHA"], status="RUNNING",
                  accepted=False, final_timing_complete=False, mapped_boot_passed=False,
                  parasitics="global-route estimate; detailed routing and qualified extraction required",
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
        cts8, cts8_meta, config, initial = restore_cts8(config)
        split, split_meta, initial = restore_clock_split()
        previous, previous_meta, initial = restore_previous()
        report["source_binding"].update(cts8_run=44246559242, cts8_artifact=cts8_meta,
            clock_split_run=44253264552, clock_split_artifact=split_meta,
            previous_repair_run=44256809783, previous_repair_artifact=previous_meta)
        report["baseline_corners"] = previous["phases"]["timing"]["corners"]
        report["max_setup_iterations"] = 200
        app = Path(os.environ["CLOUD_APPIMAGE"])
        verify(app, "x86_64")
        flow = ROOT / "hw/soc/pnr/core_only_route_refine200_flow.py"
        paths = [Path(__file__), ROOT / "scripts/cloud_core_only_clock_probe.py", ROOT / "scripts/cloud_core_only_clock_split.py", ROOT / "scripts/cloud_core_only_route_refine.py", ROOT / "hw/soc/pnr/core_only_postgrt_flow.py", ROOT / "scripts/cloud_core_only_postgrt.py", flow, ROOT / "hw/soc/pnr/core_only_globalroute_flow.py", ROOT / "hw/soc/pnr/core_only_postcts_flow.py", ROOT / "hw/soc/pnr/interface_flow.py",
                 ROOT / "hw/soc/flow/check_timing_derate.tcl", config,
                 config.parent / "physical.sdc", initial,
                 current_path(json.loads(initial.read_text())["odb"])]
        protected = {str(p): sha(p) for p in paths}
        report["protected_inputs"] = protected
        save()
        for phase, flow_name, after in [
                ("electrical", "CoreOnlyRouteElectricalTrial", "routeelectricalafter"),
                ("timing", "CoreOnlyRouteTiming200Trial", "routetimingafter")]:
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
        report["metric_deltas"] = {
            corner: {key: value - report["baseline_corners"][corner]["metrics"][key]
                     for key, value in entry["metrics"].items()}
            for corner, entry in report["phases"]["timing"]["corners"].items()
        }
        report.update(status="CLOCK_REFINE_COMPLETE_REQUIRES_DETAILED_ROUTE_AND_SIGNOFF",
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

