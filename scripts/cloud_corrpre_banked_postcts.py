#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Continue NEW banked CTS only; never inherit an old candidate's timing proof."""
import argparse
import hashlib
import json
import math
import os
import re
import shutil
import subprocess
import tarfile
import time
from pathlib import Path
from bootstrap_flow import verify
from cloud_chunked_results import verify_parts
from run_cloud_tx_layout_repair import fetch

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "hw/soc/out/cloud-corrpre-banked-postcts"
SOURCE = ROOT / "hw/soc/out/cloud-corrpre-mbist-placement"
REPO = "repos/Melihakbulut221/nssoc/"
BOOT_RUN = 39016026619
BOOT_HEAD = "f65c0c35a6e2c706f0fe7df485ab6b2115b11e6a"
PROTOCOL_RUN = 39015043900
PLACEMENT_STATUS = "COMPLETE_NATIVE_CORRPRE_MBIST_CTS_REQUIRES_ROUTING_AND_ALL_SIGNOFF_GATES"
CORNERS = [("slow", "nom_slow_1p08V_125C"), ("typical", "nom_typ_1p20V_25C"),
           ("fast", "nom_fast_1p32V_m40C")]


def sha(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def api(path):
    return json.loads(subprocess.check_output(["gh", "api", REPO + path]))


def relative(name):
    path = Path(name)
    assert not path.is_absolute() and name and ".." not in path.parts
    return path


def require_candidate(report, head):
    assert report["status"] == PLACEMENT_STATUS and report["sources_unchanged"] is True
    assert report["returncode"] == 0 and report["source_head"] == head
    boot = report["boot_source"]
    spec = boot["source_spec"]
    assert spec["run"] == boot["source_run"] == BOOT_RUN
    assert spec["head"] == boot["source_head_original"] == BOOT_HEAD
    assert spec["protocol_run"] == PROTOCOL_RUN
    assert spec["bank_proof_and_protocol_verified"] is True
    assert spec["artifact"] == boot["source_artifact"]
    assert spec["zip_sha256"] == boot["original_zip_sha256"]
    assert boot["gate_result"]["passed"] and boot["gate_result"]["sources_unchanged"]
    config = boot["configuration"]
    assert config["RF_CORRPRE"] == config["SOC_SRAM_MBIST"] == config["SOC_ETH_MBIST"] == 1
    assert config["RF_SYNPRE"] == config["CORE_REQ_REG"] == config["CORE_WB_STAGE"] == 0
    assert config["SOC_PCIE_PROFILE"] == "packet-async" and config["interface_profile"] == "full"
    assert len(report["preparation"]["macros"]) == 20
    state = relative(report["cts_state"])
    assert state.name == "state_out.json" and state.parent.name.endswith("-openroad-cts")
    assert str(state) in report["outputs"]
    return spec


def restore(args, result):
    run = api("actions/runs/" + str(args.placement_run))
    assert run["status"] == "completed" and run["conclusion"] == "success"
    assert run["path"] == ".github/workflows/corrpre-banked-placement-cloud.yml"
    assert run["event"] == "workflow_dispatch"
    group = "corrpre-banked-placement"
    stem = f"{group}-{args.placement_run}-{run['run_attempt']}"
    base = ("https://github.com/Melihakbulut221/nssoc/releases/download/"
            f"cloud-results-{args.placement_run}-{run['run_attempt']}-{group}/")
    summary = OUT / "placement.summary.json"
    manifest = OUT / "placement.parts.json"
    fetch(base + stem + ".summary.json", args.summary_sha256, summary)
    fetch(base + stem + ".parts.json", args.parts_sha256, manifest)
    report = json.loads(summary.read_text())
    spec = require_candidate(report, run["head_sha"])
    # Re-execute actual six-proof/protocol/boot source binding. A copied boolean
    # in the placement receipt cannot substitute for the original evidence.
    checked = OUT / "verified-boot-source.json"
    subprocess.run([os.sys.executable, str(ROOT / "scripts/check_pcie_banked_boot_source.py"),
                    "--boot-run", str(spec["run"]), "--boot-head", spec["head"],
                    "--artifact", str(spec["artifact"]), "--zip-sha256", spec["zip_sha256"],
                    "--protocol-run", str(spec["protocol_run"]), "--out", str(checked)], check=True)
    assert json.loads(checked.read_text()) == spec
    parts = json.loads(manifest.read_text())
    assert parts["stem"] == stem and parts["source_directory"] == SOURCE.name
    download = OUT / "download"
    download.mkdir()
    for index, row in enumerate(parts["parts"]):
        assert row["index"] == index and row["name"] == stem + ".tar.gz.part" + str(index).zfill(4)
        fetch(base + row["name"], row["sha256"], download / row["name"])
    result["archive_verification"] = verify_parts(parts, download)
    packed = download / "source.tar.gz"
    with packed.open("xb") as target:
        for row in parts["parts"]:
            with (download / row["name"]).open("rb") as stream:
                shutil.copyfileobj(stream, target)
            (download / row["name"]).unlink()
    assert sha(packed) == parts["sha256"] and not SOURCE.exists()
    with tarfile.open(packed) as archive:
        members = archive.getmembers()
        assert len({m.name for m in members}) == len(members)
        for member in members:
            path = relative(member.name)
            assert path.parts[0] == SOURCE.name and (member.isdir() or member.isfile())
        expected = {SOURCE.name + "/" + str(relative(p)) for p in report["outputs"]}
        expected.add(SOURCE.name + "/result.json")
        assert {m.name for m in members if m.isfile()} == expected
        archive.extractall(SOURCE.parent, filter="data")
    packed.unlink()
    assert sha(SOURCE / "result.json") == args.summary_sha256
    for path, digest in report["outputs"].items():
        assert sha(SOURCE / relative(path)) == digest
    result["placement_source"] = dict(run=args.placement_run, head=run["head_sha"],
        summary_sha256=args.summary_sha256, parts_sha256=args.parts_sha256,
        archive_sha256=parts["sha256"], boot_spec=spec)
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--placement-run", required=True, type=int)
    parser.add_argument("--summary-sha256", required=True)
    parser.add_argument("--parts-sha256", required=True)
    args = parser.parse_args()
    assert os.environ.get("GITHUB_ACTIONS") == "true"
    assert args.placement_run > 0
    for digest in (args.summary_sha256, args.parts_sha256):
        assert re.fullmatch("[0-9a-f]{64}", digest)
    OUT.mkdir(parents=True, exist_ok=False)
    result = dict(status="RUNNING", source_head=os.environ["GITHUB_SHA"], accepted=False,
                  final_timing_complete=False, full_phy_accepted=False, qualified_pex=False,
                  scope="NEW banked PCIe/CORRPRE/system and both Ethernet MBIST candidate. "
                        "Exact CTS DB, three separate propagated-clock placement-estimate "
                        "STA processes before/after native electrical/setup/hold repair. "
                        "Not routed, extracted timing, logic equivalence or full PHY acceptance.")
    def save():
        (OUT / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    save()
    try:
        source = restore(args, result)
        state_path = SOURCE / relative(source["cts_state"])
        state = json.loads(state_path.read_text())
        odb = Path(state["odb"])
        assert odb.is_relative_to(SOURCE) and sha(odb) == source["cts_odb_sha256"]
        assert str(odb.relative_to(SOURCE)) in source["outputs"]
        result["discarded_inherited_metric_count"] = len(state["metrics"])
        state["metrics"] = {}
        initial = OUT / "initial-state.json"
        initial.write_text(json.dumps(state, indent=2) + "\n")
        config_path = SOURCE / "prepared/config.json"
        config = json.loads(config_path.read_text())
        assert config["CLOCK_PORT"] == ["clk_i", "pcie_clk_i", "eth_rx_clk_i", "eth_tx_clk_i"]
        assert config["CLOCK_PERIOD"] == 20 and config["TIME_DERATING_CONSTRAINT"] == 5.0
        assert config["SETUP_VIOLATION_CORNERS"] == config["HOLD_VIOLATION_CORNERS"] == ["*"]
        assert config["PNR_SDC_FILE"] == config["SIGNOFF_SDC_FILE"] == str(SOURCE / "prepared/physical.sdc")
        overrides = dict(DESIGN_REPAIR_REMOVE_BUFFERS=False, DESIGN_REPAIR_BUFFER_INPUT_PORTS=False,
                         DESIGN_REPAIR_BUFFER_OUTPUT_PORTS=False, DESIGN_REPAIR_TIE_FANOUT=False)
        config.update(overrides)
        config["TIME_DERATING_CONSTRAINT"] = 5.0
        trial = OUT / "trial-config.json"
        trial.write_text(json.dumps(config, indent=2) + "\n")
        app = Path(os.environ["CLOUD_APPIMAGE"])
        verify(app, "x86_64")
        flow = ROOT / "hw/soc/pnr/corrpre_banked_flow.py"
        protected = {str(p): sha(p) for p in [Path(__file__), flow,
            ROOT / "hw/soc/pnr/interface_flow.py", ROOT / "hw/soc/pnr/corrpre_postcts_flow.py",
            ROOT / "hw/soc/flow/check_timing_derate.tcl", config_path,
            SOURCE / "prepared/physical.sdc", odb, trial, initial]}
        command = [str(app), "python", str(flow), "--flow", "CorrpreBankedPostCTS",
                   "--pdk-root", str(ROOT / "hw/soc/tools/ciel-corrpre"), "--pdk", "ihp-sg13g2",
                   "--scl", "sg13g2_stdcell", "--force-run-dir", str(OUT / "run"),
                   "--with-initial-state", str(initial), str(trial)]
        result.update(status="RUNNING_NATIVE_BANKED_POSTCTS", protected_inputs=protected,
                      config_changes=overrides, command=command)
        save()
        (OUT / "run").mkdir()
        start = time.monotonic()
        with (OUT / "native.log").open("w") as log:
            code = subprocess.call(command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
        result.update(returncode=code, elapsed_s=time.monotonic() - start)
        save()
        if code:
            print((OUT / "native.log").read_text(errors="replace")[-20000:], flush=True)
        assert code == 0, "Native repair failed; all completed states and diagnostics retained"
        assert all(sha(p) == digest for p, digest in protected.items())
        measurements = {}
        for phase in ("before", "after"):
            measurements[phase] = {}
            for short, corner in CORNERS:
                dirs = list((OUT / "run").glob("*-nssoc-corrprebanked" + phase + short))
                assert len(dirs) == 1
                folder = dirs[0]
                assert not (folder / "unpropagated.rpt").read_text().strip()
                cfg = json.loads((folder / "config.json").read_text())
                assert "c4b8b4e5e7a05f375cca3815d51b3a37721fbf5c" in cfg["PDK_ROOT"]
                data = json.loads((folder / "state_out.json").read_text())
                metrics = {k: v for k, v in data["metrics"].items() if k.endswith("__corner:" + corner)}
                for key in ("timing__setup__ws", "timing__hold__ws",
                            "timing__setup_vio__count", "timing__hold_vio__count"):
                    assert math.isfinite(float(metrics[key + "__corner:" + corner]))
                for report in ("max.rpt", "min.rpt", "checks.rpt", "violator_list.rpt",
                               "high-fanout.rpt", "clock.rpt", "ws.max.rpt", "ws.min.rpt"):
                    assert (folder / report).is_file()
                measurements[phase][corner] = dict(metrics=metrics, directory=str(folder.relative_to(OUT)))
        states = list((OUT / "run").glob("*-openroad-resizertimingpostcts/state_out.json"))
        assert len(states) == 1
        repaired = json.loads(states[0].read_text())
        result.update(status="COMPLETE_NATIVE_BANKED_POSTCTS_REQUIRES_EQUIVALENCE_ROUTING_EXTRACTED_STA",
                      measurements=measurements, repaired_state=str(states[0].relative_to(OUT)),
                      repaired_odb_sha256=sha(repaired["odb"]), sources_unchanged=True)
    except BaseException as error:
        result.update(status="FAIL_OR_ERROR", error=repr(error))
        raise
    finally:
        result["outputs"] = {str(p.relative_to(OUT)): sha(p) for p in OUT.rglob("*")
                             if p.is_file() and p != OUT / "result.json"}
        save()


if __name__ == "__main__":
    main()
