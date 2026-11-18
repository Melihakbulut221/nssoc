#!/usr/bin/env python3
"""Nominal extraction and actual-SPEF STA from authenticated detailed routing."""
from collections import deque
import json
import os
from pathlib import Path
import stat
import subprocess
from bootstrap_flow import verify
from cloud_core_only_postgrt import (ROOT, sha, completed, archive, safe_path, put,
    current_path, restore_mapping, restore_cts, qualify_sources)
from cloud_core_only_clock_probe import restore_cts8
from cloud_core_only_clock_refine import restore_clock_split, restore_previous
from cloud_core_only_detailed_route import restore_refinement
OUT = ROOT / "hw/soc/out/core-only-canonical-extracted-timing"
RUN = 44263061910
HEAD = "921f49a0c7becd72e58177e19404b45e91575e63"
CORNERS = ["nom_slow_1p08V_125C", "nom_typ_1p20V_25C", "nom_fast_1p32V_m40C"]


def restore_route():
    run = completed(RUN, HEAD)
    native, metadata = archive(run, f"core-only-detailed-route-native-{RUN}")
    summary, smeta = archive(run, f"core-only-detailed-route-summary-{RUN}")
    assert metadata["id"] == 14427036835
    assert metadata["digest"] == "sha256:2d59e124653acb0529d73435857e701463d8db29e9bd9520ed38b9054d693b7b"
    assert smeta["id"] == 14426887166
    assert smeta["digest"] == "sha256:6c7f4c49e439ac50958033f84fb23c14fda86a41d05bc3142ebb10670b8be6d8"
    raw = native.read("result.json")
    assert raw == summary.read("result.json")
    report = json.loads(raw)
    assert report["source_head"] == HEAD
    assert report["status"] == "DETAILED_ROUTE_EXECUTED_REQUIRES_CONNECTIVITY_RC_AND_SIGNOFF_AUDIT"
    assert report["sources_unchanged"] and not report["accepted"]
    assert report["returncode"] == 0
    assert report["source_binding"]["refinement_run"] == 44259265143
    root = ROOT / "hw/soc/out/core-only-detailed-route"
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
    recorded = report["routing_metrics"]
    native_metrics = safe_path(root, recorded["path"])
    assert sha(native_metrics) == recorded["sha256"]
    assert json.loads(native_metrics.read_text()) == recorded["values"]
    initial = safe_path(root, report["routed_state"])
    state = json.loads(initial.read_text())
    for key in ("odb", "nl", "def", "sdc"):
        p = current_path(state[key])
        assert root in p.parents
        assert sha(p) == report["outputs"][str(p.relative_to(root))]
    return report, [metadata, smeta], initial


def main():
    assert os.environ.get("GITHUB_ACTIONS") == "true"
    OUT.mkdir(parents=True, exist_ok=False)
    report = dict(source_head=os.environ["GITHUB_SHA"], status="PREPARING", accepted=False,
        final_timing_complete=False, qualified_rc_minmax=False, annotation_qualified=False,
        manufacturing_approval=False)
    def save():
        (OUT/"result.json").write_text(json.dumps(report, indent=2)+"\n")
    try:
        qualify_sources()
        mapping, mapping_artifacts = restore_mapping()
        cts, cts_artifacts, config, initial = restore_cts()
        assert cts["source_binding"]["netlist_sha256"] == mapping["outputs"]["synthesis/soc_top.netlist.v"]
        cts8, cts8meta, config, initial = restore_cts8(config)
        split, splitmeta, initial = restore_clock_split()
        previous, previousmeta, initial = restore_previous()
        refined, refinedmeta, initial = restore_refinement()
        routed, routedmeta, initial = restore_route()
        report["source_binding"] = dict(route_run=RUN, route_head=HEAD,
            artifacts=mapping_artifacts+cts_artifacts+[cts8meta,splitmeta,previousmeta]+refinedmeta+routedmeta)
        report["pre_route_corners"] = refined["phases"]["timing"]["corners"]
        original_config = config
        data = json.loads(config.read_text())
        assert data["CLOCK_PERIOD"] == 20 and data["TIME_DERATING_CONSTRAINT"] == 5.0
        assert data["CLOCK_PORT"] == ["clk_i"]
        data.update(STA_THREADS=1, STA_CORNERS=CORNERS)
        config = OUT/"extraction-config.json"
        config.write_text(json.dumps(data,indent=2)+"\n")
        expected = json.loads(original_config.read_text())
        expected.update(STA_THREADS=1, STA_CORNERS=CORNERS)
        assert data == expected
        app = Path(os.environ["CLOUD_APPIMAGE"]);verify(app,"x86_64")
        original_initial=initial
        original_state=json.loads(initial.read_text())
        original_odb=current_path(original_state['odb'])
        original_sdc=current_path(original_state['sdc'])
        manifest=OUT/'canonical-input.json';manifest.write_text(json.dumps(dict(odb=str(original_odb),sdc=str(original_sdc)),indent=2)+'\n')
        canonical_script=ROOT/'scripts/canonicalize_core_only_timing_names.py'
        canonical_protected={str(p):sha(p)for p in [original_initial,original_odb,original_sdc,manifest,canonical_script]}
        with (OUT/'canonical.log').open('w')as log:
            subprocess.run([str(app),'openroad','-exit','-python',str(canonical_script)],env=dict(os.environ,NSSOC_CANONICAL_OUT=str(OUT)),stdout=log,stderr=subprocess.STDOUT,check=True)
        report['canonicalization']=json.loads((OUT/'canonical-proof.json').read_text())
        assert report['canonicalization']['binary_readback_verified']
        export=OUT/'canonical-export.tcl'
        export.write_text('read_db {'+str(OUT/'canonical.odb')+'}\nwrite_def {'+str(OUT/'canonical.def')+'}\nwrite_verilog {'+str(OUT/'canonical.v')+'}\nputs NSSOC_CANONICAL_VIEWS_WRITTEN\n')
        with (OUT/'canonical-export.log').open('w')as log:subprocess.run([str(app),'openroad','-exit',str(export)],stdout=log,stderr=subprocess.STDOUT,check=True)
        assert 'NSSOC_CANONICAL_VIEWS_WRITTEN'in(OUT/'canonical-export.log').read_text()
        initial=OUT/'canonical-state.json'
        state=dict(original_state);state.update(odb=str(OUT/'canonical.odb'),nl=str(OUT/'canonical.v'),def_=str(OUT/'canonical.def'))
        state['def']=state.pop('def_')
        for key in ['spef','sdf','lib','pnl']:
            if key in state:state[key]=None
        if 'metrics'in state:state['metrics']={}
        initial.write_text(json.dumps(state,indent=2)+'\n')
        assert all(sha(p)==h for p,h in canonical_protected.items())

        flow = ROOT/"hw/soc/pnr/core_only_routed_extraction_flow.py"
        paths = [Path(__file__), flow, original_config, config, initial,
            current_path(json.loads(initial.read_text())["odb"])]
        for name in ["scripts/cloud_core_only_detailed_route.py", "scripts/cloud_core_only_clock_refine.py",
            "scripts/cloud_core_only_postcts.py", "scripts/cloud_core_only_clock_probe.py",
            "scripts/cloud_core_only_postgrt.py", "hw/soc/pnr/core_only_routed_guards.py",
            "hw/soc/pnr/replay_onehot_routed_extraction_flow.py", "hw/soc/pnr/interface_flow.py",
            "hw/soc/flow/audit_estimated_spef.py", "hw/soc/flow/check_timing_derate.tcl",
            "scripts/audit_core_only_route_annotation.py"]:
            paths.append(ROOT/name)
        protected = {str(p):sha(p) for p in paths}
        protected.update(canonical_protected)
        for p in [OUT/"canonical.odb",OUT/"canonical.def",OUT/"canonical.v",OUT/"canonical-name-map.json",OUT/"canonical-proof.json",export]:protected[str(p)]=sha(p)
        report["protected_inputs"] = protected
        directory = OUT/"extraction";directory.mkdir(parents=True,exist_ok=False)
        command=[str(app),"python",str(flow),"--flow","CoreOnlyRoutedExtraction",
            "--pdk-root",str(ROOT/"hw/soc/tools/ciel-corrpre"),"--pdk","ihp-sg13g2",
            "--scl","sg13g2_stdcell","--force-run-dir",str(directory),
            "--with-initial-state",str(initial),str(config)]
        report.update(status="EXTRACTING_AND_ANALYZING",command=command);save()
        with (OUT/"extraction.log").open("w") as log:
            code=subprocess.call(command,stdout=log,stderr=subprocess.STDOUT)
        report["returncode"]=code
        if code:
            with (OUT/"extraction.log").open() as log:print("".join(deque(log,maxlen=60)),flush=True)
            raise RuntimeError("Native extraction/STA failed")
        proofs=list(directory.glob("*-nssoc-coreonlyroutercx/native-spef-integrity.json"))
        assert len(proofs)==1
        proof=json.loads(proofs[0].read_text());assert proof["nominal_only"] and not proof["qualified_rc_minmax"]
        for entry in proof["spefs"].values():
            p=current_path(entry["path"]);assert directory in p.parents and sha(p)==entry["sha256"]
            assert entry["audit"]["status"].startswith("PASS")
        report["nominal_spef_proof"]=proof
        states=list(directory.glob("*-nssoc-coreonlyextractedsta/state_out.json"));assert len(states)==1
        report["fresh_corners"]={}
        for corner in CORNERS:
            folder=states[0].parent/corner;metrics=folder/"fresh_metrics.json";log=folder/"sta.log"
            assert metrics.is_file() and log.is_file()
            text=log.read_text();assert "CORE_ONLY_EXTRACTED_CLOCK_VERIFIED" in text
            assert "EST-0026" not in text
            report["fresh_corners"][corner]=dict(metrics_source=str(metrics.relative_to(OUT)),
                metrics_sha256=sha(metrics),metrics=json.loads(metrics.read_text()),
                sta_log=str(log.relative_to(OUT)),sta_log_sha256=sha(log))
        # Classify every unannotated driver using this run's native evidence.
        # Successful classification is not coverage acceptance, even with zero loads.
        audit_script = ROOT/"scripts/audit_core_only_route_annotation.py"
        spef_entries = list(proof["spefs"].values())
        assert len(spef_entries) == 1
        spef_path = current_path(spef_entries[0]["path"])
        routed_odb = current_path(json.loads(initial.read_text())["odb"])
        report["annotation_classification"] = {}
        for corner in CORNERS:
            log_path = OUT/report["fresh_corners"][corner]["sta_log"]
            output = OUT/("annotation-"+corner+".json")
            inputs = {key:dict(path=str(path),sha256=sha(path)) for key,path in
                [("odb",routed_odb),("spef",spef_path),("sta_log",log_path)]}
            inputs["output"] = str(output)
            manifest = OUT/("annotation-inputs-"+corner+".json")
            manifest.write_text(json.dumps(inputs,indent=2)+"\n")
            env = dict(os.environ,NSSOC_CORE_ANNOTATION_INPUTS=str(manifest))
            with (OUT/("annotation-"+corner+".log")).open("w") as log:
                subprocess.run([str(app),"openroad","-exit","-python",str(audit_script)],
                    env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
            classification=json.loads(output.read_text())
            assert classification["inputs_unchanged"] and not classification["accepted"]
            report["annotation_classification"][corner] = {
                k:v for k,v in classification.items() if k!="drivers"}
        assert all(sha(p)==h for p,h in protected.items())
        report.update(status="NOMINAL_RC_AND_NATIVE_SPEF_STA_EXECUTED_REQUIRES_COVERAGE_AND_SIGNOFF",
            sources_unchanged=True, output_state=str(states[0].relative_to(OUT)))
    except BaseException as error:
        report.update(status="FAIL_OR_INCOMPLETE",error=repr(error));raise
    finally:
        report["outputs"]={str(p.relative_to(OUT)):sha(p) for p in OUT.rglob("*")
            if p.is_file() and p!=OUT/"result.json"}
        save()
if __name__=="__main__":main()
