#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Prepare original1us stimulus with whole native845+4-contact RC, hosted only.

This prepares complete terminal instrumentation; it does not assert electrical
acceptance or silently substitute old internal selected-probe names.
"""
import hashlib,json,os,re,tarfile
from pathlib import Path
import compare_cloud_routed_endpoints as reports
import build_pcie_local_vco_hybrid_v6 as parser
import cloud_pll_vbic_acquisition as original
from route_cloud_newer_postcts import fetch,sha
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'hw/soc/out/cloud-pll845-loaded-preparation'
SOURCE=ROOT/'cloud-pll-snapshot'
def prepare_deck(old,parent,model,contract):
    oldrows=parser.statements(parent);newrows=parser.statements(model)
    assert oldrows[0][0].lower()==newrows[0][0].lower()=='.subckt'
    oldports=oldrows[0][2:];newports=newrows[0][2:]
    assert len(oldports)==len(set(oldports))==18
    assert set(oldports)==set(newports)==set(contract['interface'])
    lines=old.splitlines()
    loops=[(i,l)for i,l in enumerate(lines)if re.match(r'(?i)^xloop\s',l)]
    assert len(loops)==1
    idx,line=loops[0];fields=line.split()
    assert len(fields)==20 and fields[-1].lower()==oldrows[0][1].lower()
    external=dict(zip(oldports,fields[1:-1]))
    assert len(external)==18
    candidate_line=' '.join([fields[0],*[external[p]for p in newports],newrows[0][1]])
    lines[idx]=candidate_line
    old_flags=[l for l in lines if re.match(r'^alter .*\[off\] = 1$',l)]
    assert len(old_flags)==102
    hbts=[d for d in contract['device_records']if d['model']=='npn13g2']
    assert len(hbts)==102
    flags=['alter q.xloop.'+d['instance'].lower()+'.qnpn13g2[off] = 1'for d in hbts]
    start=next(i for i,l in enumerate(lines)if l==old_flags[0])
    assert lines[start:start+102]==old_flags,'OFF block must remain at its original execution point'
    lines[start:start+102]=flags
    saves=[(i,l)for i,l in enumerate(lines)if l.startswith('save ')]
    assert len(saves)==1
    save_index,save_line=saves[0];oldvectors=save_line[5:].split();assert len(oldvectors)==34
    public_vectors=[n for n in oldvectors if not n.lower().startswith('v(xloop.')]
    assert len(public_vectors)>=10 and all(re.fullmatch(r'v\([^()]+\)',n)for n in public_vectors)
    def probe(node):
        if node in external:
            top=external[node]
            return None if top=='0'else 'v('+top.lower()+')'
        return 'v(xloop.'+node.lower()+')'
    records=[]
    for d in contract['device_records']:
        for t in d['terminals']:
            records.append(dict(instance=d['instance'],native_id=d['native_id'],model=d['model'],
              terminal=t['terminal'],node=t['node'],vector=probe(t['node']),explicit_zero_reference=probe(t['node'])is None))
    assert len(records)==2737
    contact_probes=[dict(instance=a['instance'],body=probe(a['body_node']),metal=probe(a['metal_node']))
                    for a in contract['auxiliary_contact_models']]
    vectors=list(dict.fromkeys(public_vectors+[r['vector']for r in records if r['vector']]+
                 [p for a in contact_probes for p in (a['body'],a['metal'])if p]))
    lines[save_index]='save '+' '.join(vectors)
    text='\n'.join(lines)+'\n'
    assert old.count('.tran 3.125e-13 1e-06 0 3.125e-13')==text.count('.tran 3.125e-13 1e-06 0 3.125e-13')==1
    assert '.options reltol=1e-4 abstol=1e-12 klu'in text
    assert len(re.findall(r'(?m)^alter .*\[off\] = 1$',text))==102
    # Reversibility proves all stimuli, loads, solver settings and transient
    # duration are exactly retained. Only model call, OFF identities and saves move.
    reverse=text.replace(candidate_line,line,1)
    reverse=reverse.replace('\n'.join(flags),'\n'.join(old_flags),1)
    reverse=reverse.replace('save '+' '.join(vectors),save_line,1)
    assert reverse==old or reverse.rstrip('\n')==old.rstrip('\n')
    assert all(n in vectors for n in ('v(reference)','v(fb)','v(vctrl)'))
    return text,dict(external_mapping=external,original_loop_call=line,candidate_loop_call=candidate_line,
        original_vectors=oldvectors,retained_public_vectors=public_vectors,
        old_internal_selected_probes_replaced_by_full_terminal_instrumentation=[v for v in oldvectors if v not in public_vectors],
        native_terminal_probes=records,auxiliary_contact_probes=contact_probes,vectors=vectors,
        native_hbt_off_targets=flags,all_original_stimuli_loads_solver_duration_unchanged=True,
        full_native_terminal_coverage=True,original_internal_semantic_probe_mapping_complete=False)
def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    OUT.mkdir(parents=True,exist_ok=False);reports.OUT=OUT
    r=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],controller_sha256=sha(Path(__file__)),
      accepted=False,full_phy_accepted=False,loaded_simulation_passed=False,qualified_pex=False)
    def save():(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
    save()
    try:
        selected=['pll845-mim-wire.spice','composition.json','binding/binding.json']
        composition,proof=reports.restore_report('pll845-body-composition',39359081592,
         'fbf32f82316a71dfc8787a9994f20903e50b16b4defb28063ce783cdba2c3bee',
         'a50e2d0ef6afefacc11a24f7b109e3ed2e3d1cbcb1703340132d89c3b939413c',OUT/'composition',selected)
        assert composition['source_head']=='12240f7368bd9ad11da675b68741ea61bd9e1530'
        assert composition['sources_unchanged']and len(composition['controls'])==62 and all(x['rejected']for x in composition['controls'])
        assert composition['status']=='PASS_PLL845_BODY_COMPOSITION_AND62_CONTROLS_REQUIRES_LOADED_CLOSED_LOOP'
        contract=json.loads((OUT/'composition/composition.json').read_text())
        assert contract==composition['composition']and not contract['uncontacted_body_groups']
        assert contract['counts']==dict(devices=845,auxiliary_contacts=4,total_model_instances=849,R=3381,C=5105,MIM=26)
        r['composition_source']=proof;save()
        fetch(original.URL+'.json',original.SUMMARY_SHA,OUT/'original-summary.json')
        prior=json.loads((OUT/'original-summary.json').read_text())
        assert prior['status']=='COMPLETE_ACTUAL845_ONE_US_SELECTED_PROBES_REQUIRES_LOCK_AND_SAFETY_REVIEW'
        assert prior['native_stop_s']==1e-6 and prior['native_off_flags']==102 and len(prior['vectors'])==34
        wanted={v['hosted_path']:v['sha256']for v in prior['inputs'].values()}
        assert len(wanted)==35
        wanted.update({'source/bench.cir':prior['source_deck_sha256'],'circuit.cir':prior['relocated_deck_sha256'],
                       'parent865.spice':prior['parent_sha256']})
        packed=OUT/'original-inputs.tar.gz'
        fetch(original.URL+'.tar.gz',original.ARCHIVE_SHA,packed)
        assert packed.stat().st_size==1318040150
        assert not SOURCE.exists();SOURCE.mkdir()
        found=set()
        with tarfile.open(packed)as tar:
            for item in tar:
                p=Path(item.name)
                assert not p.is_absolute()and'..'not in p.parts and p.parts[0]=='cloud-pll-snapshot'
                relative=str(Path(*p.parts[1:]))
                if relative not in wanted:continue
                assert item.isfile()and relative not in found
                data=tar.extractfile(item).read()
                assert hashlib.sha256(data).hexdigest()==wanted[relative]
                target=SOURCE/relative;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data);found.add(relative)
        assert found==set(wanted);packed.unlink()
        old=(SOURCE/'circuit.cir').read_text();parent=(SOURCE/'parent865.spice').read_text()
        model=(OUT/'composition/pll845-mim-wire.spice').read_text()
        r['original_stimulus_lines']=[l for l in old.splitlines()if l and not l.startswith(('*','alter ','save '))]
        r['original_parent_interface']=parser.statements(parent)[0]
        r['native_candidate_interface']=parser.statements(model)[0]
        save()
        deck,coverage=prepare_deck(old,parent,model,contract)
        (OUT/'candidate-circuit.cir').write_text(deck)
        (OUT/'terminal-instrumentation.json').write_text(json.dumps(coverage,indent=2)+'\n')
        # Retain only the protected input files, never the old waveform payload.
        for rel in sorted(wanted):
            dest=OUT/'model-sources'/rel;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes((SOURCE/rel).read_bytes())
        assert all(sha(SOURCE/n)==h for n,h in wanted.items())
        assert all(sha(OUT/'composition'/n)==composition['outputs'][n]for n in selected)
        r.update(status='PASS_WHOLE_PLL_LOADED_DECK_AND2737_TERMINAL_INSTRUMENTATION_REQUIRES_NATIVE_EXECUTION',
          source_inputs=wanted,original_summary_sha256=original.SUMMARY_SHA,
          original_archive_sha256=original.ARCHIVE_SHA,retained_public_vectors=coverage['retained_public_vectors'],
          terminal_probes=len(coverage['native_terminal_probes']),vectors=len(coverage['vectors']),
          all_original_stimuli_loads_solver_duration_unchanged=True,sources_unchanged=True,
          native_execution_performed=False,original_internal_semantic_probe_mapping_complete=False)
    except BaseException as e:r.update(status='FAIL_OR_ERROR',error=repr(e));raise
    finally:
        r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};save()
if __name__=='__main__':main()
