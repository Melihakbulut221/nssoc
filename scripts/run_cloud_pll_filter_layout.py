#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Real candidate pump geometry and native gates; no parent/PEX/PHY acceptance."""
import argparse,hashlib,json,os,subprocess,sys,tarfile
from pathlib import Path
from run_cloud_tx_layout_repair import fetch,sha
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'hw/soc/out/cloud-pll-filter-layout'
SOURCES={9: ('pll_pump_filter_hv_rhi140_c9_v1.spice', 'e9f3f758184012e63a05d5ba3d91b3bc3a0fe3f0844053e986a8c2d438902364'), 11: ('pll_pump_filter_hv_rhi140_c11_v1.spice', 'fa61c8591f26d7b032d55bb4aacdeaa9402c2db44522f7fd3bc04e7fa4049e97')}
def generate(size):
    sys.path.insert(0,str(ROOT/'hw/soc/flow'))
    import make_pcie_pump_filter13_v1 as base
    source_dir=ROOT/'hw/soc/analog/pcie'
    name,digest=SOURCES[size]
    reference=source_dir/'pll_pump_filter_hv_rhi140_v1.spice'
    assert sha(reference)=='74ff41874333ea58362338efb9f81fdf5b8d9f6e601e7cde27ed0b0c22104a3c'
    cp='pll_pfd_charge_pump_hv_v1.spice';assert sha(source_dir/cp)==base.SOURCES[cp]
    assert sha(source_dir/name)==digest
    def rows(text):
        d=base.definitions({'filter':text,cp:(source_dir/cp).read_text()})
        result,wires=base.expand(d,['nssoc_tail115_pump_filter13_v1','xloop',base.PORTS]);assert not wires and len(result)==13
        return result
    before=rows(reference.read_text());expected=json.loads(json.dumps(before));caps=[r for r in expected if r['path']=='xloop.xc']
    assert len(caps)==1 and caps[0]['model']=='cap_cmim' and caps[0]['nets']==['vctrl','avss']
    assert caps[0]['params']=={'w':'10u','l':'10u'}
    caps[0]['params']={'w':str(size)+'u','l':str(size)+'u'}
    candidate=rows((source_dir/name).read_text());assert candidate==expected
    base.TOP='nssoc_pump_filter13_rhi140_c'+str(size)+'_v1'
    base.SOURCES={name:digest,cp:base.SOURCES[cp]}
    base.build(ROOT/'pdk',OUT/'layout')
    p=OUT/'layout/result.json';r=json.loads(p.read_text())
    assert len(r['core_devices'])==13 and r['substrate_contacts']==13 and r['well_contacts']==4
    r['inputs'][str(Path(__file__).resolve())]=sha(Path(__file__).resolve())
    r['inputs'][str(reference)]=sha(reference)
    r['only_core_change_from_rhi140']=dict(path='xloop.xc',old_dimensions_um=[10,10],new_dimensions_um=[size,size],other12core_devices_unchanged=True)
    r['closed_loop_accepted']=False
    p.write_text(json.dumps(r,indent=2)+'\n')
def main():
    p=argparse.ArgumentParser();p.add_argument('--size-um',type=int,choices=(9,11),required=True);p.add_argument('--generate',action='store_true');args=p.parse_args()
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    if args.generate:generate(args.size_um);return
    OUT.mkdir(parents=True,exist_ok=False)
    result=dict(status='RUNNING',size_um=args.size_um,source_head=os.environ['GITHUB_SHA'],accepted=False,parent_integrated=False,qualified_pex=False,serial_phy_complete=False,main_chip_integrated=False,
        scope='Real13core+17contact pump macro with native PCell capacitor and unchanged RHI140. Full native DRC/deep and flat30device LVS/geometry and reference fault controls/LEF checks. Not new parent wiring, fresh RC or electrical acceptance.')
    def save():(OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    def run(command,label):
        with (OUT/(label+'.log')).open('w') as log:code=subprocess.call([str(x) for x in command],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
        if code:
            print((OUT/(label+'.log')).read_text(errors='replace')[-12000:],flush=True)
            raise RuntimeError((label,code))
    save()
    protected=[Path(__file__).resolve(),ROOT/'hw/soc/flow/make_pcie_pump_filter13_v1.py',ROOT/'hw/soc/flow/check_pcie_pump_filter13_v1.py',ROOT/'hw/soc/flow/check_pcie_pump_filter13_lef.py',*[ROOT/'hw/soc/analog/pcie'/v[0] for v in SOURCES.values()]]
    pinned={str(p):sha(p) for p in protected}
    try:
        spec=json.loads((ROOT/'docs/evidence/pcie-tx-layout-cloud-input-20261013.json').read_text())
        packed=OUT/'restore.tar.gz';fetch(spec['receipt']['url'],spec['receipt']['sha256'],packed)
        assert packed.stat().st_size==spec['receipt']['bytes']
        with tarfile.open(packed) as tar:tar.extractall(ROOT,filter='data')
        packed.unlink();manifest=json.loads((ROOT/'manifest.json').read_text())
        assert all(sha(ROOT/n)==v['sha256'] for n,v in manifest['files'].items())
        assert all(sha(Path(n))==v for n,v in pinned.items())
        from run_cloud_pll_filter_lef import restore_technology
        tech=restore_technology();pinned[str(tech)]=sha(tech)
        app=Path(os.environ['CLOUD_APPIMAGE']);assert sha(app)==spec['runtime_sha256']
        result['runtime_sha256']=sha(app);result['input_bundle']=spec['receipt'];save()
        run([app,'python',Path(__file__).resolve(),'--generate','--size-um',args.size_um],'generate')
        result['layout']=json.loads((OUT/'layout/result.json').read_text());save()
        sys.path.insert(0,str(ROOT/'hw/soc/flow'))
        import check_pcie_pump_filter13_v1 as physical
        import check_pcie_pump_filter13_lef as lef
        top='nssoc_pump_filter13_rhi140_c'+str(args.size_um)+'_v1';physical.TOP=top;lef.TOP=top
        original_fault=physical.reference_fault
        def capacitor_fault(text,name):
            if name!='wrong_width':return original_fault(text,name)
            lines=text.splitlines(keepends=True);indices=[i for i,l in enumerate(lines) if l.startswith('CD') and ' cap_cmim ' in l]
            assert len(indices)==1;i=indices[0]
            old='w='+str(args.size_um)+'u l='+str(args.size_um)+'u';new='w='+str(args.size_um+1)+'u l='+str(args.size_um)+'u'
            assert lines[i].count(old)==1;lines[i]=lines[i].replace(old,new);return ''.join(lines)
        physical.reference_fault=capacitor_fault
        result['reference_width_fault']='Actual capacitor reference width changed by1um; geometry remains original candidate.';save()
        result['physical']=physical.run(OUT/'layout',OUT/'physical',app);save()
        lef.run(OUT/'layout',OUT/'lef',ROOT/'pdk',app)
        result['lef']=json.loads((OUT/'lef/result.json').read_text())
        assert all(sha(Path(n))==v for n,v in pinned.items())
        assert all(sha(ROOT/n)==v['sha256'] for n,v in manifest['files'].items())
        result['status']='PASS_CANDIDATE_PUMP_NATIVE_DRC_LVS_LEF_NOT_PARENT_OR_ELECTRICAL_ACCEPTANCE'
    except BaseException as e:result.update(status='FAIL_OR_ERROR',error=repr(e));raise
    finally:
        result['inputs']=pinned
        for name in ('physical','lef'):
            q=OUT/name/'result.json'
            if q.exists():result[name]=json.loads(q.read_text())
        result['outputs']={str(p.relative_to(OUT)):sha(p) for p in OUT.rglob('*') if p.is_file() and p!=OUT/'result.json'};save()
if __name__=='__main__':main()
