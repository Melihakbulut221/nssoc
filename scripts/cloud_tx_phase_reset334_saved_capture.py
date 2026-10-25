#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""One simulator-free read of the completed rejected318 capture and exact native roles."""
import argparse,base64,copy,hashlib,json,os,re,shutil,tarfile,tempfile,traceback
from pathlib import Path
import tx_phase_reset334_saved_diagnosis as observer
import cloud_tx_normal_saved_capture as transport
import tx_phase_reset334_loaded_contract as bench
import tx_phase_reset334_loaded_native_adapter as initialization
ROOT=Path(__file__).resolve().parents[1]
METHOD='scripts/tx-phase-reset334-saved-capture-cloud-methods.json'
GROUP='tx-phase-reset334-saved-capture-diagnosis'
OUT=ROOT/('cloud-'+GROUP)
sha=transport.sha
write=transport.write

def methods():
    m=json.loads((ROOT/METHOD).read_bytes())
    for n,h in m['protected_files'].items():assert sha(ROOT/n)==h,n
    assert m['native_simulation_authorized']is False
    core=json.loads((ROOT/observer.METHOD).read_bytes())
    closure=json.loads((ROOT/core['original_method_path']).read_bytes())
    assert len(closure['protected'])==182
    for n,h in closure['protected'].items():assert sha(ROOT/n)==h,n
    return m

def original_result(r):
    assert r['run_id']==40178775666 and r['source_head']=='7398bb00efc4ec6ff053aeb50e03028570f0cfa0'
    assert r['status']=='REJECTED_PHYSICAL334_THREE_MODEL_ORIGINAL_LOADED_GATES'
    assert r['stage']=='initial'and r['case']=='p-initial-high'and r['full_capture']is True
    assert r['native_process_saved']is False
    assert r['continuation']==dict(run=40178775666,attempt=1,
      group='tx-phase-reset334-transient-native-initial-p-initial-high',source_head=r['source_head'],
      controller_sha256=r['controller_sha256'],case='p-initial-high',native_process_saved=False,
      next_phase='review_complete_capture'),'Completed capture descriptor must never authorize continuation'
    assert r['native_exit_code']==0 and r['sources_unchanged']is True
    assert r['electrical_screen_passed']is False and r['full_PHY_accepted']is False
    q=r['review'];assert q['passed']is False and not q['errors']and not q['diagnostics']
    assert len(q['measurement']['hbt_safety'])==318
    assert sum(not h['passed']for h in q['measurement']['hbt_safety'].values())==17
    assert q['capture']['raw_sha256']==r['outputs']['work/wave.raw']
    assert r['outputs']['work/contract.json']=='ac96181ace2135093d941a7c7f4c137de0acd7176ae5d7b49d55947eb61ed8ce'
    return True

def reconstruct_inputs(prepared,native_result):
    summary=(prepared/'binding.summary.json').read_bytes()
    payloads={s:(prepared/'qualified-binding'/f'{s}-bindings-and-controls.json').read_bytes()for s in ('p','n')}
    models={s:(prepared/'qualified-binding/qualified-rc'/s/'composition/reset334-wire.spice').read_text()for s in ('p','n')}
    scalar=(prepared/'original-PLL-observer.summary.json').read_bytes()
    model_paths={s:Path('/home/runner/work/nssoc/nssoc/cloud-tx-phase-reset334-loaded-preparation/qualified-binding/qualified-rc')/s/'composition/reset334-wire.spice'for s in ('p','n')}
    deck,c=bench.prepare(summary,payloads,models,scalar,'p',True,model_paths,'/fixture/sg13g2-ngspice-models','/fixture/r3_cmc.osdi')
    base=(prepared/'cases/p-initial-high/bench.cir').read_text()
    saved=json.loads((prepared/'cases/p-initial-high/contract.json').read_bytes())
    assert deck==base and observer.canonical(c)==observer.canonical(saved)
    path=native_result['preparation_source']['path_binding'];rows=deck.splitlines(keepends=True)
    assert len(path['six_path_cards'])==6 and path['byte_exact_reversal']is True
    for edit in path['six_path_cards']:
        assert rows[edit['line']]==edit['old'];rows[edit['line']]=edit['new']
    runtime=''.join(rows);assert observer.digest(runtime.encode())==path['runtime_base_sha256']
    adapter=initialization.adapters();full=adapter.initialized_deck(runtime,c)
    assert full.replace(adapter.flag_block(c,True),'')==runtime
    assert observer.digest(full.encode())==native_result['outputs']['work/bench.cir']
    assert observer.digest((json.dumps(c,indent=2,allow_nan=False)+'\n').encode())==native_result['outputs']['work/contract.json']
    return c,full,dict(binding_summary=summary,payloads=payloads,models=models,scalar=scalar)

def validate_actual(c,deck,expected,expected_deck):
    assert c==expected,'Actual native roles/ports/oracles/vector contract differs from regenerated qualified inputs'
    assert deck==expected_deck,'Original runtime path/318OFF/source/save/solver deck changed'
    assert len(c['hbt'])==318 and len(c['thermal_nodes'])==390 and len(c['vectors'])==4726
    assert len({i['body_node']for i in c['instances']})==3 and all(i['finite_body_contacts']==90 for i in c['instances'])
    return dict(actual_HBT_roles=318,actual_rppd_thermal_states=390,saved_vectors=4726,finite_body_networks=3,
      exact_qualified_native_role_reconstruction=True,original_three_prescribed_oracles_equal=True)

def actual_controls(c,deck,expected,expected_deck,inputs):
    positive=validate_actual(c,deck,expected,expected_deck);bad=[];target=next(iter(c['hbt']))
    def reject(label,mutate):
        q,b=copy.deepcopy(c),deck;q,b=mutate(q,b);assert(q,b)!=(c,deck)
        try:validate_actual(q,b,expected,expected_deck)
        except(AssertionError,KeyError):bad.append(label)
        else:raise AssertionError('Accepted actual role/deck fault '+label)
    def field(fn):
        def edit(q,b):fn(q);return q,b
        return edit
    trials=[('HBT_Nx',lambda q:q['hbt'][target].__setitem__('nx',3)),
      ('HBT_collector',lambda q:q['hbt'][target]['terminals'].__setitem__(0,'0')),
      ('HBT_emitter',lambda q:q['hbt'][target]['terminals'].__setitem__(2,'wrong')),
      ('HBT_substrate',lambda q:q['hbt'][target]['terminals'].__setitem__(3,'0')),
      ('HBT_source_role',lambda q:q['hbt'][target].__setitem__('source_instance','PHASE__WRONG')),
      ('HBT_native_ID',lambda q:q['hbt'][target].__setitem__('native_id',999)),
      ('child_clock_polarity',lambda q:q['instances'][1]['actual_ports'].__setitem__(0,'mn')),
      ('child_preset',lambda q:q['instances'][1].__setitem__('variant','p')),
      ('finite_body_short',lambda q:q['instances'][0].__setitem__('body_node','0')),
      ('observed_phase_fit',lambda q:q['instances'][0]['oracle'].__setitem__('observed_phase_fit',True)),
      ('original_UI',lambda q:q['timing'].__setitem__('UI_s',126e-12)),
      ('original_margin',lambda q:q['limits'].__setitem__('min_sign_margin_v',.09)),
      ('missing_native_vector',lambda q:q['vectors'].pop()),
      ('missing_thermal_state',lambda q:q['thermal_nodes'].pop()),
      ('physical_child_role',lambda q:q['instances'][2].__setitem__('physical_role','phase_l1_k0'))]
    for label,fn in trials:reject(label,field(fn))
    def deckedit(label,pattern,replacement):
        def edit(q,b):
            b,count=re.subn(pattern,replacement,b,count=1,flags=re.M);assert count==1;return q,b
        reject(label,edit)
    deckedit('missing_uniform_OFF',r'^alter @q\.[^\n]+\n','')
    deckedit('changed_supply',r'^Vrail [^\n]+','Vrail avdd 0 2.4')
    deckedit('changed_transient',r'^\.tran [^\n]+','.tran 1p 34n')
    for label,section,key in [('changed_P_model','models','p'),('changed_N_model','models','n'),
      ('changed_P_binding','payloads','p'),('changed_N_binding','payloads','n'),
      ('changed_binding_summary','binding_summary',None),('changed_PLL_scalar','scalar',None)]:
        q=copy.deepcopy(inputs)
        if key is None:q[section]+=b'\n'
        else:q[section][key]+='\n'if isinstance(q[section][key],str)else b'\n'
        assert q!=inputs
        try:
            bench.qualified_inputs(q['binding_summary'],q['payloads'],q['models'])
            bench.original.boundary(q['scalar'])
        except(AssertionError,KeyError,ValueError):bad.append(label)
        else:raise AssertionError('Accepted changed qualified native input '+label)
    assert len(bad)==24
    return dict(positive=positive,rejected=bad,waveform_review_executed=False)

def source_controls():
    m=methods()
    from check_tx_phase_reset334_saved_diagnosis import controls
    math=controls();assert len(math['rejected'])==20
    metadata=transport.metadata_controls(m);assert len(metadata['rejected'])==23
    parts=transport.parts_controls();selected=transport.selected_archive_controls();publication=transport.release.controls()
    original=json.loads((ROOT/observer.RESULT).read_bytes());original_result(original);rejected=[]
    for key,value in [('native_exit_code',1),('native_process_saved',True),('full_capture',False),
      ('source_head','0'*40),('case','p-initial-low'),('electrical_screen_passed',True),('sources_unchanged',False)]:
        q=copy.deepcopy(original);q[key]=value;assert q!=original
        try:original_result(q)
        except(AssertionError,KeyError):rejected.append(key)
        else:raise AssertionError('Accepted source-result fault '+key)
    for key,value in [('native_process_saved',True),('next_phase','restore_and_continue')]:
        q=copy.deepcopy(original);q['continuation'][key]=value;assert q!=original
        try:original_result(q)
        except(AssertionError,KeyError):rejected.append('continuation:'+key)
        else:raise AssertionError('Accepted completed-capture continuation fault '+key)
    assert len(rejected)==9
    with tempfile.TemporaryDirectory()as td:
        root=Path(td);d=root/'fixture';d.mkdir();(d/'a').write_bytes(b'actual\x1b opaque bytes');(d/'b').write_bytes(b'complete inventory')
        manifest=transport.pack(d,'fixture',root,32);expected={n:sha(d/n)for n in ('a','b')}
        good=transport.audit_complete(manifest,root,root/'good',expected,{'a'})
        assert set(good['all_original_files'])==set(expected)and good['publication_addons']=={}
        faults=[]
        def reject(label,fn):
            try:fn()
            except(AssertionError,KeyError,FileNotFoundError):faults.append(label)
            else:raise AssertionError('Accepted archive fault '+label)
        reject('missing_original',lambda:transport.audit_complete(manifest,root,root/'missing',dict(expected,c='0'*64),{'a'}))
        reject('unknown_original',lambda:transport.audit_complete(manifest,root,root/'unknown',{'a':expected['a']},{'a'}))
        reject('changed_unselected',lambda:transport.audit_complete(manifest,root,root/'changed',dict(expected,b='0'*64),{'a'}))
        reject('unknown_selection',lambda:transport.audit_complete(manifest,root,root/'select',expected,{'c'}))
        for label,path,kind in [('traversal','fixture/../x',tarfile.REGTYPE),('absolute','/fixture/x',tarfile.REGTYPE),
          ('backslash','fixture/\\x',tarfile.REGTYPE),('wrong_root','other/x',tarfile.REGTYPE),
          ('symlink','fixture/x',tarfile.SYMTYPE),('hardlink','fixture/x',tarfile.LNKTYPE),('noncanonical','fixture//x',tarfile.REGTYPE)]:
            entry=tarfile.TarInfo(path);entry.type=kind
            reject(label,lambda entry=entry:transport.safe_relative(entry,'fixture'))
        assert len(faults)==11
    return dict(status='PASS_PHASE318_SAVED_CAPTURE_SOURCE_CONTROLS_ONLY',math=math,metadata=metadata,
      original_result_faults=rejected,archive_faults=faults,parts=parts,selected_archive=selected,publication=publication,
      readback_authorized=m['readback_authorized'],new_simulation=False,actual_input_controls_executed=False)

def main():
    p=argparse.ArgumentParser();p.add_argument('--controls',action='store_true');p.add_argument('--readback',action='store_true');a=p.parse_args()
    assert a.controls != a.readback and os.environ.get('GITHUB_ACTIONS')=='true'
    m=methods()
    if a.controls:print(json.dumps(source_controls(),indent=2));return
    assert m['readback_authorized']is True
    OUT.mkdir(exist_ok=False);result=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],run_id=int(os.environ['GITHUB_RUN_ID']),
      original_electrical_rejection_preserved=True,accepted=False,new_simulation=False,native_process_resumed=False,
      all31_clock_tree_accepted=False,PLL_connected=False,full_PHY_accepted=False)
    def save():write(OUT/'result.json',result)
    save();work=Path(os.environ['RUNNER_TEMP'])/'tx-phase318-saved-capture'
    try:
        result['publication_preflight']=transport.precreated(GROUP);save()
        assert shutil.disk_usage(work.parent).free>=16*1024**3,'Need16GiB for exact saved capture restore'
        work.mkdir(exist_ok=False)
        source=json.loads((ROOT/observer.RESULT).read_bytes());original_result(source)
        parts=json.loads((ROOT/m['native_parts_path']).read_bytes())
        for path,want in [(m['native_source']['workflow'],m['original_native_workflow_sha256']),
          ('scripts/cloud_tx_phase_reset334_transient.py',source['controller_sha256'])]:
            actual=transport.api('contents/'+path+'?ref='+m['native_source']['source'])
            if not actual.get('content'):actual=transport.api('git/blobs/'+actual['sha'])
            assert hashlib.sha256(base64.b64decode(actual['content'])).hexdigest()==want
        result['native_source_identity']=transport.restore_parts(m['native_source'],parts,work/'native-parts');save()
        expected=dict(source['outputs']);expected['result.json']=m['source_summary_sha256']
        selected={'work/'+n for n in ('wave.raw','bench.cir','contract.json','native.log','op.raw')}
        result['native_archive']=transport.audit_complete(parts,work/'native-parts',work/'native',expected,selected);save()
        prep=json.loads((ROOT/m['prepared_summary_path']).read_bytes());pp=json.loads((ROOT/m['prepared_parts_path']).read_bytes())
        assert prep['status']=='PASS_FOUR_REAL_THREE_MODEL_PREPARATIONS_NOT_ELECTRICAL_ACCEPTANCE'
        assert prep['run_id']==source['preparation_source']['run']==m['prepared_source']['run']
        assert source['preparation_source']['summary_sha256']==m['prepared_summary_sha256']
        assert source['preparation_source']['manifest_sha256']==sha(ROOT/m['prepared_parts_path'])
        assert source['preparation_source']['restore']['archive']['sha256']==pp['sha256']
        result['prepared_source_identity']=transport.restore_parts(m['prepared_source'],pp,work/'prepared-parts');save()
        chosen={'binding.summary.json','original-PLL-observer.summary.json','cases/p-initial-high/bench.cir','cases/p-initial-high/contract.json'}
        chosen|={'qualified-binding/'+s+'-bindings-and-controls.json'for s in ('p','n')}
        chosen|={'qualified-binding/qualified-rc/'+s+'/composition/reset334-wire.spice'for s in ('p','n')}
        expected_p=dict(prep['outputs']);expected_p['result.json']=m['prepared_summary_sha256']
        result['prepared_archive']=transport.audit_complete(pp,work/'prepared-parts',work/'prepared',expected_p,chosen);save()
        expected_c,expected_b,inputs=reconstruct_inputs(work/'prepared',source)
        case=work/'native/work';c=json.loads((case/'contract.json').read_bytes());deck=(case/'bench.cir').read_text()
        result['actual_input_controls']=actual_controls(c,deck,expected_c,expected_b,inputs);save()
        method=json.loads((ROOT/observer.METHOD).read_bytes());assert method['readback_authorized']is True
        write(OUT/'consumed-input-binding.json',dict(contract_sha256=sha(case/'contract.json'),
          native_deck_sha256=sha(case/'bench.cir'),actual_input_controls=result['actual_input_controls'],
          prepared_inputs={n:expected_p[n]for n in sorted(chosen)},
          original_first_fall_limit_s=observer.UI/2,original_electrical_acceptance=False,
          no_simulation=True,no_continuation=True))
        diagnosis=observer.observe_restored(case,method,lambda name,value:write(OUT/name,value))
        proof=write(OUT/'complete-native-row-diagnosis.json',diagnosis)
        compact=dict(status=diagnosis['status'],full_witness=proof,frames=len(diagnosis['frames']),
          failed_hbt_count=diagnosis['original_failed_HBT_count'],pair_extrema_both_signs=diagnosis['pair_extrema_both_signs'],
          failed_hbt_same_row_extrema=diagnosis['failed_hbt_same_row_extrema'],first_fall_windows=diagnosis['first_fall_windows'],
          native_pair_nodes=diagnosis['native_pair_nodes'],original_first_fall_limit_s=diagnosis['original_first_fall_limit_s'],
          original_rejection_reproduced=True,causal_conclusion=False,circuit_edit_justified=False,
          full_row_observations_in_separate_witness=True,no_interpolation_or_observed_phase_fit=True)
        write(OUT/'diagnostic-index.json',compact)
        result.update(status='PASS_PHASE318_SAVED_DIAGNOSIS_ORIGINAL_ELECTRICAL_REJECTION_REMAINS',diagnostic_index=compact,
          full_original_electrical_review_replays=1,source_capture_sha256=m['raw_sha256'])
    except BaseException as error:
        result.update(status='FAIL_PHASE318_SAVED_CAPTURE_DIAGNOSIS',error=repr(error),traceback=traceback.format_exc());raise
    finally:
        result['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p.name!='result.json'}
        save();raw=(OUT/'result.json').read_bytes();assert len(raw)<8*1024**2
        print('RESULT_SHA256',hashlib.sha256(raw).hexdigest());print('RESULT_BYTES',len(raw))
        text=base64.b64encode(raw).decode();chunks=[text[i:i+4096]for i in range(0,len(text),4096)]
        for i,c in enumerate(chunks):print(f'RESULT_BASE64 {i}/{len(chunks)} {c}')
if __name__=='__main__':main()
