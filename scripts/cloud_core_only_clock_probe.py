#!/usr/bin/env python3
"""Cloud-only authenticated native connectivity probe for the remaining CTS8 failures."""
import json
import os
from pathlib import Path
import stat
import subprocess
from bootstrap_flow import verify
from cloud_core_only_postgrt import (
    ROOT, MAP_RUN, MAP_HEAD, sha, completed, archive, safe_path, put,
    current_path, restore_mapping, restore_cts, qualify_sources, fresh_corner_metrics,
)
OUT = ROOT / "hw/soc/out/core-only-clock-probe"


def restore_cts8(original_config):
    run = completed(44246559242, "67e18d0c5ffec9db966d8733b5e5971d2422047c")
    native, metadata = archive(run, "core-only-cts8-native-44246559242")
    assert metadata["id"] == 14402843316
    assert metadata["digest"] == "sha256:3378e8d44bf485cf28dde3e91389629d5de877e5aae7f59c6cf12daac3233bdc"
    raw = native.read("result.json")
    report = json.loads(raw)
    assert report["source_head"] == run["head_sha"]
    assert report["status"] == "CTS8_TRIAL_COMPLETE_REQUIRES_ROUTING_AND_SIGNOFF"
    assert report["sources_unchanged"] and not report["accepted"]
    assert report["source_binding"]["mapping_run"] == MAP_RUN
    root = ROOT / "hw/soc/out/core-only-cts8"
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
    delta = {"CTS_SINK_CLUSTERING_ENABLE": True,
             "CTS_SINK_CLUSTERING_SIZE": 8, "CTS_MACRO_CLUSTERING_SIZE": 8}
    assert report["source_binding"]["config_delta"] == delta
    values = json.loads(original_config.read_text())
    assert not any(key in values for key in delta)
    config = original_config.parent / "config-cts8.json"
    assert not config.exists()
    config.write_text(json.dumps(dict(values, **delta), indent=2) + "\n")
    for name, digest in report["protected_inputs"].items():
        assert sha(current_path(name)) == digest, name
    for phase in report["phases"].values():
        for entry in phase["corners"].values():
            metrics, path = fresh_corner_metrics(safe_path(root, entry["state"]), entry["corner_name"])
            assert sha(path) == entry["metrics_sha256"] and metrics == entry["metrics"]
    initial = safe_path(root, report["output_state"])
    state = json.loads(initial.read_text())
    odb = current_path(state["odb"])
    assert root in odb.parents
    assert sha(odb) == report["outputs"][str(odb.relative_to(root))]
    return report, metadata, config, initial


def main():
    assert os.environ.get("GITHUB_ACTIONS") == "true"
    OUT.mkdir(parents=True, exist_ok=False)
    report = dict(source_head=os.environ["GITHUB_SHA"], status="RUNNING", accepted=False)
    def save():
        (OUT / "result.json").write_text(json.dumps(report, indent=2) + "\n")
    try:
        qualify_sources()
        mapping, map_artifacts = restore_mapping()
        cts, cts_artifacts, config, _ = restore_cts()
        assert cts["source_binding"]["netlist_sha256"] == mapping["outputs"]["synthesis/soc_top.netlist.v"]
        previous, metadata, config, initial = restore_cts8(config)
        report["source_binding"] = dict(mapping_run=MAP_RUN, mapping_head=MAP_HEAD,
            cts8_run=44246559242, artifacts=map_artifacts + cts_artifacts + [metadata])
        flow = ROOT / "hw/soc/pnr/core_only_clock_probe_flow.py"
        odb = current_path(json.loads(initial.read_text())["odb"])
        paths = [Path(__file__), flow, ROOT / "scripts/cloud_core_only_postgrt.py",
                 ROOT / "hw/soc/pnr/core_only_postcts_flow.py", config, initial, odb,
                 config.parent / "physical.sdc"]
        protected = {str(p): sha(p) for p in paths}
        report["protected_inputs"] = protected
        save()
        app = Path(os.environ["CLOUD_APPIMAGE"])
        verify(app, "x86_64")
        directory = OUT / "probe"
        directory.mkdir()
        command = [str(app), "python", str(flow), "--flow", "CoreOnlyClockProbe",
                   "--pdk-root", str(ROOT / "hw/soc/tools/ciel-corrpre"),
                   "--pdk", "ihp-sg13g2", "--scl", "sg13g2_stdcell",
                   "--force-run-dir", str(directory), "--with-initial-state", str(initial), str(config)]
        report["command"] = command
        with (OUT / "native.log").open("w") as log:
            code = subprocess.call(command, stdout=log, stderr=subprocess.STDOUT)
        report["returncode"] = code
        if code:
            print((OUT / "native.log").read_text()[-12000:])
            raise RuntimeError("Native clock probe failed")
        states = list(directory.glob("*-nssoc-coreonlyclockprobeslow/state_out.json"))
        assert len(states) == 1
        metrics, path = fresh_corner_metrics(states[0], "nom_slow_1p08V_125C")
        report.update(metrics=metrics, metrics_source=str(path.relative_to(OUT)), metrics_sha256=sha(path))
        logs = list(states[0].parent.glob("*.log"))
        lines = [line for log in logs for line in log.read_text(errors="replace").splitlines()
                 if line.startswith("CORE_PROBE_")]
        assert "CORE_PROBE_COMPLETE_NO_DATABASE_EDITS" in lines
        report["connectivity_probe"] = lines
        assert all(sha(p) == digest for p, digest in protected.items())
        report.update(status="NATIVE_CONNECTIVITY_PROBE_COMPLETE_NOT_SIGNOFF", sources_unchanged=True)
    except BaseException as error:
        report.update(status="FAIL_OR_ERROR", error=repr(error))
        raise
    finally:
        report["outputs"] = {str(p.relative_to(OUT)): sha(p) for p in OUT.rglob("*")
                             if p.is_file() and p != OUT / "result.json"}
        save()

if __name__ == "__main__":
    main()
