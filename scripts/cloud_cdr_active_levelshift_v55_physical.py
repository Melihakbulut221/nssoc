#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Native active level-shifter geometry; no whole-parent or PHY acceptance."""
import argparse,json,os,subprocess,sys,tarfile,traceback
from pathlib import Path
from run_cloud_tx_layout_repair import fetch,sha
ROOT=Path(__file__).resolve().parents[1]
MANIFEST=ROOT/'scripts/cdr-active-levelshift-v55-physical-method.json'
RECEIPT=ROOT/'docs/evidence/cdr-active-levelshift-v53-results-20261024.json'
def check():
    m=json.loads(MANIFEST.read_text())
    for p,h in m['protected'].items():assert sha(ROOT/p)==h,p
    return m
def component_evidence(out):
    rec=json.loads(RECEIPT.read_text())
    assert rec['run']==40043630319 and rec['source_head']=='3f7cf631e087830e13f763ee4f88cd0e61e3b7ea'
    assert {c['case']for c in rec['cases']}=={'nominal','hot_low','cold_high','swap_output','bias_off'}
    proofs=[]
    for c in rec['cases']:
        target=out/('component-'+c['case']+'.json')
        fetch(c['summary']['url'],c['summary']['sha256'],target)
        d=json.loads(target.read_text())
        assert d['source_head']==rec['source_head'] and d['case']==c['case']
        assert d['returncode']==0 and d['diagnostics']==[] and d['sources_unchanged']
        assert d['native_flags_verified']==2 and d['zero_source_op_maximum']<1e-9
        assert not any(d[k] for k in ('accepted','cdr_accepted','full_phy_accepted','physical_layout_matches','whole_parent_simulated'))
        found=[h for p,h in d['protected_inputs'].items()if p.endswith('/hw/soc/analog/pcie/cdr_active_levelshift_v53.spice')]
        assert found==[sha(ROOT/'hw/soc/analog/pcie/cdr_active_levelshift_v53.spice')]
        capture=d['raw_capture']
        assert capture['complete_unmodified_rows'] and capture['columns']==13 and capture['header_rows']>=109600
        assert capture['start_s']==0 and abs(capture['end_s']-34.25e-9)<1e-15 and capture['max_step_s']<=.3125e-12*1.00001
        if c['case']in ('swap_output','bias_off'):
            assert d['status']=='PASS_NATIVE_ACTIVE_LEVELSHIFT_FAULT_DETECTION_NOT_ACCEPTANCE' and d['actual_fault_detected'] and not d['component_signal_passed']
        else:
            assert d['status']=='PASS_NATIVE_ACTIVE_LEVELSHIFT_COMPONENT_ONLY_REQUIRES_PARENT_PHYSICAL_AND_FULL_CDR'
            assert d['devices_passed'] and d['component_signal_passed'] and d['component_commonmode_target_passed']
            assert d['wrong_sign_samples']==0 and d['below100mv_samples']==0 and d['minimum_signed_margin_v']>=.1
            assert d['maximum_input_to_valid_s']<=37.5e-12 and d['output_commonmode_v'][0]>=1.8 and d['output_commonmode_v'][1]<=2.15
        proofs.append(dict(case=c['case'],summary_sha256=sha(target),status=d['status']))
    return proofs
def main():
    p=argparse.ArgumentParser();p.add_argument('--kind',choices=('levelshift',),required=True);a=p.parse_args()
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    check()
    out=ROOT/'hw/soc/out/cloud-cdr-active-levelshift-v55-physical';out.mkdir(parents=True,exist_ok=False)
    r=dict(status='RUNNING',kind=a.kind,source_head=os.environ['GITHUB_SHA'],accepted=False,
           full_phy_accepted=False,closed_loop=False,qualified_pex=False,main_chip_integrated=False,
           scope='Unchanged v53 circuit in v55 geometry with actual stronger upper8x4 regular/4x4 TopVia1 arrays,16row tail MOS access and16cut/0.6um HBT emitter access:2HBT/3MOS/4R and9finite substrate contacts,8ports. Full560DRC,deep/flat18-device LVS and9actual fault controls. Component physical validation only; parent bias/load integration,fresh RC,loaded waves,PVT and full serial PHY remain required.')
    def save():(out/'result.json').write_text(json.dumps(r,indent=2)+'\n')
    save()
    try:
        r['component_preflight']=component_evidence(out);save()
        # Preserve and inspect the two native M3 spacing markers from the prior
        # actual candidate; no filter or waiver is applied to the new geometry.
        import compare_cloud_routed_endpoints as reports
        import xml.etree.ElementTree as ET
        reports.OUT=out
        previous_pin=json.loads((ROOT/'docs/evidence/cdr-active-levelshift-v55-upper-via-spacing-error-20261024.json').read_text())
        prior,proof=reports.restore_report('cdr-active-levelshift-v55-physical',previous_pin['run'],previous_pin['summary_sha256'],previous_pin['parts_sha256'],out/'prior-drc',['physical/drc/drc.lyrdb','layout/result.json'])
        assert prior==previous_pin['report']
        measurement=prior['physical']['steps']['drc']['measurement']
        assert measurement['category_count']==560 and measurement['categories']=={"'M3.b'":2}
        marker_path=out/'prior-drc/physical/drc/drc.lyrdb'
        assert sha(marker_path)==measurement['report_sha256']
        tree=ET.parse(marker_path)
        markers=[ET.tostring(item,encoding='unicode')for item in tree.findall('.//items/item')]
        assert len(markers)==2
        r['previous_drc_diagnosis']=dict(source=proof,markers=markers,corrective_geometry='HBT emitter upper regular via array8x4->8x2 to fit actual channel; all16lower cuts and0.6umM3 retained',waivers=[])
        save()
        protected={str(ROOT/p):h for p,h in check()['protected'].items()};protected[str(MANIFEST)]=sha(MANIFEST)
        r['protected_inputs']=protected
        spec=json.loads((ROOT/'docs/evidence/pcie-tx-layout-cloud-input-20261013.json').read_text())
        packed=out/'runtime.tar.gz';fetch(spec['receipt']['url'],spec['receipt']['sha256'],packed)
        with tarfile.open(packed)as tar:tar.extractall(ROOT,filter='data')
        packed.unlink()
        manifest=json.loads((ROOT/'manifest.json').read_text())
        assert all(sha(ROOT/n)==v['sha256']for n,v in manifest['files'].items())
        assert all(sha(Path(p))==h for p,h in protected.items())
        app=Path(os.environ['CLOUD_APPIMAGE']);assert sha(app)==spec['runtime_sha256']
        r['runtime_sha256']=sha(app);save()
        for name,command in [
            ('generation',[app,'python',ROOT/'hw/soc/flow/make_pcie_cdr_active_levelshift_v55.py','--pdk',ROOT/'pdk','--out',out/'layout','--kind',a.kind]),
            ('physical',[sys.executable,ROOT/'hw/soc/flow/check_pcie_cdr_active_levelshift_v55.py','--layout',out/'layout','--out',out/'physical','--app',app,'--kind',a.kind])]:
            with(out/(name+'.log')).open('w')as log:
                code=subprocess.call(list(map(str,command)),cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
            r[name+'_returncode']=code;save()
            if code:print((out/(name+'.log')).read_text()[-18000:],flush=True)
            assert code==0,name+' failed; preserve actual geometry and reports'
        physical=json.loads((out/'physical/result.json').read_text())
        assert physical['status']=='PASS_NATIVE_PDK_CDR_LEVELSHIFT18_DRC_LVS_AND_NINE_FAULT_CONTROLS'
        assert all(sha(Path(p))==h for p,h in protected.items());check()
        r.update(status='PASS_CDR_ACTIVE_LEVELSHIFT_V55_LEAF_PHYSICAL_REQUIRES_PARENT_RC_AND_LOADED_WAVES',sources_unchanged=True)
    except BaseException as e:r.update(status='FAIL_OR_ERROR',error=repr(e),traceback=traceback.format_exc());raise
    finally:
        for name in ('layout','physical'):
            p=out/name/'result.json'
            if p.exists():r[name]=json.loads(p.read_text())
        r['outputs']={str(p.relative_to(out)):sha(p)for p in out.rglob('*')if p.is_file()and p!=out/'result.json'}
        save()
if __name__=='__main__':main()
