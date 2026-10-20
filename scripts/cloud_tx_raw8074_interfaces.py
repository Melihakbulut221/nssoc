#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Cloud-only physical endpoint proof for the complete native8074 TX model."""
import json,os,subprocess,traceback
from pathlib import Path
import compare_cloud_routed_endpoints as reports
from run_cloud_tx_layout_repair import sha
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'hw/soc/out/cloud-tx-raw8074-interfaces'
def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    OUT.mkdir(parents=True,exist_ok=False);reports.OUT=OUT
    result=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],qualified_pex=False,full_serial_phy=False,mainchip_integrated=False,loaded_electrical_passed=False)
    def save():(OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    save()
    try:
        frozen=json.loads((ROOT/'scripts/tx-raw8074-interface-methods.json').read_text())
        assert all(sha(ROOT/p)==h for p,h in frozen.items())
        inputs=[
          ('tx-raw64-powered-physical',39466552523,'f5fcdbdee650f3c7868e671a9a05b0f3a7db3c78a0be76fe4afb828a1cd73d53','2a3431b7a2cae61f6b9edcbce8edeef23963bc62c170332064a5ab779ac58404','physical',
           ['layout/layout.gds','flat_lvs/result.lvsdb','source/core/layout/result.json','source/handoff-result.json','power-result.json']),
          ('tx-raw64-native-wires',39467260490,'8b0dc962fbd7bd98044eed205fe0e5fdbe19c3ea11433e32e0d2f699bcf81af6','351da636eafc92faa8ba055af2d6444108c0ea6892f7b573ad413cd464ad766b','wires',['native01/result.json']),
          ('tx-raw64-composition',39490645237,'b29553a65f7c29a8dc06072e9bf5c44876ac10bc3053ccf0c61fa219c389dd6c','31d9a0f96d2865bf0a54cf0493b71f00ee8c0774878556e9eba8a998d45c3602','composed',
           ['composition.json','raw8074-wire.spice','intrinsic/native.json','intrinsic/source/anchors.json'])]
        protected={ROOT/p:h for p,h in frozen.items()};loaded={}
        for group,run,summary,parts,folder,names in inputs:
            r,proof=reports.restore_report(group,run,summary,parts,OUT/folder,names)
            assert r['sources_unchanged'] and r['status'].startswith('PASS_')
            result.setdefault('sources',{})[folder]=proof;loaded[folder]=r
            for name in names:protected[OUT/folder/name]=r['outputs'][name]
            save()
        physical=loaded['physical']
        assert all(physical['steps'][s]['expected_verdict_observed'] for s in ('drc','deep_lvs','flat_lvs','handoff_open','body_supply_short','wrong_width','internal_port_alias','offgrid'))
        assert physical['geometry']['native_material_preserved'] and physical['geometry']['serialized_geometry_verified']
        composition=loaded['composed'];assert len(composition['controls'])==20
        assert composition['counts']['devices']==8074 and composition['counts']['R']==137221 and composition['counts']['C']==98241
        assert sha(OUT/'composed/raw8074-wire.spice')==composition['model_sha256']
        assert sha(OUT/'composed/composition.json')==composition['composition_sha256']
        topology=ROOT/'docs/evidence/tx-v5-timing-priority-physical-pass-20261019.json'
        p=json.loads(topology.read_text())
        assert p['run']==39304550527 and p['summary_sha256']=='03caa3a4f54f8e14402894a81321e33796f6ec6c502ec39fcc59e4db20e1dd5d'
        (OUT/'topology.json').write_text(json.dumps(p['report'],indent=2)+'\n')
        protected[topology]=sha(topology)
        app=Path(os.environ['CLOUD_APPIMAGE'])
        assert sha(app)=='d6a349ec65be11456e96c4981d35f63ca34d3c85daf79a51e1ccb907bb5d7466'
        log=OUT/'native-interface-binding.log'
        with log.open('w')as f:
            rc=subprocess.call([str(app),'python',str(ROOT/'scripts/bind_tx_raw8074_interfaces.py'),str(OUT),str(OUT/'interfaces.json')],cwd=ROOT,stdout=f,stderr=subprocess.STDOUT)
        result['native_binding']=dict(returncode=rc,log_sha256=sha(log));save()
        if rc:print(log.read_text(errors='replace')[-14000:],flush=True)
        assert rc==0,'Native full-parent interface binding failed'
        interfaces=json.loads((OUT/'interfaces.json').read_text())
        assert interfaces['status']=='PASS_ACTUAL8074_NATIVE124_INPUTS372_BASES64_DRIVER_HANDOFFS_REQUIRES_LOADED_WAVES'
        assert len(interfaces['references'])==124 and len(interfaces['drivers'])==64
        assert sum(len(v['terminals']) for v in interfaces['references'].values())==372
        assert interfaces['all_native_terminals_checked']==28582
        assert len(interfaces['controls'])==8 and len(interfaces['actual_endpoint_faults'])==2
        assert all(sha(p)==h for p,h in protected.items())
        result.update(status=interfaces['status'],sources_unchanged=True,counts=dict(input_legs=124,data_bases=372,driver_handoffs=64,native_terminals=28582),
          controls=interfaces['controls'],actual_endpoint_faults=interfaces['actual_endpoint_faults'],interfaces_sha256=sha(OUT/'interfaces.json'),
          protected_inputs={str(p):h for p,h in protected.items()},
          next_action='Build original complete loaded waveform bench using these actual physical probes and full8074 wire model; preserve actual native simulator process state before CI limit. External clock macros still require physical assembly.')
    except BaseException as e:result.update(status='FAIL_OR_ERROR',error=repr(e),traceback=traceback.format_exc());raise
    finally:
        result['outputs']={str(p.relative_to(OUT)):sha(p) for p in OUT.rglob('*') if p.is_file() and p!=OUT/'result.json'};save()
if __name__=='__main__':main()
