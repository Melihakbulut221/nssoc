#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""c5r3k PLL child macros: native generation, strict DRC/LVS and fault controls.

One macro per invocation:
  pump        nssoc_pump_filter13_c5r3k_v1 (XPSOURCE W6.4 -> 8 um)
  vco         nssoc_clock_vco_hbt_v6_c5r3k_v1_layout (six ring loads L4.4 -> 4.93 um)
  div1        nssoc_clock_div4_load3p2_c5r3k_v1_layout (first-divider XSP/XSN W4 -> 16 um)
  integrator  nssoc_pll_vctrl_integrator_c5r3k_v1 (rppd W2 L23 + cmim 57.7 um)
Each macro runs the frozen checker of the macro it derives from, with the
macro name and source pointed at the c5r3k files and one extra reference fault
that reverts the c5r3k change. No parent integration, RC or acquisition claim.
"""
import argparse,json,os,subprocess,sys,tarfile
from pathlib import Path
from run_cloud_tx_layout_repair import fetch,sha
ROOT=Path(__file__).resolve().parents[1];FLOW=ROOT/'hw/soc/flow'
OUT=ROOT/'hw/soc/out/cloud-pll-c5r3k-children'
GENERATORS={'pump':'make_pcie_pump_filter13_c5r3k_v1.py','vco':'make_pcie_clock_vco_v6_c5r3k_v1.py',
    'div1':'make_pcie_clock_div4_load3p2_c5r3k_v1.py','integrator':'make_pcie_pll_integrator_c5r3k_v1.py'}
SOURCES={'pump':['pll_pump_filter_hv_c5r3k_v1.spice'],'vco':['clock_vco_hbt_v6_c5r3k_v1.spice'],
    'div1':['clock_div2_conditioned_hbt_c5r3k_v1.spice'],'integrator':['pll_vctrl_integrator_c5r3k_v1.spice']}
CHECKERS={'pump':['check_pcie_pump_filter13_v1.py','check_pcie_pump_filter13_lef.py','make_pcie_pump_filter13_v1.py'],
    'vco':['check_pcie_clock_vco_v6_local_v1.py','make_pcie_clock_vco_v6_local_v1.py'],
    'div1':['check_pcie_clock_div4_load3p2_v2.py','make_pcie_clock_div4_load3p2_v2.py'],
    'integrator':['check_pcie_pll_integrator_c5r3k_v1.py','check_pcie_pump_filter13_v1.py','make_pcie_pump_filter13_v1.py']}

def bind_fault(module,name,old,new):
    """Add one reference fault that reverts the c5r3k change; others unchanged."""
    original=module.fault_reference
    def fault_reference(text,fault):
        if fault!=name:return original(text,fault)
        if text.count(old)!=1:raise ValueError('Reference fault must bind exactly once: '+name)
        return text.replace(old,new)
    module.fault_reference=fault_reference

def check(macro,app,result):
    sys.path.insert(0,str(FLOW));layout=OUT/'layout';pdk=ROOT/'pdk'
    if macro=='pump':
        import make_pcie_pump_filter13_c5r3k_v1 as variant
        import check_pcie_pump_filter13_v1 as physical
        import check_pcie_pump_filter13_lef as lef
        variant.configure(physical,lef)
        original=physical.reference_fault
        def reference_fault(text,name):
            # Replace the generic width fault by the c5r3k revert: an 8 um
            # XPSOURCE layout against a 6.4 um reference must be rejected.
            if name!='wrong_width':return original(text,name)
            lines=text.splitlines(keepends=True);i=[k for k,l in enumerate(lines)if l.startswith('MD4 ')]
            assert len(i)==1 and lines[i[0]].count(' sg13_hv_pmos w=8u l=2u ')==1
            lines[i[0]]=lines[i[0]].replace(' w=8u l=2u ',' w=6.4u l=2u ');return ''.join(lines)
        physical.reference_fault=reference_fault
        result['reference_width_fault']='XPSOURCE reference width 6.4um against actual 8um geometry'
        result['physical']=physical.run(layout,OUT/'physical',app)
        lef.run(layout,OUT/'lef',pdk,app);result['lef']=json.loads((OUT/'lef/result.json').read_text())
        return 'PASS_NATIVE_PUMP_FILTER_DRC_LVS_AND_FAULT_CONTROLS' if result['physical']['status']=='PASS_NATIVE_PUMP_FILTER_DRC_LVS_AND_FAULT_CONTROLS' else None
    if macro=='vco':
        import make_pcie_clock_vco_v6_c5r3k_v1 as variant
        import check_pcie_clock_vco_v6_local_v1 as checker
        variant.configure(checker)
        # The frozen wrong_load fault names L4.4; bind it to the c5r3k L4.93.
        bind_fault(checker,'wrong_load','RRP0 AVDD P0 BULK rppd w=8u l=4.93u','RRP0 AVDD P0 BULK rppd w=8u l=4.4u')
        fixed=ROOT/'hw/soc/tools/physical/librelane-3.0.5-x86_64.AppImage'
        if not fixed.exists():fixed.parent.mkdir(parents=True,exist_ok=True);fixed.symlink_to(app)
        assert sha(fixed)==sha(app)
        sys.argv=['check','--layout',str(layout),'--pdk',str(pdk),'--out',str(OUT/'check')];checker.main()
    elif macro=='div1':
        import make_pcie_clock_div4_load3p2_c5r3k_v1 as variant
        import check_pcie_clock_div4_load3p2_v2 as checker
        variant.configure(checker)
        checker.REFERENCE_FAULTS=(*checker.REFERENCE_FAULTS,'conditioner_series_reverted')
        bind_fault(checker,'conditioner_series_reverted',
            'RDIV__XFIRST__XSP CLKP DIV__XFIRST__CKP BULK rppd w=16u l=3.6u',
            'RDIV__XFIRST__XSP CLKP DIV__XFIRST__CKP BULK rppd w=4u l=3.6u')
        sys.argv=['check','--layout',str(layout),'--pdk',str(pdk),'--out',str(OUT/'check')];checker.main()
    else:
        import check_pcie_pll_integrator_c5r3k_v1 as checker
        return checker.run(layout,OUT/'check',app)['status']
    return json.loads((OUT/'check/result.json').read_text())['status']

def main():
    p=argparse.ArgumentParser();p.add_argument('--macro',choices=sorted(GENERATORS),required=True);args=p.parse_args();macro=args.macro
    assert os.environ.get('GITHUB_ACTIONS')=='true';OUT.mkdir(parents=True,exist_ok=False)
    r=dict(status='RUNNING',macro=macro,source_head=os.environ['GITHUB_SHA'],accepted=False,parent_integrated=False,qualified_pex=False,
        closed_loop_accepted=False,serial_phy_complete=False,main_chip_integrated=False,
        scope='Standalone c5r3k child macro: native PCell generation, main DRC, deep and flat LVS, frozen fault controls plus one c5r3k revert fault. No parent wiring, RC, acquisition or PVT acceptance.')
    def save():(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
    protected=[Path(__file__).resolve(),FLOW/GENERATORS[macro],*[FLOW/n for n in CHECKERS[macro]],*[ROOT/'hw/soc/analog/pcie'/n for n in SOURCES[macro]]]
    pinned={str(q):sha(q)for q in protected};save()
    try:
        sys.path.insert(0,str(FLOW))
        variant=__import__(GENERATORS[macro][:-3])
        if hasattr(variant,'exact_delta'):r['exact_delta']=variant.exact_delta(ROOT);save()
        spec=json.loads((ROOT/'docs/evidence/pcie-tx-layout-cloud-input-20261013.json').read_text())
        packed=OUT/'restore.tar.gz';fetch(spec['receipt']['url'],spec['receipt']['sha256'],packed)
        assert packed.stat().st_size==spec['receipt']['bytes']
        with tarfile.open(packed)as tar:tar.extractall(ROOT,filter='data')
        packed.unlink();manifest=json.loads((ROOT/'manifest.json').read_text())
        assert all(sha(ROOT/n)==v['sha256']for n,v in manifest['files'].items())
        from run_cloud_pll_filter_lef import restore_technology
        tech=restore_technology();pinned[str(tech)]=sha(tech)
        app=Path(os.environ['CLOUD_APPIMAGE']);assert sha(app)==spec['runtime_sha256']
        r['runtime_sha256']=sha(app);r['input_bundle']=spec['receipt'];save()
        if macro=='div1':os.sched_setaffinity(0,{min(os.sched_getaffinity(0))})
        with (OUT/'generate.log').open('w')as log:
            rc=subprocess.call([str(app),'python',str(FLOW/GENERATORS[macro]),'--pdk',str(ROOT/'pdk'),'--out',str(OUT/'layout')],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
        if rc:print((OUT/'generate.log').read_text(errors='replace')[-12000:],flush=True)
        assert rc==0,'Native generation failed'
        r['layout']=json.loads((OUT/'layout/result.json').read_text());save()
        status=check(macro,app,r);r['check_status']=status;save()
        assert status and status.startswith('PASS'),status
        assert all(sha(Path(n))==v for n,v in pinned.items())
        assert all(sha(ROOT/n)==v['sha256']for n,v in manifest['files'].items())
        r['status']='PASS_C5R3K_CHILD_NATIVE_DRC_LVS_FAULTS_NOT_PARENT_OR_ELECTRICAL_ACCEPTANCE'
    except BaseException as e:r.update(status='FAIL_OR_ERROR',error=repr(e));raise
    finally:
        r['inputs']=pinned
        for name in ('physical','lef','check'):
            q=OUT/name/'result.json'
            if q.exists():r[name]=json.loads(q.read_text())
        r['outputs']={str(q.relative_to(OUT)):sha(q)for q in OUT.rglob('*')if q.is_file()and q!=OUT/'result.json'};save()
if __name__=='__main__':main()
