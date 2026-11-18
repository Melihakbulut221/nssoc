#!/usr/bin/env python3
"""Nominal extraction and actual-SPEF STA from authenticated detailed routing."""
from collections import deque
import json
import os
from pathlib import Path
import stat
import re
import subprocess
from bootstrap_flow import verify
from check_antenna_netlist_export import check_added_antennas
from cloud_core_only_postgrt import (ROOT, sha, completed, archive, safe_path, put,
    current_path, restore_mapping, restore_cts, qualify_sources)
from cloud_core_only_clock_probe import restore_cts8
from cloud_core_only_clock_refine import restore_clock_split, restore_previous
from cloud_core_only_detailed_route import restore_refinement
OUT = ROOT / "hw/soc/out/core-only-antenna-extraction"
RUN = 44383558280
HEAD = "b42104b780290a762ecf705e0741af846db8d43b"
CORNERS = ["nom_slow_1p08V_125C", "nom_typ_1p20V_25C", "nom_fast_1p32V_m40C"]


def restore_stage(run_id,head,artifact_name,artifact_id,digest,relative):
    run=completed(run_id,head);z,m=archive(run,artifact_name)
    assert m['id']==artifact_id and m['digest']==digest
    raw=z.read('result.json');r=json.loads(raw)
    assert r['source_head']==head and r['sources_unchanged'] and not r['accepted']
    root=ROOT/relative;seen=set()
    for item in z.infolist():
        if item.is_dir()or item.filename=='result.json':continue
        assert not stat.S_ISLNK(item.external_attr>>16)
        n=item.filename;assert n in r['outputs']and n not in seen
        put(safe_path(root,n),z.read(item),r['outputs'][n]);seen.add(n)
    assert seen==set(r['outputs']);(root/'result.json').write_bytes(raw)
    for p,h in r['protected_inputs'].items():assert sha(current_path(p))==h,p
    return r,m,root


def restore_route():
    # Only accept this specific routed candidate after external artifact admission.
    artifact_id=int(os.environ['NSSOC_ROUTE_ARTIFACT_ID'])
    digest=os.environ['NSSOC_ROUTE_ARTIFACT_DIGEST']
    assert artifact_id>0 and re.fullmatch(r'sha256:[0-9a-f]{64}',digest)
    eco,em,eroot=restore_stage(44327965276,'0fbac4d6617c72f3d00a0b759cfc4677bae1b732',
        'core-only-pin-aware-electrical-eco-44327965276',14438605718,
        'sha256:36fcd030bd23666169d392b84668f5bf0cd727d1b4b5f351d75c8a20fd876bb1',
        'hw/soc/out/core-only-pin-aware-electrical-eco')
    assert eco['audit']['new_buffers']==6 and eco['audit']['resized_cells']==4
    grt,gm,groot=restore_stage(44328874040,'733cb000518b8bd6d95470fde5e6e3c3e32bafa6',
        'core-only-pin-aware-electrical-globalroute-44328874040',14438862280,
        'sha256:e47da3fe91a279ad2102ee2d84420b226afddd73646b26dceb5ab42c37e05fa8',
        'hw/soc/out/core-only-pin-aware-electrical-globalroute')
    completed(44385801058,'f35a79dec5bb998eb88de851d6be0c0808075cee')
    run=completed(RUN,HEAD);z,meta=archive(run,f'core-only-antenna-reroute-{RUN}')
    assert meta['id']==artifact_id and meta['digest']==digest
    raw=z.read('result.json');report=json.loads(raw)
    assert report['source_head']==HEAD and report['sources_unchanged']and not report['accepted']
    assert report['status']=='ROUTING_ANTENNA_AND_VISIBLE_GEOMETRY_CHECKED_REQUIRES_FRESH_RC_TIMING_AND_SIGNOFF'and report['returncode']==0
    binding=report['source_admission'];assert binding['run']==44382891924 and binding['head']=='508bb46d0366363d7e79a001ab8a68b230f4fd96'and binding['artifact']==14464567635 and binding['digest']=='d5864cb7b9575155444b2ca063010f889c9203ab7bf1a8867b86dba19254c4b3'
    assert binding['insertion_audit']['new_diodes']==800 and binding['insertion_audit']['total_instances']==106051
    root=ROOT/'hw/soc/out/core-only-antenna-reroute';seen=set()
    for item in z.infolist():
        if item.is_dir()or item.filename=='result.json':continue
        assert not stat.S_ISLNK(item.external_attr>>16)
        n=item.filename;assert n in report['outputs']and n not in seen
        put(safe_path(root,n),z.read(item),report['outputs'][n]);seen.add(n)
    assert seen==set(report['outputs']);(root/'result.json').write_bytes(raw)
    metrics=json.loads((root/'metrics.json').read_text());assert metrics==report['metrics']
    for key in ['route__drc_errors','antenna__violating__nets','antenna__violating__pins']:assert metrics[key]==0
    identity=json.loads((root/'identity/route-identity.json').read_text());assert identity==report['route_identity']
    assert identity['instances']==106051 and identity['sources_unchanged']
    prun=completed(44383998997,'0afa898e2a05fdc00e2a4f38bb620faebd2d0046')
    pz,pm=archive(prun,'core-only-antenna-power-contact-44383998997')
    assert pm['id']==14465730398 and pm['digest']=='sha256:6610d7e0094ba9359005f4c14ad0593b7611898ffa88fff27055e9c702fbde18'
    power_summary=json.loads(pz.read('result.json'));assert power_summary['sources_unchanged']and power_summary['status']=='ADDED_DIODE_LOCAL_POWER_CONTACT_VERIFIED_NOT_FULL_PDN_SIGNOFF'
    import hashlib
    for n,h in power_summary['outputs'].items():assert hashlib.sha256(pz.read(n)).hexdigest()==h
    power=json.loads(pz.read('power-contact.json'));assert power['checked_power_terminals']==1600 and not power['failures']and power['sources_unchanged']
    assert power['source_odb_sha256']=='2147b6df67feac28691ca76defdd7d3cafd4df1c00a74c0043fcd55f47767750'and power['source_odb_sha256']in identity['source_hashes'].values()
    report['added_diode_power_contact']=dict(artifact=pm,checked_terminals=1600,scope=power['scope'])
    for key in ['exact_instance_geometry_status_and_masters','exact_terminal_connections','exact_net_names_and_signal_types','exact_special_wires_ports_and_die']:assert identity[key]
    geometry=json.loads((root/'geometry/physical-route-audit.json').read_text());assert geometry==report['visible_geometry']
    assert geometry['source_unchanged']and geometry['actual_route_removal_control']
    assert not geometry['signal_nets_with_disconnected_geometry']and not geometry['unwired_multi_terminal_nets']and not geometry['terminals_without_geometry']and geometry['inter_net_contact_pairs']==0
    odb=root/'soc_top.odb';assert sha(odb)==report['routed_odb_sha256']==geometry['source_odb_sha256']
    # Original GRT state supplies the unchanged constraints. Export fresh views
    # from the newly routed ODB; never use the pre-diode netlist for STA.
    original_state=json.loads(safe_path(groot,grt['output_state']).read_text())
    original_sdc=current_path(original_state['sdc']);sdc_hash=sha(original_sdc)
    export=OUT/'routed-export.tcl';export.write_text('read_db {'+str(odb)+'}\nwrite_def {'+str(OUT/'routed.def')+'}\nwrite_verilog {'+str(OUT/'routed.v')+'}\nputs NSSOC_ROUTED_VIEWS_WRITTEN\n')
    app=Path(os.environ['CLOUD_APPIMAGE']);verify(app,'x86_64')
    with (OUT/'routed-export.log').open('w')as log:subprocess.run([str(app),'openroad','-exit',str(export)],stdout=log,stderr=subprocess.STDOUT,check=True)
    assert 'NSSOC_ROUTED_VIEWS_WRITTEN'in (OUT/'routed-export.log').read_text()
    export_check=check_added_antennas((OUT/'routed.v').read_text(),binding['insertion_audit']['new_cells'])
    assert export_check['new_diodes_exported']==800 and not export_check['missing_diodes']and not export_check['duplicate_diodes']and not export_check['signal_connection_mismatches']
    report['antenna_netlist_export']=export_check
    assert sha(original_sdc)==sdc_hash and sha(odb)==report['routed_odb_sha256']
    state=dict(original_state);state.update(odb=str(odb),nl=str(OUT/'routed.v'),sdc=str(original_sdc));state['def']=str(OUT/'routed.def')
    for key in ['spef','sdf','lib','pnl']:
        if key in state:state[key]=None
    state['metrics']={};initial=OUT/'routed-initial-state.json';initial.write_text(json.dumps(state,indent=2)+'\n')
    report['baseline_estimated_corners']=grt['corners']
    report['fresh_view_binding']=dict(odb_sha256=sha(odb),netlist_sha256=sha(OUT/'routed.v'),def_sha256=sha(OUT/'routed.def'),sdc_sha256=sdc_hash,export_script_sha256=sha(export))
    return report,[em,gm,meta,pm],initial


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
        report["pre_route_corners"] = routed["baseline_estimated_corners"]
        report["fresh_view_binding"] = routed["fresh_view_binding"]
        report["antenna_netlist_export"] = routed["antenna_netlist_export"]
        report["added_diode_power_contact"] = routed["added_diode_power_contact"]
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
        name_guard=ROOT/'scripts/audit_core_only_extraction_names.py'
        name_report=OUT/'extraction-name-admission.json'
        original_odb=current_path(json.loads(initial.read_text())['odb'])
        env=dict(os.environ,NSSOC_EXTRACTION_NAME_ODB=str(original_odb),NSSOC_EXTRACTION_NAME_REPORT=str(name_report),NSSOC_EXTRACTION_EXPECTED_INSTANCES='106051')
        with (OUT/'extraction-name-admission.log').open('w')as log:
            subprocess.run([str(app),'openroad','-exit','-python',str(name_guard)],env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
        report['name_admission']=json.loads(name_report.read_text())
        assert report['name_admission']['source_unchanged']and not report['name_admission']['invalid_instances']and not report['name_admission']['invalid_internal_nets']
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
        paths.extend([ROOT/"scripts/check_antenna_netlist_export.py",name_guard,name_report,OUT/"routed.v",OUT/"routed.def",OUT/"routed-export.tcl",current_path(json.loads(initial.read_text())["sdc"])])
        protected = {str(p):sha(p) for p in paths}
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
