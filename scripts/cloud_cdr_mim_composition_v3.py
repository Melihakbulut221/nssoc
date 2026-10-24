#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Compose PD394 with audited MIM-aware wires and exactly one model per native cap."""
import hashlib,importlib.util,json,os
from collections import Counter
from pathlib import Path
import compare_cloud_routed_endpoints as reports
import build_pcie_local_vco_hybrid_v6 as parser
from run_cloud_tx_layout_repair import sha
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'hw/soc/out/cloud-cdr-mim-composition-v3'
BASE_METHOD_SHA='c87d213c8676f58d989fc85c91b0408d5c1581cd69f14f96d96ed2e986d299a8'
def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true';OUT.mkdir(parents=True,exist_ok=False);reports.OUT=OUT
    r=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],qualified_pex=False,loaded_simulation_passed=False,closed_loop=False,full_phy_accepted=False)
    def save():(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
    save()
    try:
        pin=json.loads((ROOT/'docs/evidence/cdr-mim-parent-audit-v3-pass-20261018.json').read_text())
        selected=['capture/wire/anchors08.json','capture/wire/rc03/wires.spice','capture/wire/mim-audit.json','capture/source/wire/native05/result.json','capture/native-binding.json','capture/result.json']
        prior,proof=reports.restore_report('cdr-mim-parent-audit-v3',pin['run'],pin['summary_sha256'],pin['parts_sha256'],OUT/'audit',selected)
        assert prior==pin['report']and prior['sources_unchanged']and len(prior['intrinsic_controls'])==9 and len(prior['wire_controls']['cases'])==13;r['audited_source']=proof
        assert prior['audit']['actual_exported_resistors']==9979 and prior['audit']['actual_exported_capacitors']==7761 and prior['audit']['native_mim_intrinsic']['devices']==11
        bp=json.loads((ROOT/'docs/evidence/cdr-retimed-binding-v3-pass-20261018.json').read_text());names=['binding.json','pd394-compact.spice','native-devices.json']
        bound,bproof=reports.restore_report('cdr-retimed-binding-v3',bp['run'],bp['summary_sha256'],bp['parts_sha256'],OUT/'binding',names)
        assert bound==bp['report']and bound['sources_unchanged'];r['model_source']=bproof
        assert prior['intrinsic_binding_source']['summary_sha256']==bp['summary_sha256'] and prior['intrinsic_binding_source']['run']==bp['run']
        source=ROOT/'scripts/cloud_cdr_retimed_composition.py';assert sha(source)==BASE_METHOD_SHA
        text=source.read_text();changes=[]
        for a,b in [('nssoc_cdr_pd394_wire_v1','nssoc_cdr_pd394_mim_wire_v3'),('8933','9979'),('7649','7761'),('16582','17740')]:
            count=text.count(a);assert count>0;text=text.replace(a,b);changes.append(dict(before=a,after=b,count=count))
        methods=OUT/'methods';methods.mkdir();target=methods/'compose.py';target.write_text(text)
        spec=importlib.util.spec_from_file_location('pd394_mim_assembly',target);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
        binding=json.loads((OUT/'binding/binding.json').read_text());assert binding==bound['binding']
        base=OUT/'audit/capture';anchors=json.loads((base/'wire/anchors08.json').read_text());geometry=json.loads((base/'source/wire/native05/result.json').read_text());capture=json.loads((base/'result.json').read_text())
        assert capture['sources_unchanged']and capture['intrinsic_capture_binding']['R']==9979 and capture['intrinsic_capture_binding']['C']==7761
        native_text=(base/'wire/rc03/wires.spice').read_text();rows=parser.statements(native_text)
        devices=[row for row in rows[1:-1]if row[0].startswith('X')]
        expected=capture['intrinsic_capture_binding']['native_mim_devices'];assert len(devices)==len(expected)==11
        assert Counter(map(tuple,devices))==Counter(tuple(x['export'])for x in expected)
        assert {x['native_id']for x in expected}=={d['native_id']for d in binding['devices']if d['model']=='cap_cmim'}
        for d in expected:
            model=next(x for x in binding['devices']if x['native_id']==d['native_id']);params=dict(x.split('=')for x in d['export'][4:])
            assert model['model']=='cap_cmim'and all(parser.number(params[k])==parser.number(model['parameters'][k])for k in ('w','l'))
        # Project only the independently matched eleven device cards. Every raw
        # R/C token and reference plane survives; the intrinsic devices are emitted
        # once from the original native PD model binding, never added twice.
        projected=[row for row in rows if not row[0].startswith('X')]
        assert Counter(tuple(row)for row in projected[1:-1])==Counter(tuple(row)for row in rows[1:-1]if row[0].startswith(('R','C')))
        wiretext='\n'.join(' '.join(row)for row in projected)+'\n';(OUT/'verified-wire-projection.spice').write_text(wiretext)
        output,contract=m.assemble(binding,anchors,geometry,wiretext);m.verify(output,binding,anchors,geometry,wiretext)
        r['controls']=m.faults(output,binding,anchors,geometry,wiretext)
        source_rows=parser.statements(output);cap=next(row for row in source_rows if 'cap_cmim'in row)
        for label,extra in [('duplicate_bound_mim',[cap[0]+'_DUPLICATE',*cap[1:]]),('retained_extractor_mim',devices[0])]:
            mutated='\n'.join(' '.join(x)for x in [*source_rows[:-1],extra,source_rows[-1]])+'\n'
            try:m.verify(mutated,binding,anchors,geometry,wiretext)
            except (AssertionError,ValueError):r['controls'].append(dict(name=label,rejected=True,sha256=hashlib.sha256(mutated.encode()).hexdigest(),extra_card=extra))
            else:raise AssertionError('Accepted '+label)
        assert len(r['controls'])==15 and contract['counts']==dict(devices=394,R=9979,C=7761)
        assert len([row for row in parser.statements(output)if 'cap_cmim'in row])==11
        contract.update(native_extracted_mim_cards_projected_once=expected,intrinsic_mim_models_in_final_netlist=11,explicit_mim_device_estimate_double_count_removed=True,all_raw_wire_tokens_preserved=True,qualified_pex=False)
        (OUT/'pd394-mim-wire.spice').write_text(output);(OUT/'composition.json').write_text(json.dumps(contract,indent=2)+'\n')
        r['composition']=contract;r['method']=dict(original_sha256=BASE_METHOD_SHA,adapted_sha256=sha(target),changes=changes)
        assert all(sha(OUT/'audit'/n)==prior['outputs'][n]for n in selected)and all(sha(OUT/'binding'/n)==bound['outputs'][n]for n in names)and sha(source)==BASE_METHOD_SHA
        r['sources_unchanged']=True;r['status']='PASS_PD394_MIM_AWARE_COMPOSITION_AND15_CONTROLS_REQUIRES_LOADED_NATIVE_WAVES'
    except BaseException as e:r.update(status='FAIL_OR_ERROR',error=repr(e));raise
    finally:
        r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};save()
if __name__=='__main__':main()
