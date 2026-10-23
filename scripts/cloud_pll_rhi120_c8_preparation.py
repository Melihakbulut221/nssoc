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
OUT=ROOT/'hw/soc/out/cloud-pll-rhi120-c8-preparation'
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
    flags=['alter @q.xloop.'+d['instance'].lower()+'.qnpn13g2[off] = 1'for d in hbts]
    # Each OFF is followed by its native echo/show readback. Preserve all
    # command positions; rebind all102 identical OFF=1 targets and their probes.
    target_map={}
    for old_flag,new_flag in zip(old_flags,flags):
        old_target=old_flag.split()[1].split('[off]')[0].removeprefix('@')
        new_target=new_flag.split()[1].split('[off]')[0].removeprefix('@')
        assert old_target not in target_map and new_target not in target_map.values()
        assert old_flag=='alter @'+old_target+'[off] = 1'
        assert sum(l.count(old_target)for l in lines)==3,(old_target,'must occur in alter/echo/show')
        target_map[old_target]=new_target
        lines=[l.replace(old_target,new_target)for l in lines]
    assert len(target_map)==102
    assert sum(l.startswith('echo NSSOC_NATIVE_FLAG_BEGIN ')for l in lines)==102
    assert sum(l.startswith('show ')and l.endswith(' : off')for l in lines)==102
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
    for old_target,new_target in target_map.items():
        assert reverse.count(new_target)==3
        reverse=reverse.replace(new_target,old_target)
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
        composition,proof=reports.restore_report('pll-rhi120-c8-composition',39920160596,
         'eafbe90ec7991d99ecb41321163bf1bf9dde45a99575bd526e2ff185ca563e53',
         '89c737b63931f5757cd89afa9d0041ea0ac75d52b37c0e4db956173c80f33b3c',OUT/'composition',selected)
        assert composition['source_head']=='41e8b9623777d009c9dcec934484413789f74840'
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
        recovery_names=['model-sources/'+n for n in sorted(wanted)]
        recovered,recovery=reports.restore_report('pll845-loaded-preparation',39359917098,
         '14267229577ca22a5b238abd432dac4e7dcc702504bd2241e5696e4b0e748227',
         '701d1bfd73de0b8a20dc56e647e09b2f0830ba2573ffdfe9c521d18ca0d2efec',OUT/'recovery',recovery_names)
        assert recovered['status']=='FAIL_OR_ERROR'and recovered['source_head']=='4e93de433261447084e9e2698a4e1fa7805ce39f'
        assert not SOURCE.exists();SOURCE.mkdir()
        for relative,digest in wanted.items():
            data=(OUT/'recovery/model-sources'/relative).read_bytes()
            assert hashlib.sha256(data).hexdigest()==digest
            target=SOURCE/relative;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
        r['hashed_input_recovery']=recovery
        r['original_archive_re_downloaded']=False
        r['all38_input_hashes_match_original_source_summary']=len(wanted)==38
        assert len(wanted)==38
        old=(SOURCE/'circuit.cir').read_text();parent=(SOURCE/'parent865.spice').read_text()
        model=(OUT/'composition/pll845-mim-wire.spice').read_text()
        r['original_stimulus_lines']=[l for l in old.splitlines()if l and not l.startswith(('*','alter ','save ','echo ','show '))]
        r['original_parent_interface']=parser.statements(parent)[0]
        r['native_candidate_interface']=parser.statements(model)[0]
        save()
        # Retain only the protected input files, never the old waveform payload.
        for rel in sorted(wanted):
            dest=OUT/'model-sources'/rel;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes((SOURCE/rel).read_bytes())
        deck,coverage=prepare_deck(old,parent,model,contract)
        (OUT/'candidate-circuit.cir').write_text(deck)
        (OUT/'terminal-instrumentation.json').write_text(json.dumps(coverage,indent=2)+'\n')
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
