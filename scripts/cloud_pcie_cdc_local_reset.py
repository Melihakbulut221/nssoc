#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Verify local-only CDC reset distribution without changing timing exceptions."""
import copy,hashlib,json,os,shutil,subprocess,sys,traceback
from pathlib import Path
from check_pcie_integrity_native import LIB_SHA,MODEL_SHA,quote
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'cloud-pcie-cdc-local-reset'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def reset_topology(module):
    cells=module['cells'];ports=module['ports']
    raw=ports['reset_ni']['bits'];assert len(raw)==1
    domains={}
    release_cells=set()
    for name,clock in [('source_release','source_clk_i'),('destination_release','destination_clk_i')]:
        bits=module['netnames'][name]['bits']
        assert len(bits)==2 and len(set(bits))==2
        records=[]
        for bit in bits:
            matches=[(n,c)for n,c in cells.items()if c.get('connections',{}).get('Q')==[bit]]
            assert len(matches)==1,('Release driver missing or ambiguous',name,bit)
            n,c=matches[0];assert c['type']=='sg13g2_dfrbpq_1'
            assert c['connections']['CLK']==ports[clock]['bits'] and c['connections']['RESET_B']==raw
            release_cells.add(n);records.append((n,c))
        assert records[1][1]['connections']['D']==[bits[0]],('Broken release synchronizer',name)
        domains[clock]={'release_q':bits[1],'cells':[n for n,c in records],'functional_registers':[]}
    assert len(release_cells)==4
    for n,c in cells.items():
        if c['type']!='sg13g2_dfrbpq_1':continue
        if n in release_cells:continue
        matches=[clock for clock in domains if c['connections']['CLK']==ports[clock]['bits']]
        assert len(matches)==1,('Functional clock domain mismatch',n)
        d=domains[matches[0]]
        assert c['connections']['RESET_B']==[d['release_q']],('Functional reset bypass or wrong clock domain',n)
        d['functional_registers'].append(n)
    raw_sinks=[]
    for n,c in cells.items():
        for pin,bits in c['connections'].items():
            if c['port_directions'].get(pin)=='input' and raw[0] in bits:
                raw_sinks.append((n,pin))
    assert set(raw_sinks)=={(n,'RESET_B')for n in release_cells},('Raw reset has non-release sinks',raw_sinks)
    assert all(d['functional_registers']for d in domains.values())
    return {'raw_reset_sinks':raw_sinks,'domains':domains,'raw_reset_reaches_only_four_release_flops':True}
def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    OUT.mkdir(exist_ok=False)
    report={'status':'RUNNING','source_head':os.environ['GITHUB_SHA'],'full_phy_accepted':False,
            'final_timing_complete':False,'scope':'RTL event equivalence, functional port simulations and actual IHP mapped reset topology. No SDF, metastability, placement, routed recovery/removal or chip acceptance.'}
    def save():(OUT/'result.json').write_text(json.dumps(report,indent=2)+'\n')
    save()
    try:
        method=ROOT/'scripts/pcie-cdc-local-reset-method.json'
        pins=json.loads(method.read_text())['protected']
        assert all(sha(ROOT/p)==v for p,v in pins.items())
        protected={p:sha(ROOT/p)for p in pins}
        yosys=Path(shutil.which('yosys')).resolve();iverilog=Path(shutil.which('iverilog')).resolve()
        pdk=ROOT/'hw/soc/tools/ihp-native-boot-c4b8b4e/ihp-sg13g2'
        lib=pdk/'libs.ref/sg13g2_stdcell/lib/sg13g2_stdcell_typ_1p20V_25C.lib'
        models=pdk/'libs.ref/sg13g2_stdcell/verilog/sg13g2_stdcell.v'
        assert sha(lib)==LIB_SHA and sha(models)==MODEL_SHA
        report['tools']={str(p):sha(p)for p in [yosys,iverilog,iverilog.with_name('vvp')]}
        report['models']={str(p):sha(p)for p in [lib,models]}
        def run(cmd,name):
            with (OUT/(name+'.log')).open('w')as log:
                code=subprocess.call(list(map(str,cmd)),cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
            report.setdefault('commands',[]).append({'command':list(map(str,cmd)),'code':code,'log':name+'.log'});save()
            if code:print((OUT/(name+'.log')).read_text()[-12000:],flush=True)
            assert code==0,('Actual check failed',name,code)
        run([sys.executable,'-m','pytest','-q','sw/tests/test_pcie_apb_cdc.py','sw/tests/test_pcie_apb_cdc_constraints.py','--junitxml='+str(OUT/'rtl-tests.xml')],'rtl-tests')
        run([sys.executable,ROOT/'scripts/check_pcie_chip_timing_equivalence.py','--kind','cdc','--out',OUT/'equivalence','--yosys',yosys],'equivalence')
        report['equivalence']=json.loads((OUT/'equivalence/result.json').read_text());save()
        run([sys.executable,ROOT/'scripts/check_pcie_apb_cdc_native.py','--out',OUT/'native','--yosys',yosys,'--iverilog-dir',iverilog.parent,'--pdk',pdk],'native')
        native=json.loads((OUT/'native/result.json').read_text())
        assert native['status']=='PASS' and native['inputs_unchanged']
        report['native']=native;save()
        mapped=json.loads((OUT/'native/mapped.json').read_text())['modules']['soc_pcie_apb_cdc']
        report['topology']=reset_topology(mapped);save()
        fixture=ROOT/'sw/tests/fixtures/pcie_chip_timing/pre-local-release-reset-cdc-20261023.v'
        old=OUT/'before-mapped.json'
        recipe='; '.join(['read_liberty -lib '+quote(lib),'read_verilog -sv '+quote(fixture),
            'hierarchy -check -top soc_pcie_apb_cdc','synth -top soc_pcie_apb_cdc -noabc',
            'dfflibmap -liberty '+quote(lib),'abc -liberty '+quote(lib),
            'hilomap -singleton -hicell sg13g2_tiehi L_HI -locell sg13g2_tielo L_LO',
            'clean','check -assert','write_json '+quote(old)])
        (OUT/'before-map.ys').write_text(recipe+'\n')
        run([yosys,'-Q','-T','-s',OUT/'before-map.ys'],'before-map')
        before=json.loads(old.read_text())['modules']['soc_pcie_apb_cdc']
        controls={}
        raw_bad=copy.deepcopy(mapped);cross_bad=copy.deepcopy(mapped)
        domains=report['topology']['domains'];n=domains['source_clk_i']['functional_registers'][0]
        raw_bad['cells'][n]['connections']['RESET_B']=raw_bad['ports']['reset_ni']['bits']
        cross_bad['cells'][n]['connections']['RESET_B']=[domains['destination_clk_i']['release_q']]
        for label,bad in [('actual_before_rtl',before),('raw_reset_bypass',raw_bad),('wrong_domain_release',cross_bad)]:
            try:reset_topology(bad)
            except AssertionError as e:controls[label]={'rejected':True,'reason':repr(e)}
            else:raise AssertionError(('Reset topology fault accepted',label))
        report['topology_controls']=controls
        assert all(sha(ROOT/p)==v for p,v in protected.items())
        report.update(status='PASS_NATIVE_LOCAL_RESET_DISTRIBUTION_REQUIRES_CHIP_REMAP_AND_STA',
                      sources_unchanged=True,source_hashes=protected)
    except BaseException as e:
        report.update(status='FAIL_OR_ERROR',error=repr(e),traceback=traceback.format_exc());raise
    finally:
        report['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'}
        save()
if __name__=='__main__':main()
