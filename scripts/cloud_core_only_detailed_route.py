#!/usr/bin/env python3
"""Detailed-route selected core-only refinement; execution is never signoff."""
from collections import deque
import json
import os
from pathlib import Path
import stat
import subprocess
from bootstrap_flow import verify
from cloud_core_only_postgrt import (ROOT, sha, completed, archive, safe_path, put,
    current_path, restore_mapping, restore_cts, qualify_sources, fresh_corner_metrics)
from cloud_core_only_clock_probe import restore_cts8
from cloud_core_only_clock_refine import restore_clock_split, restore_previous

OUT = ROOT / "hw/soc/out/core-only-detailed-route"
RUN = 44259265143
HEAD = "572c3eb98392b0f56351d5aaf4f256499b4b8d9f"


def restore_refinement():
    run = completed(RUN, HEAD)
    native, metadata = archive(run, f"core-only-clock-refine-native-{RUN}")
    summary, summary_metadata = archive(run, f"core-only-clock-refine-summary-{RUN}")
    assert metadata["id"] == 14408985519
    assert metadata["digest"] == "sha256:abc9267b370aa3bc2b5c42ccc4c3a9381e2e5a1058e3a4bded78d5f7744f3cc4"
    assert summary_metadata["id"] == 14408162501
    assert summary_metadata["digest"] == "sha256:a6c299889cff6d90e29f351c6c7c5ab9a5b78b2dabf4e72cd5bfe0ffaa3ef120"
    raw = native.read("result.json")
    assert raw == summary.read("result.json")
    report = json.loads(raw)
    assert report["source_head"] == HEAD
    assert report["status"] == "CLOCK_REFINE_COMPLETE_REQUIRES_DETAILED_ROUTE_AND_SIGNOFF"
    assert report["sources_unchanged"] and not report["accepted"]
    assert report["source_binding"]["previous_repair_run"] == 44256809783
    root = ROOT / "hw/soc/out/core-only-clock-refine"
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
    # Admission for this initial route trial, not a product acceptance gate.
    # Setup and electrical residuals must remain recorded, never zeroed/waived.
    for entry in report["phases"]["timing"]["corners"].values():
        assert entry["metrics"]["design__max_fanout_violation__count"] == 0
        assert entry["metrics"]["timing__hold_vio__count"] == 0
    initial = safe_path(root, report["output_state"])
    state = json.loads(initial.read_text())
    for key in ("odb", "nl", "def", "sdc"):
        assert state.get(key), key
        p = current_path(state[key])
        assert root in p.parents, (key, p)
        assert sha(p) == report["outputs"][str(p.relative_to(root))]
    return report, [metadata, summary_metadata], initial


def main():
    assert os.environ.get("GITHUB_ACTIONS") == "true", "Cloud-only runner"
    OUT.mkdir(parents=True, exist_ok=False)
    result = dict(source_head=os.environ["GITHUB_SHA"], status="PREPARING",
                  accepted=False, final_timing_complete=False, full_chip_lvs_passed=False,
                  manufacturing_approval=False, phases={})
    def save():
        (OUT / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    try:
        qualify_sources()
        mapping, mapping_artifacts = restore_mapping()
        cts, cts_artifacts, config, initial = restore_cts()
        assert cts["source_binding"]["netlist_sha256"] == mapping["outputs"]["synthesis/soc_top.netlist.v"]
        cts8, cts8_metadata, config, initial = restore_cts8(config)
        split, split_metadata, initial = restore_clock_split()
        previous, previous_metadata, initial = restore_previous()
        refined, refined_metadata, initial = restore_refinement()
        result["source_binding"] = dict(refinement_run=RUN, refinement_head=HEAD,
            artifacts=mapping_artifacts + cts_artifacts + [cts8_metadata, split_metadata,
                previous_metadata] + refined_metadata)
        result["baseline_corners"] = refined["phases"]["timing"]["corners"]
        app = Path(os.environ["CLOUD_APPIMAGE"])
        verify(app, "x86_64")
        flow = ROOT / "hw/soc/pnr/core_only_detailed_route_flow.py"
        paths = [Path(__file__), flow, config, config.parent / "physical.sdc", initial,
            current_path(json.loads(initial.read_text())["odb"])]
        for name in ["scripts/cloud_core_only_postcts.py", "scripts/cloud_core_only_postgrt.py",
            "scripts/cloud_core_only_clock_probe.py", "scripts/cloud_core_only_clock_refine.py",
            "hw/soc/pnr/core_only_postcts_flow.py", "hw/soc/pnr/interface_flow.py",
            "hw/soc/flow/check_timing_derate.tcl", "hw/soc/flow/prune_orphan_guides.tcl"]:
            paths.append(ROOT / name)
        protected = {str(p): sha(p) for p in paths}
        result["protected_inputs"] = protected
        directory = OUT / "routing"
        directory.mkdir(parents=True, exist_ok=False)
        command = [str(app), "python", str(flow), "--flow", "CoreOnlyDetailedRoute",
            "--pdk-root", str(ROOT / "hw/soc/tools/ciel-corrpre"), "--pdk", "ihp-sg13g2",
            "--scl", "sg13g2_stdcell", "--force-run-dir", str(directory),
            "--with-initial-state", str(initial), str(config)]
        result.update(status="ROUTING", command=command)
        save()
        with (OUT / "routing.log").open("w") as log:
            code = subprocess.call(command, stdout=log, stderr=subprocess.STDOUT)
        result["returncode"] = code
        if code:
            with (OUT / "routing.log").open() as log:
                print("".join(deque(log, maxlen=60)), flush=True)
            raise RuntimeError("Native detailed routing flow failed")
        states = list(directory.glob("*-nssoc-coreonlydetailedrouting/state_out.json"))
        assert len(states) == 1, states
        routed = states[0]
        state = json.loads(routed.read_text())
        for key in ("odb", "def", "nl", "sdc"):
            path = current_path(state[key])
            assert directory in path.parents, (key, path)
        metrics = routed.parent / "or_metrics_out.json"
        assert metrics.is_file()
        # Archive current DRT-process metrics as evidence. Do not inherit or
        # promote state.metrics/pre-route STA to extracted timing results.
        result["routing_metrics"] = dict(path=str(metrics.relative_to(OUT)),
            sha256=sha(metrics), values=json.loads(metrics.read_text()))
        assert all(sha(p) == digest for p, digest in protected.items())
        result.update(status="DETAILED_ROUTE_EXECUTED_REQUIRES_CONNECTIVITY_RC_AND_SIGNOFF_AUDIT",
            sources_unchanged=True, routed_state=str(routed.relative_to(OUT)),
            extraction_executed=False, annotation_qualified=False)
    except BaseException as error:
        result.update(status="FAIL_OR_INCOMPLETE", error=repr(error))
        raise
    finally:
        result["outputs"] = {str(p.relative_to(OUT)): sha(p) for p in OUT.rglob("*")
            if p.is_file() and p != OUT / "result.json"}
        save()

if __name__ == "__main__":
    main()
