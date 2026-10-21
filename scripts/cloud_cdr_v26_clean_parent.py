#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Validate actual v26 parent metal cleanup with original full physical and graph gates."""
import json,os,shutil,subprocess,sys,tarfile
from pathlib import Path
import compare_cloud_routed_endpoints as reports
from run_cloud_tx_layout_repair import fetch,sha
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'hw/soc/out/cloud-cdr-input-access-v26-clean-parent'
TOP='nssoc_cdr_pd476_follower_v23'
def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    OUT.mkdir(parents=True,exist_ok=False);reports.OUT=OUT
    r=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],accepted=False,qualified_pex=False,full_phy_accepted=False,closed_loop=False)
    def save():(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
    def run(label,cmd):
        with(OUT/(label+'.log')).open('w')as log:code=subprocess.call(list(map(str,cmd)),cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
        r.setdefault('commands',[]).append(dict(label=label,returncode=code));save()
        if code:print((OUT/(label+'.log')).read_text()[-18000:],flush=True)
        assert code==0,(label,code)
    try:
        pin=json.loads((ROOT/'docs/evidence/cdr-input-access-v26-parent-physical-pass-20261021.json').read_text())
        assert pin['run']==39525872386 and pin['summary_sha256']=='44361f37b6558c13937c127027e911cd6136d60a96ede44c061d7e0da52c0dae'
        wanted=[n for n in pin['outputs']if n.startswith(('layout/','inputs/','physical/lvs_flat/'))or n=='children.json']
        prior,proof=reports.restore_report('cdr-input-access-v26-parent',pin['run'],pin['summary_sha256'],pin['parts_sha256'],OUT/'baseline',wanted)
        assert prior==pin['report']and prior['sources_unchanged']
        diag,dp=reports.restore_report('cdr-v26-unowned-metal-diagnosis',39529481164,
            'e7ee8a8373b94deb650ae1b5e82170650ae6dc99dff5cbd4b7ecd4e921091513',
            '242ed607927b3d47b556f3c6d32230715c4f7826511cfc28b927fd44bfeaf6ac',
            OUT/'diagnosis',['source/unowned-metal.json','source/wire/probe01.py'])
        assert diag['status']=='COMPLETE_UNOWNED_METAL_DIAGNOSIS_REQUIRES_PHYSICAL_FIX'and diag['sources_unchanged']and diag['strict_original_gate_reproduced']
        assert diag['failed_source']['summary_sha256']=='01976c2338fa22fa9f978ffb90d0afde5edf59e9d325053a25522e9c258b7c44'
        for n in ('layout','inputs'):shutil.copytree(OUT/'baseline'/n,OUT/n)
        shutil.copyfile(OUT/'baseline/children.json',OUT/'children.json')
        methods=[Path(__file__),ROOT/'scripts/clean_cdr_v26_parent_metal.py',ROOT/'scripts/check_cdr_follower_v23_parent_geometry.py',ROOT/'hw/soc/flow/check_pcie_cdr_follower_v23_parent.py']
        protected={str(p):sha(p)for p in [*methods,*[OUT/'baseline'/n for n in wanted]]}
        runtime=json.loads((ROOT/'docs/evidence/pcie-tx-layout-cloud-input-20261013.json').read_text())
        packed=OUT/'runtime.tar.gz';fetch(runtime['receipt']['url'],runtime['receipt']['sha256'],packed)
        with tarfile.open(packed)as t:t.extractall(ROOT,filter='data')
        packed.unlink();manifest=json.loads((ROOT/'manifest.json').read_text())
        assert all(sha(ROOT/n)==v['sha256']for n,v in manifest['files'].items())
        app=Path(os.environ['CLOUD_APPIMAGE']);assert sha(app)==runtime['runtime_sha256']
        run('cleanup',[app,'python',ROOT/'scripts/clean_cdr_v26_parent_metal.py','--out',OUT])
        script="import sys,json;from pathlib import Path;sys.path.insert(0,'scripts');from check_cdr_follower_v23_parent_geometry import check;p=Path(sys.argv[1]);(p/'child-geometry-proof.json').write_text(json.dumps(check(p),indent=2)+'\\n')"
        run('child_geometry',[app,'python','-c',script,OUT])
        run('physical',[sys.executable,ROOT/'hw/soc/flow/check_pcie_cdr_follower_v23_parent.py','--layout',OUT/'layout','--out',OUT/'physical','--app',app])
        graph=OUT/'wire';graph.mkdir()
        original=(OUT/'diagnosis/source/wire/probe01.py').read_text()
        assert original.count("P/'parent/layout/")==2 and original.count("P/'parent/physical/")==2 and original.count("P/'parent/layout/result.json'")==1
        adapted=original.replace("P/'parent/layout/","P/'layout/").replace("P/'parent/physical/","P/'physical/")
        probe=graph/'probe01.py';probe.write_text(adapted)
        run('strict_native_graph',[app,'python',probe])
        result=json.loads((graph/'native05/result.json').read_text())
        assert result['native_device_count']==476 and result['native_terminal_count']==1382 and result['wire_component_count']==111
        assert result['no_wire_geometry_change']and result['no_component_union_by_native_label']
        r['cleanup']=json.loads((OUT/'cleanup-proof.json').read_text())
        r['child_geometry']=json.loads((OUT/'child-geometry-proof.json').read_text())
        r['physical']=json.loads((OUT/'physical/result.json').read_text())
        assert r['physical']['status']=='PASS_NATIVE_PDK_CDR_PD476_DRC_LVS_AND_FAULT_CONTROLS'
        assert r['child_geometry']['status']=='PASS_ALL16_ACTUAL_PLACEMENTS_AND_EIGHT_NATIVE_LEAF_DRAWINGS'
        assert all(sha(Path(p))==h for p,h in protected.items())
        assert all(sha(ROOT/n)==v['sha256']for n,v in manifest['files'].items())
        r.update(status='PASS_PD476_V26_CLEAN_PARENT_PHYSICAL_AND_STRICT111_COMPONENT_GRAPH_REQUIRES_FRESH_RC',sources_unchanged=True,
            parent_source=proof,diagnosis_source=dp,intrinsic_replacement_history=prior['replacement'],strict_graph=result,
            graph_source_delta=dict(original_sha256=sha(OUT/'diagnosis/source/wire/probe01.py'),adapted_sha256=sha(probe),only_parent_input_paths_changed=True))
    except BaseException as e:r.update(status='FAIL_OR_ERROR',error=repr(e));raise
    finally:
        for k in ('layout','physical'):
            p=OUT/k/'result.json'
            if p.exists():r[k]=json.loads(p.read_text())
        r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};save()
if __name__=='__main__':main()
