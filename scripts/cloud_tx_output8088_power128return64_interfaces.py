#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Bind full8088 physical sampling and output endpoints before loaded waves."""
import json,os,subprocess,traceback
from pathlib import Path
import compare_cloud_routed_endpoints as reports
from run_cloud_tx_layout_repair import sha
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'hw/soc/out/cloud-tx-output8088-power128return64-interfaces'
def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    OUT.mkdir(parents=True,exist_ok=False);reports.OUT=OUT
    r=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],qualified_pex=False,full_serial_phy=False,mainchip_integrated=False,loaded_electrical_passed=False)
    def save():(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
    save()
    try:
        delta=json.loads((ROOT/'scripts/tx-output8088-power128return64-interface-method.json').read_text())
        original=(ROOT/delta['baseline_path']).read_text();candidate=ROOT/delta['candidate_path']
        assert sha(ROOT/delta['baseline_path'])==delta['baseline_sha256']and sha(candidate)==delta['candidate_sha256']
        chunks=[];cursor=0
        for change in delta['changes']:
            assert cursor<=change['start']<=change['end']<=len(original)
            chunks.extend([original[cursor:change['start']],change['replacement']]);cursor=change['end']
        chunks.append(original[cursor:]);assert ''.join(chunks)==candidate.read_text()
        inputs=[
          ('tx-output8088-power128return64-physical',39895931760,'11cc148299aa8c3363de4d25f0f326944e56b2bf08a7618ec7da7a85dbf9770d','2cb514f3aed30a5965c8d204cc58e157524256b0ef6d155e9ac8bbe2406f71c8','physical',['layout/layout.gds','flat_lvs/result.lvsdb','integration-result.json']),
          ('tx-raw64-powered-physical',39466552523,'f5fcdbdee650f3c7868e671a9a05b0f3a7db3c78a0be76fe4afb828a1cd73d53','2a3431b7a2cae61f6b9edcbce8edeef23963bc62c170332064a5ab779ac58404','core-metadata',['source/core/layout/result.json','source/handoff-result.json']),
          ('tx-output8088-power128return64-native-wires',39897229856,'918072117513308657e7b2f0361b431ed08a965f4a50369a7155d388ea1032c0','0f5355e06d499b399b8734b964ca6190ae82e8df42e60751a9c39a3cc5c924ed','wires',['native01/result.json']),
          ('tx-output8088-power128return64-composition',39905090602,'0af88e610bfd9f6406a7987902a2459fc3aac2cbdcc8e224c76860586ab1001c','3240fceef721ca0b4b49610a7d7956ec44f4cecf02c2e6449ef73a86a121ab13','composed',['composition.json','output8088-wire.spice','intrinsic/native.json','intrinsic/source/anchors.json'])]
        protected={candidate:sha(candidate),ROOT/delta['baseline_path']:delta['baseline_sha256']}
        loaded={}
        for group,run,summary,parts,folder,names in inputs:
            report,proof=reports.restore_report(group,run,summary,parts,OUT/folder,names)
            assert report['sources_unchanged']and report['status'].startswith('PASS_')
            r.setdefault('sources',{})[folder]=proof;loaded[folder]=report
            for name in names:protected[OUT/folder/name]=report['outputs'][name]
            save()
        physical=loaded['physical']
        assert all(physical['steps'][name]['expected_verdict_observed']for name in ('drc','deep_lvs','flat_lvs','handoff_open','output_return_open','wrong_width','body_supply_short','wrong_output_Nx','internal_port_alias','offgrid','swap_output_inputs'))
        assert physical['geometry']['native_material_preserved']and physical['geometry']['serialized_geometry_verified']
        assert physical['geometry']['source_core_gds_sha256']==loaded['core-metadata']['outputs']['layout/layout.gds']=='9583c6cf7f70d4dad4736b808535ef564bed11d0730ce4674314025d0beaebdb'
        composed=loaded['composed']
        pin=json.loads((ROOT/'docs/evidence/tx-output8088-power128return64-composition-pass-20261023.json').read_text())
        assert pin['report']==composed and len(composed['controls'])==25
        assert sha(OUT/'composed/output8088-wire.spice')==composed['model_sha256']
        assert sha(OUT/'composed/composition.json')==composed['composition_sha256']
        topology=ROOT/'docs/evidence/tx-v5-timing-priority-physical-pass-20261019.json'
        p=json.loads(topology.read_text());assert p['run']==39304550527 and p['summary_sha256']=='03caa3a4f54f8e14402894a81321e33796f6ec6c502ec39fcc59e4db20e1dd5d'
        (OUT/'topology.json').write_text(json.dumps(p['report'],indent=2)+'\n');protected[topology]=sha(topology)
        app=Path(os.environ['CLOUD_APPIMAGE']);assert sha(app)=='d6a349ec65be11456e96c4981d35f63ca34d3c85daf79a51e1ccb907bb5d7466'
        log=OUT/'native-interface-binding.log'
        with log.open('w')as f:code=subprocess.call([str(app),'python',str(candidate),str(OUT),str(OUT/'interfaces.json')],cwd=ROOT,stdout=f,stderr=subprocess.STDOUT)
        r['native_binding']=dict(returncode=code,log_sha256=sha(log));save()
        if code:print(log.read_text(errors='replace')[-14000:],flush=True)
        assert code==0
        interfaces=json.loads((OUT/'interfaces.json').read_text())
        assert interfaces['status']=='PASS_ACTUAL8088_NATIVE124_INPUTS372_BASES64_DRIVER_HANDOFFS_FOUR_OUTPUT_PORTS_REQUIRES_LOADED_WAVES'
        assert len(interfaces['references'])==124 and len(interfaces['drivers'])==64 and len(interfaces['output_ports'])==4
        assert sum(len(x['terminals'])for x in interfaces['references'].values())==372
        assert interfaces['all_native_terminals_checked']==28620
        assert len(interfaces['controls'])==8 and len(interfaces['actual_endpoint_faults'])==2 and len(interfaces['output_port_controls'])==2
        assert all(sha(p)==digest for p,digest in protected.items())
        r.update(status=interfaces['status'],sources_unchanged=True,counts=dict(input_legs=124,data_bases=372,driver_handoffs=64,output_ports=4,native_terminals=28620),
            controls=interfaces['controls'],actual_endpoint_faults=interfaces['actual_endpoint_faults'],output_port_controls=interfaces['output_port_controls'],
            interfaces_sha256=sha(OUT/'interfaces.json'),protected_inputs={str(p):h for p,h in protected.items()},
            next_action='Prepare original34ns full loaded bench with actual8088 core/output; preserve all original stimuli, safety, bit-order and sampling gates. Remaining clock/bias/modulation boundaries remain explicit.')
    except BaseException as e:r.update(status='FAIL_OR_ERROR',error=repr(e),traceback=traceback.format_exc());raise
    finally:
        r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};save()
if __name__=='__main__':main()
