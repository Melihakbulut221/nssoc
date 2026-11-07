#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""c5r3k PLL849 parent: integrate the verified child macros and run native DRC/LVS.

Inputs: the published passing RHI120/C8 parent (run 39914855175, pinned in
docs/evidence/pll-rhi120-c8-parent-pass-20261023.json) and the four c5r3k
child results of run 42397775128 (workflow artifacts, pinned below by the
SHA-256 of each result.json, which in turn pins every generated view).
"""
import argparse,json,os,shutil,subprocess,sys,tarfile
from pathlib import Path
import integrate_pll_c5r3k_parent as base
from run_cloud_tx_layout_repair import fetch,sha
ROOT=Path(__file__).resolve().parents[1];OUT=base.OUT
CHILD_RUN=42397775128
CHILDREN={'pump':'60b8c1cdd03e67be294f91863efb425878320b885f0a46758a15a3eb24af6d57',
          'vco':'07f2d90f27efa00ce1a897a76058c427085fec4fd9baca9212f2ed9b39891198',
          'div1':'471a67cece3762255287429df2a04f5a9250b94008f68169433bcfd9af8995c5',
          'integrator':'5b404296e5e406d49f9bbf5972dc05b1383d7c04bcf2b26d029895782c9aa6a9'}
CHILD_STATUS='PASS_C5R3K_CHILD_NATIVE_DRC_LVS_FAULTS_NOT_PARENT_OR_ELECTRICAL_ACCEPTANCE'

def main():
    p=argparse.ArgumentParser();p.add_argument('--generate',action='store_true');p.add_argument('--children',type=Path);args=p.parse_args()
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    if args.generate:base.generate();return
    import compare_cloud_routed_endpoints as reports
    OUT.mkdir(parents=True,exist_ok=False);reports.OUT=OUT
    r=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],top=base.TOP,expected_native_devices=base.DEVICES,accepted=False,full_phy_accepted=False,
        qualified_pex=False,closed_loop_accepted=False,main_chip_integrated=False,
        scope='c5r3k pump, VCO and first-divider macros swapped into the verified RHI120/C8 PLL845 parent and the vctrl integrator added in the free area with three routes. Native main DRC, deep and flat LVS at 849 devices and three faults. Fresh parent RC, acquisition and PVT remain required.')
    def save():(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
    save()
    try:
        pin=json.loads((ROOT/'docs/evidence/pll-rhi120-c8-parent-pass-20261023.json').read_text())
        names=['integrated/'+base.OLDTOP+'.gds','integrated/result.json','integrated/schematic.cir']
        prior,proof=reports.restore_report('pll-rhi120-c8-parent',pin['run'],pin['summary_sha256'],pin['parts_sha256'],OUT/'parent',names)
        assert prior['source_head']==pin['source_head'] and prior['status']==pin['status']
        assert prior['physical']['status']=='PASS_ACTUAL845_FILTER_PARENT_NATIVE_DRC_LVS_AND_FAULTS_NOT_RC'
        r['parent_source']=proof
        r['children']={}
        for key,digest in CHILDREN.items():
            src=args.children/key;res=src/'result.json';assert sha(res)==digest,key
            child=json.loads(res.read_text());assert child['status']==CHILD_STATUS and child['macro']==key
            layout={n:h for n,h in child['outputs'].items() if n.startswith('layout/')};assert layout
            for n,h in layout.items():assert sha(src/n)==h,(key,n)
            dest=OUT/'children'/key;dest.mkdir(parents=True);shutil.copytree(src/'layout',dest/'layout')
            r['children'][key]=dict(run=CHILD_RUN,result_sha256=digest,source_head=child['source_head'],layout_outputs=layout)
        save()
        spec=json.loads((ROOT/'docs/evidence/pcie-tx-layout-cloud-input-20261013.json').read_text());packed=OUT/'runtime.tar.gz'
        fetch(spec['receipt']['url'],spec['receipt']['sha256'],packed)
        with tarfile.open(packed)as tar:tar.extractall(ROOT,filter='data')
        packed.unlink();manifest=json.loads((ROOT/'manifest.json').read_text());assert all(sha(ROOT/n)==v['sha256']for n,v in manifest['files'].items())
        app=Path(os.environ['CLOUD_APPIMAGE']);assert sha(app)==spec['runtime_sha256'];r['runtime_sha256']=sha(app)
        r['method_hashes']={str(q):sha(q)for q in [Path(__file__),ROOT/'scripts/integrate_pll_c5r3k_parent.py']};save()
        with (OUT/'generate.log').open('w')as log:rc=subprocess.call([str(app),'python',str(Path(__file__).resolve()),'--generate'],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
        if rc:print((OUT/'generate.log').read_text(errors='replace')[-12000:],flush=True)
        assert rc==0,'Native parent generation failed'
        r['integrated']=json.loads((OUT/'integrated/result.json').read_text());save()
        r['physical']=base.verify(app)
        assert all(sha(ROOT/n)==v['sha256']for n,v in manifest['files'].items())
        assert all(sha(Path(n))==h for n,h in r['method_hashes'].items())
        r['status']='PASS_C5R3K_PARENT849_DRC_LVS_REQUIRES_FRESH_RC_AND_ACQUISITION'
    except BaseException as e:r.update(status='FAIL_OR_ERROR',error=repr(e));raise
    finally:
        for label in ('integrated','physical'):
            q=OUT/label/'result.json'
            if q.exists():r[label]=json.loads(q.read_text())
        r['outputs']={str(q.relative_to(OUT)):sha(q)for q in OUT.rglob('*')if q.is_file()and q!=OUT/'result.json'};save()
if __name__=='__main__':main()
