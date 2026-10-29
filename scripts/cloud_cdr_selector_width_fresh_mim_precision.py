#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Fresh PD500 MIM-aware extraction in both precise native orders and composition."""
import copy,hashlib,importlib.util,json,os,shlex,subprocess,sys
from collections import Counter
from decimal import Decimal
from pathlib import Path
import build_pcie_local_vco_hybrid_v6 as parser
import tx_native_cap_order as cap_order
import cdr_selector_width_fresh_rc_legacy as admission
from cdr_v59_mim_composition_derivation import derive as derive_composition,controls as count_controls
from run_cloud_tx_layout_repair import sha
ROOT=Path(__file__).resolve().parents[1]
OUT=admission.MIM_OUT
MODEL='nssoc_cdr_pd500_resistor_mim_wire_v59'
def check():
    return admission.methods()

def records(path):
    result=Counter()
    for row in parser.statements(path.read_text())[1:-1]:
        assert row[0].startswith(('R','C','X'))
        key=tuple(row)if row[0][0]in ('R','X')else ('C',*sorted(row[1:3]),Decimal(row[3]))
        result[key]+=1
    return result

def compose(cap,audit):
    base=OUT/'precise';binding=json.loads((base/'model-binding/binding.json').read_text())
    pin=admission.binding_pin()
    assert binding==pin['report']['binding']and cap['model_binding_source']['summary_sha256']==pin['summary_sha256']
    assert audit['intrinsic_binding_source']['summary_sha256']==pin['summary_sha256']
    anchors=json.loads((base/'wire/anchors08.json').read_text());geometry=json.loads((base/'source/wire/native05/result.json').read_text())
    rows=parser.statements((base/'wire/rc03/wires.spice').read_text());devices=[x for x in rows[1:-1]if x[0].startswith('X')]
    expected=cap['intrinsic_capture_binding']['native_mim_devices']
    assert len(devices)==len(expected)==7 and Counter(map(tuple,devices))==Counter(tuple(d['export'])for d in expected)
    assert {d['native_id']for d in expected}=={d['native_id']for d in binding['devices']if d['model']=='cap_cmim'}
    for d in expected:
        model=next(x for x in binding['devices']if x['native_id']==d['native_id']);params=dict(x.split('=')for x in d['export'][4:])
        assert model['model']=='cap_cmim'and all(parser.number(params[k])==parser.number(model['parameters'][k])for k in ('w','l'))
    projected=[row for row in rows if not row[0].startswith('X')]
    assert Counter(tuple(row)for row in projected[1:-1])==Counter(tuple(row)for row in rows[1:-1]if row[0].startswith(('R','C')))
    wiretext='\n'.join(' '.join(row)for row in projected)+'\n'
    destination=OUT/'composition';destination.mkdir();(destination/'verified-wire-projection.spice').write_text(wiretext)
    source=ROOT/'scripts/cloud_cdr_retimed_composition.py';assert sha(source)=='c87d213c8676f58d989fc85c91b0408d5c1581cd69f14f96d96ed2e986d299a8'
    text=source.read_text();changes=[];nr=audit['audit']['actual_exported_resistors'];nc=audit['audit']['actual_exported_capacitors']
    assert nr==cap['intrinsic_capture_binding']['R']and nc==cap['intrinsic_capture_binding']['C']and min(nr,nc)>0
    text,count_derivation=derive_composition(text,nr,nc)
    changes=count_derivation['records']
    method=destination/'compose.py';method.write_text(text)
    spec=importlib.util.spec_from_file_location('fresh_pd500_composition',method);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    output,contract=m.assemble(binding,anchors,geometry,wiretext);m.verify(output,binding,anchors,geometry,wiretext)
    controls=m.faults(output,binding,anchors,geometry,wiretext);outputrows=parser.statements(output);caprow=next(row for row in outputrows if 'cap_cmim'in row)
    for label,extra in [('duplicate_bound_mim',[caprow[0]+'_DUPLICATE',*caprow[1:]]),('retained_extractor_mim',devices[0])]:
        changed='\n'.join(' '.join(x)for x in [*outputrows[:-1],extra,outputrows[-1]])+'\n'
        try:m.verify(changed,binding,anchors,geometry,wiretext)
        except (AssertionError,ValueError):controls.append(dict(name=label,rejected=True))
        else:raise AssertionError('Accepted '+label)
    for label in ('missing_mos','wrong_mos_width','swapped_mos_gate_source','mos_body_short','rounded_gain_mos_width','old_gain_mos_width'):
        changed=copy.deepcopy(outputrows)
        target=next(d for d in binding['devices']if d['model']=='sg13_lv_nmos'and (not label.endswith('gain_mos_width')or parser.number(d['parameters']['w'])==Decimal('53.335e-6')))
        index=next(i for i,row in enumerate(changed)if row[0]==target['instance']);row=changed[index]
        if label=='missing_mos':del changed[index]
        elif label in ('wrong_mos_width','rounded_gain_mos_width','old_gain_mos_width'):
            i=next(i for i,x in enumerate(row)if x.startswith('w='));row[i]='w='+dict(wrong_mos_width='999u',rounded_gain_mos_width='53.33u',old_gain_mos_width='36u')[label]
        elif label=='swapped_mos_gate_source':assert row[2]!=row[3];row[2],row[3]=row[3],row[2]
        else:assert row[4]!=row[3];row[4]=row[3]
        mutant='\n'.join(' '.join(row)for row in changed)+'\n'
        try:m.verify(mutant,binding,anchors,geometry,wiretext)
        except (AssertionError,ValueError):controls.append(dict(name=label,rejected=True))
        else:raise AssertionError('Accepted '+label)
    assert len(controls)==21 and all(c['rejected']for c in controls)
    assert contract['counts']==dict(devices=500,R=nr,C=nc)and sum('cap_cmim'in row for row in parser.statements(output))==7
    contract.update(native_extracted_mim_cards_projected_once=expected,intrinsic_mim_models_in_final_netlist=7,explicit_mim_device_estimate_double_count_removed=True,all_raw_wire_tokens_preserved=True,qualified_pex=False)
    (destination/'pd500-mim-wire.spice').write_text(output);(destination/'composition.json').write_text(json.dumps(contract,indent=2)+'\n')
    return dict(status='PASS_PD500_FRESH_MIM_COMPOSITION_AND21_CONTROLS_REQUIRES_LOADED_WAVES',contract=contract,controls=controls,method=dict(original_sha256=sha(source),adapted_sha256=sha(method),changes=changes),binding_summary_sha256=pin['summary_sha256'],non_cascading_count_derivation=count_derivation)

def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true'and os.environ['GITHUB_RUN_ATTEMPT']=='1';admission.authorize();check();OUT.mkdir(parents=True,exist_ok=False)
    result=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],qualified_pex=False,full_phy_accepted=False,closed_loop=False,loaded_simulation_passed=False,variants={})
    def save():(OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    def run(command,label,env=None):
        path=OUT/(label+'.log')
        with path.open('w')as log:code=subprocess.call(list(map(str,command)),cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT)
        result.setdefault('commands',[]).append(dict(label=label,returncode=code,sha256=sha(path)));save()
        if code:print(path.read_text(errors='replace')[-18000:],flush=True)
        assert code==0,(label,code)
    save()
    try:
        result['current_input_restoration']=admission.restore_inputs()
        result['count_derivation_controls']=count_controls((ROOT/'scripts/cloud_cdr_retimed_composition.py').read_text())
        result['order_controls']=cap_order.controls();run([sys.executable,ROOT/'scripts/tx_reverse_native_cap_order.py','--controls'],'reverse-order-controls')
        for variant in ('precise','precise_reversed'):
            env=dict(os.environ,CDR500_CAPTURE_VARIANT=variant)
            run([sys.executable,admission.derived('capture')],variant+'-capture',env)
            cap_path=OUT/variant/'result.json';cap=json.loads(cap_path.read_text());cap_sha=sha(cap_path)
            run([sys.executable,admission.derived('audit')],variant+'-audit',env)
            audit=json.loads((OUT/variant/'audit-stage/result.json').read_text())
            assert sha(cap_path)==cap_sha and cap['sources_unchanged']and audit['sources_unchanged']
            assert len(audit['wire_controls']['cases'])==13 and len(audit['intrinsic_controls'])==9 and all(c['rejected']for c in audit['intrinsic_controls'])
            result['variants'][variant]=dict(capture=cap,audit=audit);save()
        first=OUT/'precise/wire/rc03';second=OUT/'precise_reversed/wire/rc03'
        assert records(first/'wires.spice')==records(second/'wires.spice'),'Two-order native R/C/device records differ'
        _,equivalence=cap_order.reorder((second/'pump_wires.ext').read_text(),(first/'pump_wires.ext').read_text())
        for token in ('device','parameters','node','port','equiv','substrate'):
            assert [r for r in cap_order.rows((first/'pump_wires.ext').read_text())if r[0]==token]==[r for r in cap_order.rows((second/'pump_wires.ext').read_text())if r[0]==token],token
        reversal=json.loads((second/'pump_wires.order-proof.json').read_text());assert reversal['reversed_enumeration']and reversal['symmetric_endpoint_value_multiset_exact']and reversal['non_coupling_records_unchanged']
        result['native_order_equivalence']=equivalence;result['reversal']=reversal
        result['composition']=compose(result['variants']['precise']['capture'],result['variants']['precise']['audit'])
        result['current_input_integrity']=admission.verify_restored()
        check();result.update(status='PASS_PD500_MIM_NATIVE_DOUBLE_TOTALS_TWO_ORDERS_22_CONTROLS_EACH_AND21_COMPOSITION_CONTROLS_REQUIRES_LOADED_WAVES',sources_unchanged=True,both_native_orders_verified=True,native_rc_and_device_records_equal_in_both_orders=True)
    except BaseException as error:result.update(status='FAIL_OR_ERROR',error=repr(error));raise
    finally:
        result['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};save()
if __name__=='__main__':main()
