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
OUT = ROOT / "hw/soc/out/cloud-predecode-postcts"
SOURCE = ROOT / "hw/soc/out/cloud-predecode-chip-placement"
REPO = "repos/Melihakbulut221/nssoc/"
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


def restore(args, result):
    import zipfile, stat
    run = api('actions/runs/43622573415')
    assert run['status']=='completed' and run['conclusion']=='success'
    assert run['head_sha']=='a3a79275ea42940b3c319c7c15cab2ae75f15109'
    def archive(aid, digest, name):
        meta=api('actions/artifacts/'+str(aid))
        assert meta['workflow_run']['id']==43622573415 and meta['workflow_run']['head_sha']==run['head_sha']
        assert meta['digest']=='sha256:'+digest and not meta['expired']
        path=OUT/name
        with path.open('xb') as f:
            subprocess.run(['gh','api',REPO+'actions/artifacts/'+str(aid)+'/zip'],stdout=f,check=True)
        assert sha(path)==digest
        return zipfile.ZipFile(path)
    safe=archive(14125635095,'27634a4fc273d1dfa52c6bb72cbfde2b50e8f7c3bf15fb5ff73cf31dbad72ace','safe.zip')
    native=archive(14124619734,'244a660873d74ae73e2913c1cd96546817d6a3e0474045a662ea566246adaac5','native.zip')
    report=json.loads(safe.read('result.json'))
    assert report['source_head']==run['head_sha'] and report['sources_unchanged'] and report['returncode']==0
    assert report['accepted'] is False and report['functional_boot_accepted'] is False
    assert report['cts_odb_sha256']=='fc4400278ce81212ca7b30bf2d02aa7356f23e512336020e201e98839cd9beab'
    assert len(report['preparation']['macros'])==20
    names=native.namelist();assert len(names)==len(set(names))
    assert {n for n in names if not n.endswith('/')}==set(report['outputs'])|{'result.json'}
    assert not SOURCE.exists();SOURCE.mkdir(parents=True)
    for info in native.infolist():
        name=relative(info.filename)
        assert not stat.S_ISLNK(info.external_attr >> 16)
        if info.is_dir():continue
        raw=native.read(info)
        expected=hashlib.sha256(safe.read('result.json')).hexdigest() if info.filename=='result.json' else report['outputs'][info.filename]
        assert hashlib.sha256(raw).hexdigest()==expected,info.filename
        dest=SOURCE/name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(raw)
    result['placement_source']=dict(run=43622573415,head=run['head_sha'],native_artifact=14124619734,
        native_sha256='244a660873d74ae73e2913c1cd96546817d6a3e0474045a662ea566246adaac5',
        authenticated_files=len(report['outputs']),functional_boot_accepted=False)
    return report


def main():
    args = None
    assert os.environ.get('GITHUB_ACTIONS') == 'true'
    OUT.mkdir(parents=True, exist_ok=False)
    result = dict(status="RUNNING", source_head=os.environ["GITHUB_SHA"], accepted=False, functional_boot_accepted=False,
                  final_timing_complete=False, full_phy_accepted=False, qualified_pex=False,
                  scope="NEW predecode candidate; boot validation remains independent and pending. "
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
        result.update(status="COMPLETE_PREDECODE_POSTCTS_REQUIRES_BOOT_EQUIVALENCE_ROUTING_EXTRACTED_STA",
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
