#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Bind actual native91 divider to all382R649C, retaining failures and explicit physical limits."""
import json,os,re,sys
from pathlib import Path
import compare_cloud_routed_endpoints as reports
import build_pcie_local_vco_hybrid_v6 as compact
import pll_divider_load3p2_intrinsic as intrinsic
import pll_divider_load3p2_compose_model as compose
from cloud_tx_driver_localpins_intrinsic import PDK
from run_cloud_tx_layout_repair import sha,fetch
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'hw/soc/out/cloud-pll-divider-load3p2-compose'
SOURCE=dict(run=38971785699,group='pll-divider-load3p2-rc',head='612bbe0d4c961360aa77541849ed3fb598d532e8',
    summary='f3b8172501491956a3fcee1f5c0505f6e55b60f4d9b61933f79a7a2c17ba7aa3',
    parts='94fcfaaa471e39d9b2009e038f0fd994325d23840e8b84e0ce472d7da95c5041')
def controls(text,verify,out,composed):
    faults=['missing_HBT','wrong_Nx','swap_B_E','body_short','missing_contact','wrong_contact_R','wrong_resistor_L','missing_resistor_ps','missing_MIM','wrong_MIM_width','swap_MIM_planes']
    if composed:faults+=['drop_wire_R','change_wire_R','change_wire_C','move_wire_C','Cref_as_supply','swap_C_B_planes']
    results=[]
    for fault in faults:
        lines=text.splitlines()
        # Select distinct terminals, so every mutation changes real connectivity.
        q=next(i for i,s in enumerate(lines)if ' npn13G2 'in s and s.split()[2]!=s.split()[3])
        tap=next(i for i,s in enumerate(lines)if ' ptap1 'in s)
        rr=next(i for i,s in enumerate(lines)if ' rppd 'in s)
        cap=next(i for i,s in enumerate(lines)if ' cap_cmim 'in s and s.split()[1]!=s.split()[2])
        if fault=='missing_HBT':del lines[q]
        elif fault=='wrong_Nx':
            old=re.search(r'Nx=(\S+)',lines[q])[1];lines[q]=re.sub(r'Nx=\S+','Nx='+str(int(old)+1),lines[q])
        elif fault=='missing_contact':del lines[tap]
        elif fault=='wrong_contact_R':lines[tap]=re.sub(r'R=\S+','R=1',lines[tap])
        elif fault=='wrong_resistor_L':lines[rr]=re.sub(r'l=\S+','l=999u',lines[rr])
        elif fault=='missing_resistor_ps':lines[rr]=re.sub(r' ps=\S+','',lines[rr])
        elif fault=='missing_MIM':del lines[cap]
        elif fault=='wrong_MIM_width':lines[cap]=re.sub(r'w=\S+','w=999u',lines[cap])
        elif fault=='swap_MIM_planes':
            words=lines[cap].split();words[1],words[2]=words[2],words[1];lines[cap]=' '.join(words)
        elif fault=='Cref_as_supply':lines=[s.replace('wire_cref','AVSS')for s in lines]
        elif fault in ['drop_wire_R','change_wire_R','change_wire_C','move_wire_C']:
            index=next(i for i,s in enumerate(lines)if s.startswith('R'if fault.endswith('_R')else 'C'))
            if fault=='drop_wire_R':del lines[index]
            else:
                words=lines[index].split()
                if fault=='move_wire_C':words[1]=next(n for n in compose.PORTS if n not in words[1:3])
                else:words[3]=str(compact.number(words[3])*2)
                lines[index]=' '.join(words)
        else:
            words=lines[q].split()
            if fault=='body_short':words[4]='AVSS'
            elif fault=='swap_C_B_planes':
                assert words[1]!=words[2];words[1],words[2]=words[2],words[1]
            else:words[2],words[3]=words[3],words[2]
            lines[q]=' '.join(words)
        bad='\n'.join(lines)+'\n';assert bad!=text
        (out/(fault+'.spice')).write_text(bad)
        try:verify(bad)
        except AssertionError as error:results.append(dict(fault=fault,rejected=True,reason=str(error)))
        else:raise AssertionError('Accepted actual divider model corruption '+fault)
    assert len(results)==(17 if composed else 11) and all(r['rejected']for r in results)
    return results
def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true';OUT.mkdir(parents=True,exist_ok=False);reports.OUT=OUT
    result=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],source=SOURCE,simulator_checked=False,
        qualified_pex=False,qualified_substrate=False,poly_diffusion_resistance_included=False,
        serial_phy_complete=False,mainchip_integrated=False,qualified_timing=False)
    def save():(OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    save()
    try:
        source=OUT/'source';stem=SOURCE['group']+'-'+str(SOURCE['run'])+'-1'
        base='https://github.com/Melihakbulut221/nssoc/releases/download/cloud-results-'+str(SOURCE['run'])+'-1-'+SOURCE['group']+'/'
        fetch(base+stem+'.summary.json',SOURCE['summary'],OUT/'source-summary.json')
        frozen=json.loads((OUT/'source-summary.json').read_text())
        prior,proof=reports.restore_report(SOURCE['group'],SOURCE['run'],SOURCE['summary'],SOURCE['parts'],source,tuple(frozen['outputs']));result['restore']=proof
        assert prior==frozen and prior['source_head']==SOURCE['head'] and prior['source_unchanged']
        assert prior['status']=='PASS_FRESH_ACTUAL_DIVIDER3P2_WIRE_RC_AND13_RAW_CORRUPTIONS_NOT_COMPOSED_ELECTRICAL_OR_PHY_ACCEPTANCE'
        assert prior['controls']['status']=='PASS_REAL_NATIVE_BASELINE_AND13_RAW_CORRUPTION_CONTROLS'
        assert len(prior['controls']['cases'])==13 and all(c['rejected_by']for c in prior['controls']['cases'])
        app=Path(os.environ['CLOUD_APPIMAGE']);assert sha(app)=='d6a349ec65be11456e96c4981d35f63ca34d3c85daf79a51e1ccb907bb5d7466'
        sys.path.insert(0,str(ROOT/'hw/soc/flow'));from check_pcie_rx_cell import execute
        result['export']=execute([app,'python',ROOT/'scripts/pll_divider_load3p2_native.py',source,OUT],OUT,'export');save()
        assert result['export']['returncode']==0,(OUT/'export.log').read_text()[-12000:]
        native=json.loads((OUT/'native.json').read_text());rows=native['modes']['lvs_flat']['devices']
        models=OUT/'pdk';pins={p:h for p,h in compact.MODEL_PINS.items()if p.endswith(('resistors_mod.lib','sg13g2_hbt_mod.lib','capacitors_mod.lib','sg13g2_tech.json','utility_functions.py'))}
        for path,digest in pins.items():
            target=models/path;target.parent.mkdir(parents=True,exist_ok=True)
            fetch('https://raw.githubusercontent.com/IHP-GmbH/IHP-Open-PDK/'+PDK+'/ihp-sg13g2/'+path,digest,target)
        hbt=(models/'libs.tech/ngspice/models/sg13g2_hbt_mod.lib').read_text(encoding='latin-1')
        res=(models/'libs.tech/ngspice/models/resistors_mod.lib').read_text()
        caps=(models/'libs.tech/ngspice/models/capacitors_mod.lib').read_text()
        assert len(re.findall(r'^\.subckt\s+npn13G2\s+c\s+b\s+e\s+bn\s*$',hbt,re.M|re.I))==1
        assert len(re.findall(r'^\.subckt\s+rppd\s+1\s+2\s+bn\s*$',res,re.M|re.I))==1
        assert len(re.findall(r'^\.subckt\s+cap_cmim\s+PLUS\s+MINUS\s*$',caps,re.M|re.I))==1
        tap=re.search(r'^\.subckt\s+ptap1\s+1\s+2\s*\n(.*?)^\.ends\s+ptap1',res,re.M|re.S|re.I);assert tap
        assert [line.strip()for line in re.findall(r'^R\S+\s+1\s+2\s+R=R\s*$',tap[1],re.M)]==['R1 1 2 R=R']
        tech=json.loads((models/'libs.tech/klayout/python/sg13g2_pycell_lib/sg13g2_tech.json').read_text())['techParams']
        text,bindings=intrinsic.build(rows,tech,compose.INTRINSIC_TOP);model=OUT/'divider91.spice';model.write_text(text)
        result['intrinsic']=intrinsic.verify(model.read_text(),rows,tech,compose.INTRINSIC_TOP);result['intrinsic_bindings']=bindings
        d=OUT/'intrinsic-controls';d.mkdir()
        result['intrinsic_controls']=controls(text,lambda s:intrinsic.verify(s,rows,tech,compose.INTRINSIC_TOP),d,False);save()
        planes=json.loads((source/'anchors03.json').read_text());wire=(source/'rc01/wires.spice').read_text()
        text,expected,wires,mapping,bindings=compose.prepare(text,wire,native,planes,tech)
        model=OUT/'divider91-wire.spice';model.write_text(text)
        result['positive']=compose.verify(model.read_text(),expected,wires,mapping,native,planes)
        result['bindings']=bindings;result['wire_node_map']=mapping
        d=OUT/'composition-controls';d.mkdir()
        result['composition_controls']=controls(text,lambda s:compose.verify(s,expected,wires,mapping,native,planes),d,True)
        assert all(sha(source/n)==v for n,v in prior['outputs'].items()) and all(sha(models/p)==h for p,h in pins.items())
        result.update(status='PASS_NATIVE91_ALL382R649C_DIVIDER_COMPOSITION_WITH28_FAULTS_NOT_ACQUISITION_OR_PHY_ACCEPTANCE',
            model_sha256=sha(model),intrinsic_sha256=sha(OUT/'divider91.spice'),native_sha256=sha(OUT/'native.json'),
            gds_sha256=native['gds_sha256'],native_database_sha256=native['modes']['lvs_flat']['database_sha256'],
            models=dict(commit=PDK,hashes=pins),source_unchanged=True)
    except BaseException as error:result.update(status='FAIL_OR_ERROR',error=repr(error));raise
    finally:
        result['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};save()
if __name__=='__main__':main()
