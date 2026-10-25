#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Compose actual native v50 devices with every audited physical wire R/C."""
import copy,hashlib,importlib.util,io,json,os,tokenize,traceback
from collections import Counter
from pathlib import Path
import compare_cloud_routed_endpoints as reports
import build_pcie_local_vco_hybrid_v6 as parser
from run_cloud_tx_layout_repair import sha
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'hw/soc/out/cloud-cdr-active-levelshift-v50-composition'
def check():
    m=json.loads((ROOT/'scripts/cdr-active-levelshift-v50-composition-method.json').read_text())
    for p,h in m['protected'].items():assert sha(ROOT/p)==h,p
def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true';check()
    OUT.mkdir(parents=True,exist_ok=False);reports.OUT=OUT
    r=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],qualified_pex=False,loaded_simulation_passed=False,
           closed_loop=False,full_phy_accepted=False,main_chip_integrated=False,
           scope='Exact native18device+53R+93C physical leaf composition with50intrinsic terminals/40actual points/8external pins plus explicit extractor reference. Finite body contacts retained; no ideal body/supply aliases. Not loaded waveform,parent bias integration or full PHY acceptance.')
    def save():(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
    save()
    try:
        pin=json.loads((ROOT/'docs/evidence/cdr-active-levelshift-v50-rc-pass-20261024.json').read_text())
        selected=['wire/anchors08.json','wire/native05/result.json','wire/rc03/wires.spice','wire/audit.json','wire/native-mutations01.json']
        rc,rcproof=reports.restore_report('cdr-active-levelshift-v50-rc',pin['run'],pin['summary_sha256'],pin['parts_sha256'],OUT/'rc',selected)
        assert rc==pin['report'] and rc['sources_unchanged'] and rc['audit']['status']=='PASS_WIRE_GRAPH_AND_COLLAPSED_C_ONLY'
        assert rc['audit']['actual_exported_resistors']==53 and rc['audit']['actual_exported_capacitors']==93
        assert rc['controls']['status']=='PASS_REAL_NATIVE_BASELINE_AND14_RAW_CORRUPTION_CONTROLS' and len(rc['controls']['cases'])==14
        r['rc_source']=rcproof
        bp=json.loads((ROOT/'docs/evidence/cdr-active-levelshift-v50-binding-pass-20261024.json').read_text())
        names=['binding.json','levelshift18-compact.spice','native-devices.json']
        prior,bproof=reports.restore_report('cdr-active-levelshift-v50-binding',bp['run'],bp['summary_sha256'],bp['parts_sha256'],OUT/'binding',names)
        assert prior==bp['report'] and prior['sources_unchanged'] and len(prior['controls'])==9
        assert prior['physical_source']['summary_sha256']==rc['physical_inputs']['summary_sha256']
        r['binding_source']=bproof
        source=ROOT/'scripts/cloud_cdr_retimed_composition.py';original=source.read_text()
        text=original[original.index('def assemble('):original.index('\ndef main():')]
        replacements={'394':'18','1134':'50','776':'40','751':'32','383':'18','111':'9','25':'8','26':'9','8933':'53','7649':'93'}
        counts=Counter();tokens=[]
        for tok in tokenize.generate_tokens(io.StringIO(text).readline):
            if tok.type==tokenize.NUMBER and tok.string in replacements:
                counts[tok.string]+=1;tok=tok._replace(string=replacements[tok.string])
            tokens.append(tok)
        assert set(counts)==set(replacements)
        text=tokenize.untokenize(tokens);changes=[]
        for old,new in [
            ("cases=('missing_mim','wrong_mim_width','swapped_mim_plates','missing_contact',","cases=('missing_contact',"),
            ('assert len(result)==13','assert len(result)==10'),
            ("['R_ALIAS','dp','dn','1']","['R_ALIAS','ip','inn','1']"),
            ('Native394 devices + all8933R/7649C. MIM separation/RF/body PEX NOT qualified.','Native18 devices + all53R/93C. RF/body PEX NOT qualified.')]:
            assert text.count(old)==1,(old,text.count(old));text=text.replace(old,new);changes.append(dict(before=old,after=new))
        text="import copy,difflib,hashlib,json\nfrom collections import Counter\nimport build_pcie_local_vco_hybrid_v6 as parser\nMODEL='nssoc_cdr_active_levelshift_v50_wire'\n"+text
        methods=OUT/'methods';methods.mkdir();target=methods/'compose.py';target.write_text(text)
        spec=importlib.util.spec_from_file_location('v50_native_wire_composer',target);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
        binding=json.loads((OUT/'binding/binding.json').read_text());assert binding==prior['binding']
        anchors=json.loads((OUT/'rc/wire/anchors08.json').read_text());geometry=json.loads((OUT/'rc/wire/native05/result.json').read_text())
        assert anchors==rc['anchors'] and geometry==rc['geometry']
        wiretext=(OUT/'rc/wire/rc03/wires.spice').read_text()
        output,contract=m.assemble(binding,anchors,geometry,wiretext);m.verify(output,binding,anchors,geometry,wiretext)
        r['controls']=m.faults(output,binding,anchors,geometry,wiretext)
        original_rows=parser.statements(output)
        for label in ('missing_mos','wrong_mos_width','swapped_mos_gate_source','mos_body_short'):
            rows=copy.deepcopy(original_rows);i=next(i for i,row in enumerate(rows)if 'sg13_lv_nmos'in row)
            if label=='missing_mos':del rows[i]
            elif label=='wrong_mos_width':
                k=next(k for k,x in enumerate(rows[i])if x.startswith('w='));rows[i][k]='w=999u'
            elif label=='swapped_mos_gate_source':
                assert rows[i][2]!=rows[i][3];rows[i][2],rows[i][3]=rows[i][3],rows[i][2]
            else:
                assert rows[i][4]!=rows[i][3];rows[i][4]=rows[i][3]
            mutant='\n'.join(' '.join(row)for row in rows)+'\n'
            try:m.verify(mutant,binding,anchors,geometry,wiretext)
            except (AssertionError,ValueError):r['controls'].append(dict(name=label,rejected=True,sha256=hashlib.sha256(mutant.encode()).hexdigest()))
            else:raise AssertionError('Accepted '+label)
        assert len(r['controls'])==14 and contract['counts']==dict(devices=18,R=53,C=93)
        assert Counter(d['model']for d in contract['device_records'])==dict(npn13g2=2,sg13_lv_nmos=3,rppd=4,ptap1=9)
        contract.update(all_raw_wire_values_and_topology_preserved=True,intrinsic_device_models_emitted_once=True,native_mim_absent=True,qualified_pex=False)
        (OUT/'levelshift18-wire.spice').write_text(output);(OUT/'composition.json').write_text(json.dumps(contract,indent=2)+'\n')
        r['composition']=contract;r['method']=dict(original_sha256=sha(source),adapted_sha256=sha(target),numeric_census_changes=dict(counts),map=replacements,changes=changes)
        assert all(sha(OUT/'rc'/n)==rc['outputs'][n]for n in selected)
        assert all(sha(OUT/'binding'/n)==prior['outputs'][n]for n in names)
        check()
        r.update(status='PASS_V50_LEAF18_ALL146_WIRE_ELEMENTS_AND14_COMPOSITION_CONTROLS_REQUIRES_LOADED_NATIVE_WAVES',sources_unchanged=True)
    except BaseException as e:r.update(status='FAIL_OR_ERROR',error=repr(e),traceback=traceback.format_exc());raise
    finally:
        r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'}
        save()
if __name__=='__main__':main()
