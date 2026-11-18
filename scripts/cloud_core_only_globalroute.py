#!/usr/bin/env python3
"""Restore authenticated repaired core-only CTS and run global routing.

PostCTS estimated parasitics and trial completion are never final timing,
mapped boot, LVS, DRC, or production acceptance.
"""
from collections import deque
import hashlib
import io
import json
import math
import os
from pathlib import Path
import stat
import subprocess
import tarfile
import zipfile
from bootstrap_flow import verify

ROOT = Path.cwd().resolve()
OUT = ROOT / "hw/soc/out/core-only-globalroute"
REPO = "repos/Melihakbulut221/nssoc/"
MAP_RUN, MAP_HEAD = 44238569057, "bfb1fcc1bcd1d2def770ac26bd978767b0466e32"
CTS_RUN, CTS_HEAD = 44239812957, "3b5938b3d2cdea3951c7b9067f296b696e29c9e3"
GUARD_RUN, GUARD_HEAD = 44240371021, "d145b505c308d875d074471d88a0882575cc6f3f"
MASTER = "RM_IHPSG13_1P_2048x64_c2_bm_bist"

def api(path):
    return json.loads(subprocess.check_output(["gh", "api", REPO + path]))

def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def completed(run_id, head):
    run = api(f"actions/runs/{run_id}")
    assert run["head_sha"] == head and run["run_attempt"] == 1
    assert run["status"] == "completed" and run["conclusion"] == "success"
    return run

def archive(run, name):
    rows = [a for a in api(f"actions/runs/{run['id']}/artifacts")["artifacts"]
            if a["name"] == name]
    assert len(rows) == 1
    item = rows[0]
    assert not item["expired"]
    assert item["workflow_run"]["id"] == run["id"]
    assert item["workflow_run"]["head_sha"] == run["head_sha"]
    data = subprocess.check_output(["gh", "api", REPO + f"actions/artifacts/{item['id']}/zip"])
    assert item["digest"] == "sha256:" + hashlib.sha256(data).hexdigest()
    z = zipfile.ZipFile(io.BytesIO(data))
    assert len(z.namelist()) == len(set(z.namelist()))
    return z, item

def safe_path(root, name):
    p = Path(name)
    assert not p.is_absolute() and ".." not in p.parts and p.parts
    target = root / p
    assert root.resolve() in target.resolve().parents
    return target

def put(path, data, digest):
    assert hashlib.sha256(data).hexdigest() == digest, str(path)
    assert not path.exists(), str(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)

def current_path(name):
    p = Path(name)
    if not p.is_absolute():
        p = ROOT / p
    p = p.resolve()
    assert ROOT in p.parents, name
    assert p.is_file(), name
    return p

def restore_mapping():
    run = completed(MAP_RUN, MAP_HEAD)
    z, mapped_meta = archive(run, f"core-only-mainchip-mapping-{MAP_RUN}")
    native, native_meta = archive(run, f"core-only-mainchip-source-native-{MAP_RUN}")
    report = json.loads(z.read("mapping.json"))
    assert report["source_head"] == MAP_HEAD
    assert report["status"] == "MAPPED_CORE_ONLY_REQUIRES_MAPPED_BOOT_AND_PHYSICAL_SIGNOFF"
    assert report["macros"] == {MASTER: 4}
    assert not report["accepted"] and not report["pcie_present"] and not report["ethernet_present"]
    assert report["source_binding"]["all_files_unchanged"]
    for name, digest in report["source_binding"]["before"].items():
        assert sha(safe_path(ROOT, name)) == digest, name
    assert native.namelist() == ["build.tgz"]
    relative = Path("hw/soc/out/core-only-mainchip")
    restored = set()
    with tarfile.open(fileobj=io.BytesIO(native.read("build.tgz"))) as tar:
        for member in tar:
            p = Path(member.name)
            assert not p.is_absolute() and ".." not in p.parts
            assert p == relative or relative in p.parents
            if member.isdir():
                continue
            assert member.isfile()
            name = str(p.relative_to(relative))
            assert name in report["outputs"] and name not in restored
            restored.add(name)
            put(ROOT / p, tar.extractfile(member).read(), report["outputs"][name])
    assert restored == set(report["outputs"])
    return report, [mapped_meta, native_meta]

def restore_cts():
    run = completed(CTS_RUN, CTS_HEAD)
    native, metadata = archive(run, f"core-only-placement-native-{CTS_RUN}")
    summary, smeta = archive(run, f"core-only-placement-summary-{CTS_RUN}")
    raw = native.read("result.json")
    assert raw == summary.read("result.json")
    report = json.loads(raw)
    assert report["source_head"] == CTS_HEAD and report["returncode"] == 0
    assert report["status"] == "CTS_COMPLETE_REQUIRES_NEW_BOOT_ROUTING_AND_SIGNOFF"
    assert report["sources_unchanged"] and not report["accepted"]
    assert not report["final_timing_complete"]
    assert report["source_binding"]["run"] == MAP_RUN
    assert report["source_binding"]["head"] == MAP_HEAD
    root = ROOT / "hw/soc/out/core-only-placement"
    restored = set()
    for info in native.infolist():
        if info.is_dir():
            continue
        assert not stat.S_ISLNK(info.external_attr >> 16)
        name = info.filename
        if name == "result.json":
            continue
        assert name in report["outputs"] and name not in restored
        restored.add(name)
        put(safe_path(root, name), native.read(info), report["outputs"][name])
    assert restored == set(report["outputs"])
    root.joinpath("result.json").write_bytes(raw)
    for name, digest in report["protected_inputs"].items():
        assert sha(current_path(name)) == digest, name
    state_path = safe_path(root, report["cts_state"])
    state = json.loads(state_path.read_text())
    assert sha(current_path(state["odb"])) == report["cts_odb_sha256"]
    for key in ("nl", "def", "sdc"):
        if state.get(key):
            current_path(state[key])
    config_path = root / "prepared/config.json"
    config = json.loads(config_path.read_text())
    assert config["CLOCK_PORT"] == ["clk_i"] and config["CLOCK_NET"] == ["clk_i"]
    assert config["CLOCK_PERIOD"] == 20 and config["TIME_DERATING_CONSTRAINT"] == 5.0
    assert set(config["MACROS"]) == {MASTER}
    assert len(config["MACROS"][MASTER]["instances"]) == 4
    return report, [metadata, smeta], config_path, state_path


def fresh_corner_metrics(state_path, corner):
    """Only this STA process's metrics, never state-in's carried-over values."""
    native = state_path.parent / "or_metrics_out.json"
    raw = json.loads(native.read_text())
    suffix = "__corner:" + corner
    selected = {key[:-len(suffix)]: value for key, value in raw.items()
                if key.endswith(suffix)}
    required = ("timing__setup__ws", "timing__hold__ws",
                "timing__setup_vio__count", "timing__hold_vio__count",
                "design__max_slew_violation__count", "design__max_cap_violation__count")
    for key in required:
        value = selected.get(key)
        assert isinstance(value, (int, float)) and not isinstance(value, bool), (corner, key, value)
        assert math.isfinite(value), (corner, key, value)
        if key.endswith("__count"):
            assert value >= 0 and value == int(value), (corner, key, value)
    other = [key for key in raw if "__corner:" in key and not key.endswith(suffix)]
    assert not other, ("Unexpected corner in single-corner process", other)
    return selected, native

def qualify_sources():
    completed(GUARD_RUN, GUARD_HEAD)
    import base64
    for name in ("hw/soc/pnr/core_only_postcts_flow.py",
                 "scripts/qualify_core_only_timing_guards.py"):
        value = api(f"contents/{name}?ref={GUARD_HEAD}")
        data = base64.b64decode(value["content"])
        assert hashlib.sha256(data).hexdigest() == sha(ROOT / name), name

def restore_postcts():
    run = completed(44242709956, "d6e690676c9f1fecaccea89b0ef4fcc6146d2e1b")
    native, metadata = archive(run, "core-only-postcts-native-44242709956")
    assert metadata["id"] == 14401785833
    assert metadata["digest"] == "sha256:32ccd56e3e7091231c0ddb7a60ef033d7cb15ff54bacd44101add577b137d3d2"
    raw = native.read("result.json")
    report = json.loads(raw)
    assert report["status"] == "POSTCTS_REPAIR_COMPLETE_REQUIRES_ROUTING_AND_SIGNOFF"
    assert report["sources_unchanged"] and not report["accepted"]
    assert report["source_binding"]["mapping_run"] == MAP_RUN
    assert report["source_binding"]["cts_run"] == CTS_RUN
    root = ROOT / "hw/soc/out/core-only-postcts"
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
    for corner, entry in report["phases"]["timing"]["corners"].items():
        metrics, path = fresh_corner_metrics(safe_path(root, entry["state"]), entry["corner_name"])
        assert sha(path) == entry["metrics_sha256"] and metrics == entry["metrics"]
        assert metrics["timing__setup_vio__count"] == metrics["timing__hold_vio__count"] == 0
    initial = safe_path(root, report["output_state"])
    state = json.loads(initial.read_text())
    for key in ("odb", "nl", "def", "sdc"):
        if state.get(key):
            path = current_path(state[key])
            assert root in path.parents, (key, path)
            assert sha(path) == report["outputs"][str(path.relative_to(root))]
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
        postcts, postcts_meta, initial = restore_postcts()
        report["source_binding"]["postcts_run"] = 44242709956
        report["source_binding"]["postcts_artifact"] = postcts_meta
        app = Path(os.environ["CLOUD_APPIMAGE"])
        verify(app, "x86_64")
        flow = ROOT / "hw/soc/pnr/core_only_globalroute_flow.py"
        paths = [Path(__file__), flow, ROOT / "hw/soc/pnr/core_only_postcts_flow.py", ROOT / "hw/soc/pnr/interface_flow.py",
                 ROOT / "hw/soc/flow/check_timing_derate.tcl", config,
                 config.parent / "physical.sdc", initial,
                 current_path(json.loads(initial.read_text())["odb"])]
        protected = {str(p): sha(p) for p in paths}
        report["protected_inputs"] = protected
        save()
        for phase, flow_name, after in [
                ("globalroute", "CoreOnlyGlobalRoute", "routed")]:
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
        report.update(status="GLOBAL_ROUTE_COMPLETE_REQUIRES_DETAILED_ROUTE_AND_SIGNOFF",
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

