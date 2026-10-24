#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Restore verified leaves, physically assemble and verify the complete retimed PD."""
import json,os,subprocess,sys,tarfile
from pathlib import Path
import compare_cloud_routed_endpoints as reports
from run_cloud_tx_layout_repair import fetch,sha
from cdr_retimed_via_rich_v7_parent_plan import build,verify,TYPES,controls
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'hw/soc/out/cloud-cdr-retimed-via-rich-v7-parent'
def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    OUT.mkdir(parents=True,exist_ok=False);reports.OUT=OUT
    r=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],full_phy_accepted=False,closed_loop=False,qualified_pex=False,main_chip_integrated=False)
    def save():(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
    save()
    try:
        specpath=ROOT/'docs/evidence/cdr-retimed-via-rich-v7-parent-children-20261018.json';spec=json.loads(specpath.read_text());assert set(spec['children'])==set(TYPES)
        protected={str(p):sha(p)for p in [Path(__file__),specpath,ROOT/'scripts/cdr_retimed_via_rich_v7_parent_plan.py',ROOT/'scripts/generate_cdr_retimed_via_rich_v7_parent.py',ROOT/'hw/soc/flow/check_pcie_cdr_retimed_via_rich_v7_parent.py',ROOT/'scripts/generate_cdr_retimed_parallel_v3_risers.py',ROOT/'scripts/generate_cdr_retimed_avss256_base.py',ROOT/'scripts/cdr-avss256-placement-delta.json',ROOT/'scripts/generate_cdr_retimed_parallel_v3_base.py',ROOT/'scripts/check_cdr_via_rich_v7_parent_sources.py',ROOT/'scripts/cdr-via-rich-v7-parent-source-delta.json',ROOT/'scripts/check_cdr_xor_power_access_geometry.py',ROOT/'scripts/check_cdr_sampler_via_rich_geometry.py',ROOT/'scripts/generate_cdr_retimed_strapped_v6_risers.py']}
        from check_cdr_via_rich_v7_parent_sources import check
        check()
        r['source_controls']=controls();manifest=dict(status='ALL_EIGHT_CHILD_SOURCE_PROOFS_BOUND',children={});r['child_sources']={}
        for kind,pin in spec['children'].items():
            folder=pin['directory'];name=TYPES[kind]['top'];selected=[folder+'/result.json',folder+'/schematic.cir',folder+'/'+name+'.gds',folder+'/'+name+'.lef']
            dest=OUT/'inputs'/kind
            prior,proof=reports.restore_report(pin['group'],pin['run'],pin['summary_sha256'],pin['parts_sha256'],dest,selected)
            assert prior['source_head']==pin['source_head']and prior['status']==pin['status']and prior['sources_unchanged']
            physical=prior['physical'];steps=physical['steps'];steps={s['name']:s for s in steps}if isinstance(steps,list)else steps
            assert steps['drc']['measurement']['status']=='PASS'and steps['drc']['measurement']['category_count']==560
            for key in ('lvs','lvs_flat'):
                a=steps[key]['audit'];assert a['status']=='PASS within comparison scope'and not a['extraction_diagnostics']
                roots=[x for x in a['circuits']if x['layout'].lower()==name.lower()];assert len(roots)==1
                assert roots[0]['layout_devices_recursive']==roots[0]['schematic_devices_recursive']==TYPES[kind]['devices']
            files={str((dest/n).relative_to(OUT)):sha(dest/n)for n in selected}
            assert all(sha(dest/n)==prior['outputs'][n]for n in selected)
            manifest['children'][kind]=dict(directory=str((dest/folder).relative_to(OUT)),files=files);r['child_sources'][kind]=proof;save()
        (OUT/'children.json').write_text(json.dumps(manifest,indent=2)+'\n')
        source=json.loads((ROOT/'docs/evidence/pcie-tx-layout-cloud-input-20261013.json').read_text());packed=OUT/'runtime.tar.gz';fetch(source['receipt']['url'],source['receipt']['sha256'],packed)
        with tarfile.open(packed)as t:t.extractall(ROOT,filter='data')
        packed.unlink();runtime=json.loads((ROOT/'manifest.json').read_text());assert all(sha(ROOT/n)==v['sha256']for n,v in runtime['files'].items())
        assert all(sha(Path(p))==h for p,h in protected.items())
        app=Path(os.environ['CLOUD_APPIMAGE']);assert sha(app)==source['runtime_sha256'];r['runtime_sha256']=sha(app)
        baseline_pin=json.loads((ROOT/'docs/evidence/cdr-retimed-parallel-v3-parent-children-20261018.json').read_text())['children']['xor']
        oldtop='nssoc_cdr_xor_hybrid_tail_layout_v3';selected=['layout/result.json','layout/schematic.cir','layout/'+oldtop+'.gds','layout/'+oldtop+'.lef']
        prior,proof=reports.restore_report(baseline_pin['group'],baseline_pin['run'],baseline_pin['summary_sha256'],baseline_pin['parts_sha256'],OUT/'geometry-baseline',selected)
        assert prior['source_head']==baseline_pin['source_head'] and prior['status']==baseline_pin['status']
        proofpath=OUT/'xor-geometry-conservation.json'
        with (OUT/'xor-geometry-conservation.log').open('w')as log:
            rc=subprocess.call([str(app),'python',str(ROOT/'scripts/check_cdr_xor_power_access_geometry.py'),'--baseline',str(OUT/'geometry-baseline/layout'),'--candidate',str(OUT/'inputs/xor/layout'),'--output',str(proofpath)],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
        if rc:print((OUT/'xor-geometry-conservation.log').read_text()[-12000:],flush=True)
        assert rc==0,'Independent XOR drawing conservation failed'
        geometry=json.loads(proofpath.read_text());assert geometry['status']=='PASS_EXACT_NATIVE_XOR59_POWER_ADDITIONS_AND_THREE_GEOMETRY_FAULTS'
        r['xor_geometry_conservation']=geometry;r['xor_baseline_source']=proof;save()
        sampler_pin=json.loads((ROOT/'docs/evidence/cdr-retimed-strapped-v6-parent-children-20261018.json').read_text())['children']['sampler']
        sampler_top='nssoc_rx_sampler_strapped_layout_v10';selected=['layout/result.json','layout/schematic.cir','layout/'+sampler_top+'.gds','layout/'+sampler_top+'.lef']
        original_sampler,sampler_proof=reports.restore_report(sampler_pin['group'],sampler_pin['run'],sampler_pin['summary_sha256'],sampler_pin['parts_sha256'],OUT/'sampler-baseline',selected)
        assert original_sampler['source_head']==sampler_pin['source_head'] and original_sampler['status']==sampler_pin['status'] and original_sampler['sources_unchanged']
        proofpath=OUT/'sampler-primitive-conservation.json'
        with (OUT/'sampler-primitive-conservation.log').open('w')as log:
            rc=subprocess.call([str(app),'python',str(ROOT/'scripts/check_cdr_sampler_via_rich_geometry.py'),'--baseline',str(OUT/'sampler-baseline/layout'),'--candidate',str(OUT/'inputs/sampler/layout'),'--output',str(proofpath)],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
        if rc:print((OUT/'sampler-primitive-conservation.log').read_text()[-12000:],flush=True)
        assert rc==0,'Independent sampler primitive drawing comparison failed'
        sampler_geometry=json.loads(proofpath.read_text());assert sampler_geometry['status']=='PASS_ALL54_NATIVE_PRIMITIVE_DRAWINGS_REFERENCE_AND_THREE_CONTROLS'
        r['sampler_geometry_conservation']=sampler_geometry;r['sampler_baseline_source']=sampler_proof;save()
        for name,cmd in [('generation',[app,'python',ROOT/'scripts/generate_cdr_retimed_via_rich_v7_parent.py','--out',OUT]),('physical',[sys.executable,ROOT/'hw/soc/flow/check_pcie_cdr_retimed_via_rich_v7_parent.py','--layout',OUT/'layout','--out',OUT/'physical','--app',app])]:
            with (OUT/(name+'.log')).open('w')as log:rc=subprocess.call(list(map(str,cmd)),cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
            r[name+'_returncode']=rc;save()
            if rc:print((OUT/(name+'.log')).read_text()[-16000:],flush=True)
            assert rc==0,'Actual parent '+name+' failed'
        r['physical']=json.loads((OUT/'physical/result.json').read_text());assert r['physical']['status']=='PASS_NATIVE_PDK_CDR_PD484_DRC_LVS_AND_FAULT_CONTROLS'
        assert all(sha(Path(p))==h for p,h in protected.items());r.update(status='PASS_PD484_HYBRID_PHYSICAL_REQUIRES_NEW_RC_AND_ORIGINAL_LOADED_GATES',sources_unchanged=True,protected_inputs=protected)
    except BaseException as e:r.update(status='FAIL_OR_ERROR',error=repr(e));raise
    finally:
        for name in ('layout','physical'):
            p=OUT/name/'result.json'
            if p.exists():r[name]=json.loads(p.read_text())
        r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};save()
if __name__=='__main__':main()
