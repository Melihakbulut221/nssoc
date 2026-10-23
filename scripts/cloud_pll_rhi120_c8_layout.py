#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Actual RHI120/C8 pump candidate; original gates and native geometry controls."""
import argparse,hashlib,json,os,subprocess,sys,tarfile
from pathlib import Path
from run_cloud_tx_layout_repair import fetch,sha
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'hw/soc/out/cloud-pll-rhi120-c8-layout'
TOP='nssoc_pump_filter13_rhi120_c8_v1'
SOURCES={8: ('pll_pump_filter_hv_rhi120_c8_v1.spice', '88c72dc6de79d598548e3eba833f832bf02501c126f75e2f2e9435fcd207fc55')}
ORIGINAL_SHA='f1ac5a165fdc8160d6ad2588a6da87d62a4314cc7ce67e7bc4bac0ed6ccd31d7'
def generate(size):
    assert size==8
    sys.path.insert(0,str(ROOT/'hw/soc/flow'))
    import make_pcie_pump_filter13_v1 as base
    source_dir=ROOT/'hw/soc/analog/pcie'
    name,digest=SOURCES[size]
    reference=source_dir/'pll_pump_filter_hv_rhi140_c8_v1.spice'
    assert sha(reference)==ORIGINAL_SHA
    cp='pll_pfd_charge_pump_hv_v1.spice';assert sha(source_dir/cp)==base.SOURCES[cp]
    assert sha(source_dir/name)==digest
    def rows(text):
        d=base.definitions({'filter':text,cp:(source_dir/cp).read_text()})
        result,wires=base.expand(d,['nssoc_tail115_pump_filter13_v1','xloop',base.PORTS])
        assert not wires and len(result)==13
        return result
    before=rows(reference.read_text());expected=json.loads(json.dumps(before))
    rhi=[r for r in expected if r['path']=='xloop.xrhi']
    assert len(rhi)==1 and rhi[0]['model']=='rppd' and rhi[0]['nets']==['vco_avdd','vctrl','sub']
    assert rhi[0]['params']=={'w':'1u','l':'140u','b':'0','sw_et':'1'}
    rhi[0]['params']['l']='120u'
    candidate_text=(source_dir/name).read_text()
    candidate=rows(candidate_text);assert candidate==expected and candidate!=before
    rejected=[]
    for label,bad in [
        ('unchanged',reference.read_text()),
        ('wrong_rhi',candidate_text.replace('l=120u','l=100u')),
        ('changed_rlo',candidate_text.replace('l=47u','l=48u')),
        ('changed_cap',candidate_text.replace('w=8u l=8u','w=9u l=8u')),
        ('wrong_supply',candidate_text.replace('XRHI vco_avdd vctrl','XRHI div_avdd vctrl'))]:
        assert rows(bad)!=expected,label
        rejected.append(label)
    base.TOP=TOP;base.SOURCES={name:digest,cp:base.SOURCES[cp]}
    base.build(ROOT/'pdk',OUT/'layout')
    p=OUT/'layout/result.json';r=json.loads(p.read_text())
    assert len(r['core_devices'])==13 and r['substrate_contacts']==13 and r['well_contacts']==4
    actual=[{k:row[k]for k in ('path','model','nets','params')}for row in r['core_devices']]
    assert actual==expected
    r['inputs'][str(Path(__file__).resolve())]=sha(Path(__file__).resolve())
    r['inputs'][str(reference)]=sha(reference)
    r['exact_core_delta']=dict(path='xloop.xrhi',old_length_um=140,new_length_um=120,
        unchanged_width_um=1,unchanged_capacitor_um=[8,8],other12core_devices_unchanged=True,
        source_negative_controls_rejected=rejected,actual_native_pcell_parameters_checked=True)
    r['closed_loop_accepted']=False
    p.write_text(json.dumps(r,indent=2)+'\n')
def main():
    p=argparse.ArgumentParser();p.add_argument('--size-um',type=int,choices=(8,),required=True);p.add_argument('--generate',action='store_true');args=p.parse_args()
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    if args.generate:generate(args.size_um);return
    OUT.mkdir(parents=True,exist_ok=False)
    result=dict(status='RUNNING',rhi_length_um=120,size_um=args.size_um,source_head=os.environ['GITHUB_SHA'],accepted=False,parent_integrated=False,qualified_pex=False,serial_phy_complete=False,main_chip_integrated=False,
        scope='Real13core+17contact pump macro with native PCell RHI length120um and unchanged8um MIM. Full native DRC/deep and flat30device LVS/geometry and reference fault controls/LEF checks. Not new parent wiring, fresh RC or electrical acceptance.')
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
        top=TOP;physical.TOP=top;lef.TOP=top
        original_fault=physical.reference_fault
        def resistor_fault(text,name):
            if name!='wrong_width':return original_fault(text,name)
            lines=text.splitlines(keepends=True)
            indices=[i for i,l in enumerate(lines)if l.startswith('RD')and ' rppd 'in l and 'w=1u l=120u'in l]
            assert len(indices)==1;i=indices[0]
            lines[i]=lines[i].replace('w=1u l=120u','w=1u l=140u')
            return ''.join(lines)
        physical.reference_fault=resistor_fault
        result['reference_length_fault']='RHI reference length140um against actual120um geometry; all other reference records unchanged.';save()
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
