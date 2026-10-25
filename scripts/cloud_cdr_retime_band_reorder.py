#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Cloud-only v16 band reorder, immutable child proof and original native gates."""
import json,os,shutil,subprocess,sys,tarfile
from pathlib import Path
import compare_cloud_routed_endpoints as reports
from run_cloud_tx_layout_repair import fetch,sha
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'hw/soc/out/cloud-cdr-retime-band-reorder'
TOP='nssoc_cdr_pd484_localbus_v12'
def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    OUT.mkdir(parents=True,exist_ok=False);reports.OUT=OUT
    r=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],accepted=False,
        full_phy_accepted=False,closed_loop=False,qualified_pex=False,main_chip_integrated=False)
    def save():(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
    save()
    try:
        pinpath=ROOT/'docs/evidence/cdr-retime-data-v16-physical-pass-20261020.json'
        pin=json.loads(pinpath.read_text())
        assert pin['run']==39334427158 and pin['source_head']=='93bd54c05201d089babb5cc9049f174dd5338ca4'
        assert pin['summary_sha256']=='e1eac820df0d11888ee2a8b1b588e9e01bb17b20dbb110240b2687b45787e3f2'
        assert pin['parts_sha256']=='8bbd2c71846e9e5dd4310ff2c02017773f1c048df0cb44e4a1404b7e0ca90c64'
        leaves=[n for n in pin['report']['outputs']if n=='children.json'or n.startswith('inputs/')]
        assert 'children.json'in leaves and len([n for n in leaves if n.endswith('.gds')])==8
        names=['layout/result.json','layout/schematic.cir','layout/'+TOP+'.gds','layout/'+TOP+'.lef']+leaves
        prior,proof=reports.restore_report(pin['group'],pin['run'],pin['summary_sha256'],pin['parts_sha256'],OUT/'baseline',names)
        assert prior==pin['report']and prior['sources_unchanged']
        assert prior['status']=='PASS_PD484_NATIVE_RETIME_DATA_ACCESS_PHYSICAL_REQUIRES_FRESH_RC_AND_ORIGINAL_LOADED_GATES'
        assert prior['physical']['status']=='PASS_NATIVE_PDK_CDR_PD484_DRC_LVS_AND_FAULT_CONTROLS'
        assert sha(OUT/'baseline/layout'/(TOP+'.gds'))=='c920186862bde235868d3fa009fedcff868246750f0fa38874e3c6b42ba7255e'
        r['physical_source']=proof
        for n in leaves:
            src=OUT/'baseline'/n;dst=OUT/n
            assert sha(src)==prior['outputs'][n]
            dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(src,dst)
        methods=[Path(__file__),pinpath,ROOT/'scripts/generate_cdr_retime_band_reorder.py',
            ROOT/'scripts/check_cdr_localbus_v12_parent_geometry.py',
            ROOT/'hw/soc/flow/check_pcie_cdr_retimed_localbus_v12_parent.py']
        protected={str(p):sha(p)for p in [*methods,*[OUT/'baseline'/n for n in names],*[OUT/n for n in leaves]]}
        spec=json.loads((ROOT/'docs/evidence/pcie-tx-layout-cloud-input-20261013.json').read_text())
        packed=OUT/'runtime.tar.gz';fetch(spec['receipt']['url'],spec['receipt']['sha256'],packed)
        with tarfile.open(packed)as t:t.extractall(ROOT,filter='data')
        packed.unlink();runtime=json.loads((ROOT/'manifest.json').read_text())
        assert all(sha(ROOT/n)==v['sha256']for n,v in runtime['files'].items())
        app=Path(os.environ['CLOUD_APPIMAGE']);assert sha(app)==spec['runtime_sha256']
        r['runtime_sha256']=sha(app);assert all(sha(Path(n))==v for n,v in protected.items());save()
        script="import sys,json;from pathlib import Path;sys.path.insert(0,'scripts');from check_cdr_localbus_v12_parent_geometry import check;p=Path(sys.argv[1]);r=check(p);(p/'child-geometry-proof.json').write_text(json.dumps(r,indent=2)+'\\n')"
        commands=[
            ('generation',[app,'python',ROOT/'scripts/generate_cdr_retime_band_reorder.py','--out',OUT]),
            ('child_geometry',[app,'python','-c',script,OUT]),
            ('physical',[sys.executable,ROOT/'hw/soc/flow/check_pcie_cdr_retimed_localbus_v12_parent.py','--layout',OUT/'layout','--out',OUT/'physical','--app',app])]
        for name,cmd in commands:
            with(OUT/(name+'.log')).open('w')as f:code=subprocess.call(list(map(str,cmd)),cwd=ROOT,stdout=f,stderr=subprocess.STDOUT)
            r[name+'_returncode']=code
            for key,file in [('geometry','geometry-proof.json'),('child_geometry','child-geometry-proof.json')]:
                if (OUT/file).is_file():r[key]=json.loads((OUT/file).read_text())
            save()
            if code:print((OUT/(name+'.log')).read_text()[-16000:],flush=True)
            assert code==0,('Actual reordered parent stage failed',name,code)
        g=r['geometry']
        assert g['enumerated']==720 and g['candidate_target_span_um']<g['original_target_span_um']
        assert all(g[k]for k in ('original_child_hierarchy_preserved','all_parent_band_geometry_conserved',
            'all_original_v13_v14_v15_v16_local_overlays_preserved','exact_serialized_geometry_checked','reference_byte_identical'))
        assert len(g['controls'])==2
        assert r['child_geometry']['status']=='PASS_ALL16_ACTUAL_PLACEMENTS_AND_EIGHT_NATIVE_LEAF_DRAWINGS'
        assert len(r['child_geometry']['controls'])==3
        r['physical']=json.loads((OUT/'physical/result.json').read_text())
        assert r['physical']['status']=='PASS_NATIVE_PDK_CDR_PD484_DRC_LVS_AND_FAULT_CONTROLS'
        assert all(sha(Path(n))==v for n,v in protected.items())
        assert all(sha(ROOT/n)==v['sha256']for n,v in runtime['files'].items())
        r.update(status='PASS_PD484_V16_BAND_REORDER_PHYSICAL_REQUIRES_FRESH_FULL_RC_AND_ORIGINAL_LOADED_GATES',
            sources_unchanged=True,protected_inputs=protected,
            scope='Permute six complete native physical bands, preserve original484devices and all local v16 geometry, rebuild global TM1 trunk lengths, verify all original560DRC and deep/flatLVS/fault gates. No waveform or timing acceptance without fresh full extraction and original loaded gates.')
    except BaseException as e:r.update(status='FAIL_OR_ERROR',error=repr(e));raise
    finally:
        for name in ('layout','physical'):
            p=OUT/name/'result.json'
            if p.is_file():r[name]=json.loads(p.read_text())
        r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'}
        save()
if __name__=='__main__':main()
