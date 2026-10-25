# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Observation-only refinement; fixtures never stand in for full-chip proofs."""
import copy
import json
from pathlib import Path
import shutil
import stat
import sys
import zipfile

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]/'scripts'))
import prove_alu_state_refinement as ref  # noqa: E402


def fixture():
    module, _ = ref.state.lift(ref.state.fixture(), ['ff0','ff1'])
    plan = ref.part.make_plan(module, module, 2)
    parents = [g['id'] for g in plan['groups'][:-1]]
    refined = ref.refinement_plan(plan, parents, 1)
    return plan, parents, refined


def records(plan, timeouts=()):
    return [dict(shard=s, groups=[dict(id=g['id'], bits=len(g['obligations']), shard=s, native_returncode=0,
        verdict='TIMEOUT_UNPROVED' if g['id'] in timeouts else 'PROVED_ALL_BINARY_BOUNDARY_EQUATIONS')
        for g in plan['groups'] if g['shard']==s]) for s in range(4)]


def test_refines_only_unproved_output_bits_and_preserves_every_input():
    plan, parents, refined = fixture()
    assert (refined['symbolic_input_bits'], refined['total_output_bits'], len(refined['groups'])) == (6,8,8)
    assert refined['symbolic_inputs'] == plan['symbolic_inputs']
    mapped = ref.validate_refinement(plan, refined, parents)
    assert mapped == [tuple(p) for g in plan['groups'][:-1] for p in g['obligations']]
    verdict = ref.combined_verdict(plan, records(plan,parents), refined, records(refined), parents)
    assert verdict['state_bijection_proved'] and verdict['complete_original_output_bits']==9
    assert verdict['preserved_proved_groups']==1 and verdict['refined_parent_groups']==4
    assert not verdict['full_soc_functional_accepted'] and verdict['unresolved_four_state_boot_failure']


@pytest.mark.parametrize('fault', ['missing_parent','duplicate_parent','unknown_parent','zero_width'])
def test_parent_and_width_guards(fault):
    plan, parents, refined = fixture()
    if fault=='missing_parent':
        with pytest.raises(ValueError): ref.validate_refinement(plan,refined,parents[:-1])
        return
    if fault=='duplicate_parent': parents.append(parents[0])
    if fault=='unknown_parent': parents[0]='unknown'
    with pytest.raises(ValueError): ref.refinement_plan(plan,parents,0 if fault=='zero_width' else 1)


@pytest.mark.parametrize('fault', ['missing_bit','duplicate_bit','wrong_bit','missing_group','wrong_owner','changed_input'])
def test_refinement_cannot_omit_relabel_or_duplicate_equations(fault):
    plan, parents, refined = fixture()
    if fault=='missing_bit': refined['groups'][0]['obligations'].pop()
    if fault=='duplicate_bit': refined['groups'][1]['obligations']=copy.deepcopy(refined['groups'][0]['obligations'])
    if fault=='wrong_bit': refined['groups'][0]['obligations'][0][1]+=1
    if fault=='missing_group': refined['groups'].pop()
    if fault=='wrong_owner': refined['groups'][0]['shard']=2
    if fault=='changed_input':
        key=next(iter(refined['symbolic_inputs']));refined['symbolic_inputs'][key]+=1;refined['symbolic_input_bits']+=1
    with pytest.raises(ValueError): ref.validate_refinement(plan,refined,parents)


@pytest.mark.parametrize('fault', ['old_cex','old_unknown','old_tool_error','old_omission','old_duplicate','timeout_set',
                                  'new_omission','new_duplicate','missing_shard','extra_shard'])
def test_combined_coverage_cannot_hide_any_old_or_new_result(fault):
    plan, parents, refined = fixture();old=records(plan,parents);new=records(refined)
    if fault=='old_cex': old[0]['groups'][0]['verdict']='COUNTEREXAMPLE_PRESERVED'
    if fault=='old_unknown': old[0]['groups'][0]['verdict']='UNKNOWN'
    if fault=='old_tool_error': old[0]['groups'][0]['native_returncode']=1
    if fault=='old_omission': old[0]['groups'].pop()
    if fault=='old_duplicate': old[0]['groups'].append(copy.deepcopy(old[0]['groups'][0]))
    if fault=='timeout_set': parents.pop()
    if fault=='new_omission': new[0]['groups'].pop()
    if fault=='new_duplicate': new[0]['groups'].append(copy.deepcopy(new[0]['groups'][0]))
    if fault=='missing_shard': new.pop()
    if fault=='extra_shard': new.append(copy.deepcopy(new[0]))
    with pytest.raises(ValueError): ref.combined_verdict(plan,old,refined,new,parents)


@pytest.mark.parametrize('verdict', ['TIMEOUT_UNPROVED','COUNTEREXAMPLE_PRESERVED','UNKNOWN'])
def test_new_nonpassing_bit_is_never_accepted(verdict):
    plan,parents,refined=fixture();new=records(refined);new[0]['groups'][0]['verdict']=verdict
    result=ref.combined_verdict(plan,records(plan,parents),refined,new,parents)
    assert not result['state_bijection_proved']


def test_observation_wrapper_contains_no_added_inputs_or_internal_assumptions(tmp_path):
    plan,parents,refined=fixture();text=ref.wrapper(plan,refined,parents)
    assert text.count('nssoc_preserved_miter preserved(')==1
    assert text.count('input wire ')==len(plan['symbolic_inputs'])
    for n in plan['symbolic_inputs']: assert f'.in_{n}(in_{n})' in text
    for group in refined['groups']:
        for prefix in ('gold','gate'):
            expected='{'+', '.join(f'observed_{prefix}_{p}[{i}]' for p,i in reversed(group['obligations']))+'}'
            assert f'assign {prefix}_{group["id"]} = {expected};' in text
    script=ref.build_script(tmp_path/'prior.il',tmp_path/'observe.v',tmp_path/'result.il',tmp_path/'interface.json')
    assert 'rename miter nssoc_preserved_miter' in script and 'prep -top miter -flatten' in script
    assert script.count('read_rtlil')==1
    assert not any(s in script+text for s in ['setundef','cutpoint','blackbox',' -set ','assume','delete -input'])


def test_full_work_is_cloud_only_before_output_creation(tmp_path,monkeypatch):
    monkeypatch.delenv('GITHUB_ACTIONS',raising=False)
    with pytest.raises(ValueError): ref.prepare(tmp_path/'output',tmp_path/'work')
    with pytest.raises(ValueError): ref.run_shard(tmp_path/'bundle',0,tmp_path/'output',tmp_path/'work')
    assert not (tmp_path/'output').exists()


def test_pinned_input_is_exact_incomplete_producer_without_changing_old_sources():
    lock=ref.load_lock()
    assert len(lock['timed_out_groups'])==19 and lock['proved_groups']==250
    assert lock['common_miter']['bytes']==187903447 and lock['source_conclusion']=='failure'
    for name,pin in ref.PINS.items(): assert ref.state.common.sha(ref.ROOT/name)==pin


def test_safe_archive_preserves_nested_bytes(tmp_path):
    z=tmp_path/'good.zip'
    with zipfile.ZipFile(z,'w') as archive: archive.writestr('nested/member.bin', bytes(range(256)))
    ref.restore(z,tmp_path/'capture')
    assert (tmp_path/'capture/nested/member.bin').read_bytes()==bytes(range(256))


@pytest.mark.parametrize('fault',['parent','absolute','link','duplicate'])
def test_archive_rejects_unsafe_or_duplicate_entries(tmp_path,fault):
    z=tmp_path/'bad.zip'
    with zipfile.ZipFile(z,'w') as archive:
        if fault=='parent': archive.writestr('../escape','bad')
        if fault=='absolute': archive.writestr('/escape','bad')
        if fault=='link':
            info=zipfile.ZipInfo('link');info.external_attr=(stat.S_IFLNK|0o777)<<16;archive.writestr(info,'target')
        if fault=='duplicate':
            archive.writestr('same','one')
            with pytest.warns(UserWarning): archive.writestr('same','two')
    with pytest.raises(ValueError): ref.restore(z,tmp_path/'capture')


def fixture_log(plan,shard,timeouts):
    lines=[]
    for g in plan['groups']:
        if g['shard']!=shard: continue
        outcome='Interrupted SAT solver: TIMEOUT!' if g['id'] in timeouts else 'SAT proof finished - no model found: SUCCESS!'
        lines += [f'NSSOC_GROUP_BEGIN {g["id"]}', 'Final constraint equation: { } = { }', outcome,
                  f'NSSOC_GROUP_END {g["id"]} 0']
    return '\n'.join(lines+['NSSOC_ALL_ASSIGNED_GROUPS_VISITED',''])


def prior_bundle(tmp_path):
    """Small explicit mock receipt at the original producer validation boundary."""
    plan,parents,_=fixture();bundle=tmp_path/'prior';common=bundle/'common';common.mkdir(parents=True)
    methods={}
    for name,sha in ref.PINS.items():
        path=common/'methods'/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes((ref.ROOT/name).read_bytes())
        methods[name]=ref.state.archived.pin(path);assert methods[name]['sha256']==sha
    ref.state.common.save(common/'plan.json',plan);(common/'common-miter.il').write_text('fixture IL; not an executed full-chip proof')
    row=dict(status='COMMON_MITER_PREPARED_NOT_PROVED', github_source_commit='fixture-source',
        complete_inputs_rechecked=True, runtime=ref.manifest()['runtime'],methods=methods,
        plan=ref.state.archived.pin(common/'plan.json'),common_miter=ref.state.archived.pin(common/'common-miter.il'),
        outputs=ref.inventory(common))
    ref.state.common.save(common/'result.json',row)
    lock=dict(source_commit='fixture-source',common_result=ref.state.archived.pin(common/'result.json'),
        plan=row['plan'],common_miter=row['common_miter'],original_input_bits=6,original_output_bits=9,original_groups=5,
        proved_groups=1,timed_out_groups=parents,shard_results={})
    rows=[]
    for shard in range(4):
        path=bundle/('shard'+str(shard));path.mkdir();log=fixture_log(plan,shard,parents);(path/'partitions.log').write_text(log)
        groups=ref.part.parse_shard(log,plan,shard,path)
        found=dict(status='ALL_ASSIGNED_GROUPS_VISITED',shard=shard,complete_inputs_rechecked=True,execution=dict(returncode=0),
            github_source_commit='fixture-source',methods=methods,common_miter=row['common_miter'],plan=row['plan'],groups=groups,
            outputs=ref.inventory(path))
        ref.state.common.save(path/'result.json',found);lock['shard_results'][str(shard)]=ref.state.archived.pin(path/'result.json');rows.append(found)
    aggregate=ref.part.aggregate(plan,rows);aggregate.update(github_source_commit='fixture-source',common_miter=row['common_miter'],
        plan=row['plan'],shard_results=lock['shard_results'])
    path=bundle/'verdict';path.mkdir();ref.state.common.save(path/'alu-partition-verdict.json',aggregate)
    lock['aggregate_result']=ref.state.archived.pin(path/'alu-partition-verdict.json')
    return bundle,lock


def test_prior_replays_every_raw_log_and_exact_source_boundary(tmp_path):
    bundle,lock=prior_bundle(tmp_path)
    _,plan,rows=ref.verify_prior(bundle,lock)
    assert ref.part.aggregate(plan,rows)['proved_groups']==1


@pytest.mark.parametrize('fault',['raw_log','group_log','result','source','runtime','missing_method','missing_output','extra_file'])
def test_original_pins_and_complete_inventory_cannot_be_weakened(tmp_path,fault):
    bundle,lock=prior_bundle(tmp_path);common=bundle/'common'
    row=json.loads((common/'result.json').read_text())
    if fault=='raw_log': (bundle/'shard0/partitions.log').write_text('changed')
    if fault=='group_log': (bundle/('shard0/'+ref.part.PREFIX+'0000.log')).write_text('changed')
    if fault=='result': (bundle/'shard0/result.json').write_text('{}')
    if fault=='source': row['github_source_commit']='other'
    if fault=='runtime': row['runtime']['sha256']='0'*64
    if fault=='missing_method': row['methods'].pop(next(iter(row['methods'])))
    if fault=='missing_output': row['outputs'].pop('common-miter.il')
    if fault=='extra_file': (common/'extra').write_text('extra')
    if fault in {'source','runtime','missing_method','missing_output'}:
        ref.state.common.save(common/'result.json',row);lock['common_result']=ref.state.archived.pin(common/'result.json')
    with pytest.raises(ValueError): ref.verify_prior(bundle,lock)


@pytest.mark.parametrize('fault',['source','event','status','conclusion','attempt'])
def test_download_refuses_wrong_producer_before_network_blob(tmp_path,monkeypatch,fault):
    lock=ref.load_lock()
    run=dict(head_sha=lock['source_commit'],event='push',status='completed',conclusion='failure',run_attempt=1)
    field={'source':'head_sha','event':'event','status':'status','conclusion':'conclusion','attempt':'run_attempt'}[fault]
    run[field]='wrong';monkeypatch.setattr(ref,'api',lambda _:run)
    with pytest.raises(ValueError): ref.fetch_originals(lock,tmp_path/'output',tmp_path/'work')


@pytest.mark.parametrize('fault',['id','name','size','sha','run','source','expired'])
def test_download_rejects_wrong_exact_artifact_before_blob(tmp_path,monkeypatch,fault):
    lock=ref.load_lock();entry=next(iter(lock['artifacts'].values()))
    run=dict(head_sha=lock['source_commit'],event='push',status='completed',conclusion='failure',run_attempt=1)
    artifact=dict(id=entry['id'],name=entry['name'],size_in_bytes=entry['bytes'],digest='sha256:'+entry['sha256'],expired=False,
                  workflow_run=dict(id=lock['source_run'],head_sha=lock['source_commit']))
    if fault in {'id','name'}: artifact[fault]='wrong'
    if fault=='size': artifact['size_in_bytes']+=1
    if fault=='sha': artifact['digest']='sha256:'+'0'*64
    if fault=='run': artifact['workflow_run']['id']+=1
    if fault=='source': artifact['workflow_run']['head_sha']='wrong'
    if fault=='expired': artifact['expired']=True
    monkeypatch.setattr(ref,'api',lambda path:run if '/runs/' in path else artifact)
    with pytest.raises(ValueError): ref.fetch_originals(lock,tmp_path/'output',tmp_path/'work')


def prepared_bundle(tmp_path,monkeypatch):
    old,lock=prior_bundle(tmp_path)
    output=tmp_path/'refined';output.mkdir();shutil.move(old,output/'prior')
    lock.update(refinement_width=1)
    monkeypatch.setattr(ref,'load_lock',lambda:copy.deepcopy(lock));monkeypatch.setenv('GITHUB_SHA','refinement-fixture-source')
    original=json.loads((output/'prior/common/plan.json').read_text())
    plan=ref.refinement_plan(original,lock['timed_out_groups'],1)
    (output/'observations.v').write_text(ref.wrapper(original,plan,lock['timed_out_groups']))
    (output/'common-miter.il').write_text('mock refined native IL; tests only')
    ref.state.common.save(output/'plan.json',plan)
    methods=ref.snapshot_methods(output)
    row=dict(status='REFINED_MITER_PREPARED_NOT_PROVED',github_source_commit='refinement-fixture-source',
        complete_inputs_rechecked=True,runtime=ref.manifest()['runtime'],methods=methods,
        original_lock=ref.state.archived.pin(ref.ROOT/ref.LOCK),original_common_miter=lock['common_miter'],
        common_miter=ref.state.archived.pin(output/'common-miter.il'),plan=ref.state.archived.pin(output/'plan.json'),
        outputs=ref.inventory(output))
    ref.state.common.save(output/'result.json',row)
    return output,row


def test_new_preparation_preserves_original_sources_runtime_and_complete_inventory(tmp_path,monkeypatch):
    bundle,_=prepared_bundle(tmp_path,monkeypatch)
    _,plan,original,rows,lock=ref.verify_common(bundle)
    assert plan['total_output_bits']==8 and original['total_output_bits']==9
    assert ref.prior_verdict(original,rows,lock['timed_out_groups'])[0]['proved_groups']==1


@pytest.mark.parametrize('fault',['missing_method','missing_output','extra_file','runtime','source','wrapper','symlink','lock'])
def test_refined_preparation_fails_closed_on_mutated_identity_or_closure(tmp_path,monkeypatch,fault):
    bundle,row=prepared_bundle(tmp_path,monkeypatch)
    if fault=='missing_method': row['methods'].pop(next(iter(row['methods'])))
    if fault=='missing_output': row['outputs'].pop('common-miter.il')
    if fault=='extra_file': (bundle/'extra').write_text('extra')
    if fault=='runtime': row['runtime']['sha256']='0'*64
    if fault=='source': row['github_source_commit']='different'
    if fault=='wrapper':
        (bundle/'observations.v').write_text('changed');row['outputs']['observations.v']=ref.state.archived.pin(bundle/'observations.v')
    if fault=='symlink': (bundle/'extra').symlink_to(bundle/'plan.json')
    if fault=='lock': row['original_lock']['sha256']='0'*64
    ref.state.common.save(bundle/'result.json',row)
    with pytest.raises(ValueError): ref.verify_common(bundle)


@pytest.mark.parametrize('changed_after',[False,True])
def test_shard_rechecks_complete_prepared_inputs_after_native_boundary(tmp_path,monkeypatch,changed_after):
    """Mock the native execution only; exercise the real before/after consumer gate."""
    _,_,plan=fixture();bundle=tmp_path/'bundle';bundle.mkdir();(bundle/'common-miter.il').write_text('mock native IL')
    runtime=tmp_path/'dummy-runtime';runtime.write_bytes(b'mock-executable')
    prepared=dict(common_miter=ref.state.archived.pin(bundle/'common-miter.il'),plan=dict(bytes=1,sha256='0'*64),
        methods={},original_common_miter={},original_lock={},runtime=ref.state.archived.pin(runtime),sentinel='before')
    calls=[]
    def verify(_):
        calls.append('full-input-closure')
        row=copy.deepcopy(prepared)
        if changed_after and len(calls)==2: row['sentinel']='changed'
        return row,plan,None,None,None
    monkeypatch.setattr(ref,'verify_common',verify);monkeypatch.setenv('GITHUB_ACTIONS','true')
    monkeypatch.setattr(ref.state.common,'download',lambda entry,path:path.write_bytes(runtime.read_bytes()))
    def execute(runtime_path,script,output,name):
        (output/(name+'.log')).write_text(fixture_log(plan,0,()))
        return dict(returncode=0)
    monkeypatch.setattr(ref.part,'execute_tcl',execute)
    if changed_after:
        with pytest.raises(ValueError,match='changed during native'):
            ref.run_shard(bundle,0,tmp_path/'out',tmp_path/'work')
        result=json.loads((tmp_path/'out/result.json').read_text())
        assert result['status']=='REFINED_SHARD_FAILED_OR_INCOMPLETE' and not result.get('complete_inputs_rechecked')
    else:
        assert ref.run_shard(bundle,0,tmp_path/'out',tmp_path/'work')['complete_inputs_rechecked']
    assert calls==['full-input-closure','full-input-closure']


def test_workflow_four_workers_preserves_prior_incomplete_status():
    text=(ref.ROOT/'.github/workflows/timing-alu-state-refinement.yml').read_text()
    assert 'max-parallel: 4' in text and 'fail-fast: false' in text and 'actions: read' in text
    assert 'needs: [prepare, prove]' in text and "needs.prepare.result == 'success'" in text
    assert ' --assume' not in text and 'cancel-in-progress: false' in text
