#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Wait for exact native producer evidence, then compose every actual TX wire."""
import hashlib,json,os,subprocess,sys,time
from pathlib import Path
import compare_cloud_routed_endpoints as reports
import compose_tx_raw64_native as compose
import cloud_tx_raw64_intrinsic as intrinsic
from run_cloud_tx_layout_repair import sha
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'hw/soc/out/cloud-tx-raw64-composition'
REPO='repos/Melihakbulut221/nssoc/'
def api(path):return json.loads(subprocess.check_output(['gh','api',REPO+path]))
def prerequisite():
    spec=json.loads((ROOT/'docs/evidence/tx-raw64-composition-input-20261020.json').read_text())
    deadline=time.monotonic()+10800
    while True:
        run=api('actions/runs/'+str(spec['run']))
        assert run['head_sha']==spec['source_head']and run['path']==spec['workflow_path']and run['run_attempt']==1 and run['head_branch']=='codex/complete-open-work'
        if run['status']=='completed':
            assert run['conclusion']=='success',('Native producer prerequisite rejected',spec['run'],run['conclusion'])
            break
        assert time.monotonic()<deadline,'Observation limit reached; do not restart live prerequisite'
        print(json.dumps(dict(waiting_for_exact_native_producer=spec['run'],status=run['status'])),flush=True)
        time.sleep(30)
    jobs=api('actions/runs/'+str(spec['run'])+'/jobs?per_page=100')['jobs']
    assert len(jobs)==1 and jobs[0]['name']=='native-producer-precision'and jobs[0]['conclusion']=='success'
    release=api('releases/tags/cloud-results-'+str(spec['run'])+'-1-tx-raw64-totalcap-precision');loaded={}
    for suffix in ('.summary.json','.parts.json'):
        found=[a for a in release['assets']if a['name'].endswith(suffix)];assert len(found)==1
        a=found[0];data=subprocess.check_output(['gh','api','-H','Accept: application/octet-stream',REPO+'releases/assets/'+str(a['id'])])
        digest=hashlib.sha256(data).hexdigest()
        assert len(data)==a['size']and a['digest']=='sha256:'+digest
        loaded[suffix]=(a,data,digest)
    a,data,digest=loaded['.summary.json'];b,parts,partsha=loaded['.parts.json'];r=json.loads(data)
    assert r['source_head']==spec['source_head']and r['sources_unchanged']
    assert r['status']=='PASS_REBUILT_NATIVE8074_RC_DOUBLE_TOTALS_AND13_CONTROLS_NOT_COMPOSED_ELECTRICAL_OR_PHY_ACCEPTANCE'
    assert r['baseline_reproduced_original_rc_and_failure']and r['no_rc_records_changed']and r['no_geometry_technology_or_threshold_change']
    assert len(r['controls']['cases'])==13 and r['controls']['status']=='PASS_REAL_NATIVE_BASELINE_AND13_RAW_CORRUPTION_CONTROLS'
    a=r['precise_audit']
    assert a['status']=='PASS_WIRE_GRAPH_AND_COLLAPSED_C_ONLY'and a['actual_exported_resistors']==137221 and a['actual_exported_capacitors']==98241
    return spec,dict(run=spec['run'],source_head=spec['source_head'],summary_asset=loaded['.summary.json'][0]['id'],summary_sha256=digest,parts_asset=b['id'],parts_sha256=partsha,report=r)
def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true';OUT.mkdir(parents=True,exist_ok=False);reports.OUT=OUT
    result=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],qualified_pex=False,qualified_substrate=False,full_serial_phy=False,mainchip_integrated=False,loaded_electrical_passed=False)
    def save():(OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    save()
    try:
        spec,pin=prerequisite();(OUT/'precision-source.json').write_text(json.dumps(pin,indent=2)+'\n')
        selected=['precise/rc01/wires.spice','precise/anchors03.json','precise/audit.json']
        prior,proof=reports.restore_report('tx-raw64-totalcap-precision',pin['run'],pin['summary_sha256'],pin['parts_sha256'],OUT/'rc',selected)
        assert prior==pin['report'];result['rc_source']=proof
        assert json.loads((OUT/'rc/precise/audit.json').read_text())==prior['precise_audit']
        bp=json.loads((ROOT/'docs/evidence/tx-raw64-intrinsic-pass-20261020.json').read_text())
        assert bp['run']==39482960779 and bp['source_head']=='0b685f0fefac2c6eb6a30aee199818aad7b747cf'
        names=['binding.json','native.json','raw8074-intrinsic.spice','source/anchors.json','pdk/libs.tech/klayout/python/sg13g2_pycell_lib/sg13g2_tech.json']
        bound,bproof=reports.restore_report('tx-raw64-intrinsic',bp['run'],bp['summary_sha256'],bp['parts_sha256'],OUT/'intrinsic',names)
        assert bound==bp['report']and bound['sources_unchanged']and len(bound['controls'])==15 and bound['negative_spacing_control']['rejected']
        result['intrinsic_source']=bproof
        native=json.loads((OUT/'intrinsic/native.json').read_text());binding=json.loads((OUT/'intrinsic/binding.json').read_text())
        anchors=json.loads((OUT/'rc/precise/anchors03.json').read_text());original_anchors=json.loads((OUT/'intrinsic/source/anchors.json').read_text())
        assert all(anchors[k]==original_anchors[k]for k in ('rows','anchors','public','negative_controls','counts'))
        tech=json.loads((OUT/'intrinsic/pdk/libs.tech/klayout/python/sg13g2_pycell_lib/sg13g2_tech.json').read_text())['techParams']
        compact=(OUT/'intrinsic/raw8074-intrinsic.spice').read_text()
        assert sha(OUT/'intrinsic/raw8074-intrinsic.spice')==bound['model_sha256']
        assert sha(OUT/'intrinsic/binding.json')==bound['binding_sha256']
        intrinsic.verify(compact,native,tech)
        wire=(OUT/'rc/precise/rc01/wires.spice').read_text()
        contract=compose.prepare(native,binding,anchors,compact,wire)
        output=compose.assemble(contract);compose.verify(output,contract)
        result['controls']=compose.controls(output,contract)
        assert len(result['controls'])==20
        final=OUT/'raw8074-wire.spice';final.write_text(output)
        formal=dict(interface=[*contract['ports'],'wire_cref'],device_records=contract['witnesses'],wire_node_map=contract['wire_map'],body_node_map=contract['body_map'],counts=dict(devices=8074,R=137221,C=98241,external_ports=164,physical_ports=163,metal_reference_planes=13344,body_nets=65,conductors=698,terminals=28582),no_ideal_driver_core_interconnect=True,every_native_mos_junction_preserved=True,every_raw_wire_record_preserved=True,every_terminal_reference_plane_preserved=True,substrate_spreading_included=False,device_access_resistance_included=False,qualified_pex=False)
        (OUT/'composition.json').write_text(json.dumps(formal,indent=2)+'\n')
        assert all(sha(OUT/'rc'/n)==prior['outputs'][n]for n in selected)
        assert all(sha(OUT/'intrinsic'/n)==bound['outputs'][n]for n in names)
        result.update(status='PASS_ACTUAL_FULL8074_PARENT_WIRE_COMPOSITION_AND20_CONTROLS_REQUIRES_LOADED_NATIVE_WAVES',sources_unchanged=True,counts=formal['counts'],model_sha256=sha(final),composition_sha256=sha(OUT/'composition.json'),methods={p:sha(ROOT/p)for p in ['scripts/cloud_tx_raw64_composition.py','scripts/compose_tx_raw64_native.py','scripts/cloud_tx_raw64_intrinsic.py']})
    except BaseException as error:result.update(status='FAIL_OR_ERROR',error=repr(error));raise
    finally:
        result['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};save()
if __name__=='__main__':main()
