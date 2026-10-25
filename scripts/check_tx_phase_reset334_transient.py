#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Hosted-only source derivation and refusal controls; never a DUT pass."""
import ast,copy,json,math,os
from pathlib import Path
import tx_phase_reset334_transient_support as support
import cloud_tx_phase_reset334_transient as lifecycle
ROOT=Path(__file__).resolve().parents[1]
def rejected(name,fn):
    try:fn()
    except (AssertionError,KeyError,TypeError,ValueError):return name
    raise AssertionError('Accepted corruption '+name)
def derivation():
    d=json.loads((ROOT/'scripts/tx-phase-reset334-transient-source-delta.json').read_text())
    original=(ROOT/d['baseline_path']).read_text();candidate=(ROOT/d['candidate_path']).read_text()
    assert support.digest(original)==d['baseline_sha256']and support.digest(candidate)==d['candidate_sha256']
    changed=original
    for edit in d['edits']:
        assert changed.count(edit['before'])==edit['count']
        changed=changed.replace(edit['before'],edit['after'])
    assert changed==candidate
    reversed_text=candidate
    for edit in reversed(d['edits']):
        assert edit['after']and reversed_text.count(edit['after'])==edit['count']
        reversed_text=reversed_text.replace(edit['after'],edit['before'])
    assert reversed_text==original
    old=ast.parse(original);new=ast.parse(candidate)
    preserved={}
    for name in ('digest','api','byte_hash','raw_state','verify_prefix','spice_lines'):
        a=next(n for n in old.body if isinstance(n,ast.FunctionDef)and n.name==name)
        b=next(n for n in new.body if isinstance(n,ast.FunctionDef)and n.name==name)
        assert ast.get_source_segment(original,a)==ast.get_source_segment(candidate,b)
        preserved[name]=support.digest(ast.get_source_segment(original,a))
    for name in ('run','state','dump'):
        a=next(n for n in ast.walk(old)if isinstance(n,ast.FunctionDef)and n.name==name)
        b=next(n for n in ast.walk(new)if isinstance(n,ast.FunctionDef)and n.name==name)
        assert ast.get_source_segment(original,a)==ast.get_source_segment(candidate,b)
        preserved['main.'+name]=support.digest(ast.get_source_segment(original,a))
    return dict(reversible_edits=len(d['edits']),preserved_functions=preserved,no_native_execution=True)
def copy_controls():
    import subprocess,sys,tempfile
    source=(ROOT/'scripts/cloud_tx_phase_reset334_transient.py').read_text()
    assignments=[n for n in ast.walk(ast.parse(source))if isinstance(n,ast.Assign)and
      any(isinstance(t,ast.Name)and t.id=='compare'for t in n.targets)]
    assert len(assignments)==1
    program=ast.literal_eval(assignments[0].value)
    pinned=(ROOT/'scripts/run_cloud_tx_layout_repair.py').read_text()
    a=next(n for n in ast.parse(pinned).body if isinstance(n,ast.FunctionDef)and n.name=='sha')
    b=next(n for n in ast.parse(program).body if isinstance(n,ast.FunctionDef)and n.name=='sha')
    assert ast.get_source_segment(pinned,a)==ast.get_source_segment(program,b)
    bad=[]
    with tempfile.TemporaryDirectory(dir=ROOT)as directory:
        left=Path(directory)/'left';right=Path(directory)/'right'
        for root in (left,right):
            (root/'nested').mkdir(parents=True)
            (root/'pages.img').write_bytes(bytes(range(256))*32)
            (root/'nested/core.img').write_bytes(b'actual full inventory\n')
        def check():return subprocess.run([sys.executable,'-c',program,str(left),str(right)],capture_output=True).returncode
        assert check()==0
        for fault in ('checkpoint-changed-byte','checkpoint-missing-file','checkpoint-extra-file'):
            (right/'pages.img').write_bytes((left/'pages.img').read_bytes())
            (right/'nested/core.img').write_bytes((left/'nested/core.img').read_bytes())
            extra=right/'extra.img'
            if extra.exists():extra.unlink()
            if fault=='checkpoint-changed-byte':(right/'pages.img').write_bytes(b'changed'+(left/'pages.img').read_bytes())
            elif fault=='checkpoint-missing-file':(right/'nested/core.img').unlink()
            else:extra.write_bytes(b'extra')
            assert check()!=0,fault;bad.append(fault)
    return bad
def positive_fixture():
    names=['xdut.xd'+str(i)for i in range(318)]
    c=dict(hbt={n:{}for n in names},vectors=['v(n'+str(i)+')'for i in range(4726)],
      instances=[dict(instance=n,physical_role='fixed-'+n,oracle=dict(first_falls=[
        dict(arm_s=1.75e-9,fall_s=2e-9),dict(arm_s=14.03125e-9,fall_s=14.25e-9)]))
        for n in ('xdut','xloadm','xloadq')])
    safety={n:dict(min_post_vce_v=.5,max_whole_abs_vce_v=1.5,max_whole_abs_vbe_v=.9,
      max_whole_abs_ic_per_emitter_a=.002,passed=True)for n in names}
    screens={}
    for instance in c['instances']:
        releases=[]
        for prescribed in instance['oracle']['first_falls']:
            edge=prescribed['fall_s']+50e-12
            releases.append(dict(**prescribed,observed_release_edges_s=[edge],exactly_one=True,before_first_fall=False,
              signed_delay_s=edge-prescribed['fall_s'],within_original_UI_center=True))
        signal=dict(fixed_phase_samples={n:dict(fixed_original_UI_centers=256,minimum_signed_margin_v=.11,
          wrong_sign_samples=0,margin_violations=0,rising_s=[],falling_s=[])for n in ('MP','QP','release')},
          asynchronous_preset_during_running={n:dict(minimum_signed_margin_v=.11,wrong_sign_samples=0)for n in ('MP','QP','release')},
          first_fall_releases=releases,fixed_phase_and_margin_passed=True,preset_passed=True,first_fall_passed=True,
          diagnostic_signal_screen_passed=True,observed_phase_fitted=False,production_startup_or_recovery_removal_qualified=False)
        screens[instance['instance']]=dict(signals=signal,pair_ranges={},physical_role=instance['physical_role'])
    measurement=dict(hbt_safety=safety,all318_HBT_safety_passed=True,all_three_fixed_phase_screens_passed=True,
      three_model_screens=screens,diagnostic_screen_passed=True,**support.paths.bench.FLAGS)
    row=dict(returncode=0,diagnostics=[],solver={'status':'PASS_NATIVE_SOLVER_OPTION_READBACK'},
      flags=dict(actual_HBT_targets=318,uniform_OFF_value=1,all_native_flags_read_back=True),
      zero_source_op=dict(rows=1,columns=4726,all_saved_electrical_and_thermal_states_zero=True),
      capture=dict(columns=4727,complete_unmodified_rows=True,logical_vector_order=['time',*c['vectors']],
        start_s=0.,end_s=34e-9,max_step_s=.3125e-12),measurement=measurement,errors=[])
    assert support.gate(row,c)['passed']
    return row,c
def controls():
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    m=support.methods();der=derivation();old=support.zero.source_controls();portable=lifecycle.controls()
    assert portable['count']==22
    op_raw=(ROOT/'docs/evidence/tx-phase-reset334-zero-op-full-result-20261025.json').read_bytes()
    assert support.digest(op_raw)==support.OP['summary_sha256']
    d=json.loads(op_raw)
    run=dict(id=support.OP['run'],head_sha=support.OP['head'],run_attempt=1,status='completed',conclusion='success',
      path='.github/workflows/tx-phase-reset334-zero-op-cloud.yml')
    assert support.validate_OP(d,run)
    faults=[]
    mutations=[
      ('OP-live',lambda a,r:r.update(status='in_progress')),('OP-failed',lambda a,r:r.update(conclusion='failure')),
      ('OP-source',lambda a,r:r.update(head_sha='0'*40)),('OP-wrong-run',lambda a,r:r.update(id=1)),
      ('OP-summary-source',lambda a,r:a.update(source_head='0'*40)),('OP-missing-case',lambda a,r:a['cases'].pop('n-initial-low')),
      ('OP-prior-error',lambda a,r:a.update(validation_errors=['retained'])),
      ('OP-nonnative-flags',lambda a,r:a['cases']['p-initial-high']['flags'].update(all_native_flags_read_back=False)),
      ('OP-missing-column',lambda a,r:a['cases']['p-initial-high']['zero_source_op'].update(columns=4725)),
      ('OP-nonzero-state',lambda a,r:a['cases']['p-initial-high']['zero_source_op'].update(all_saved_electrical_and_thermal_states_zero=False)),
      ('OP-raw-identity',lambda a,r:a['outputs'].update({'p-initial-high/op.raw':'0'*64})),
      ('OP-claimed-transient',lambda a,r:a.update(transient_executed=True))]
    for name,edit in mutations:
        a,b=copy.deepcopy((d,run));edit(a,b)
        faults.append(rejected(name,lambda:support.validate_OP(a,b)))
    row,c=positive_fixture()
    first=lambda r:r['measurement']['hbt_safety']['xdut.xd0']
    screen=lambda r:r['measurement']['three_model_screens']['xloadm']['signals']
    mutations=[
      ('safety-missing-device',lambda r:r['measurement']['hbt_safety'].pop('xdut.xd0')),
      ('safety-renamed-device',lambda r:r['measurement']['hbt_safety'].update({'wrong':r['measurement']['hbt_safety'].pop('xdut.xd0')})),
      ('safety-low-VCE-hidden-by-pass-flag',lambda r:first(r).update(min_post_vce_v=.399)),
      ('safety-high-VCE-hidden-by-pass-flag',lambda r:first(r).update(max_whole_abs_vce_v=1.601)),
      ('safety-high-VBE-hidden-by-pass-flag',lambda r:first(r).update(max_whole_abs_vbe_v=1.001)),
      ('safety-high-Ic-hidden-by-pass-flag',lambda r:first(r).update(max_whole_abs_ic_per_emitter_a=.003001)),
      ('safety-NaN',lambda r:first(r).update(min_post_vce_v=float('nan'))),
      ('missing-child',lambda r:r['measurement']['three_model_screens'].pop('xloadm')),
      ('wrong-child-role',lambda r:r['measurement']['three_model_screens']['xloadm'].update(physical_role='wrong')),
      ('fewer-fixed-centers',lambda r:screen(r)['fixed_phase_samples']['MP'].update(fixed_original_UI_centers=255)),
      ('under100mV-hidden-by-pass-flag',lambda r:screen(r)['fixed_phase_samples']['MP'].update(minimum_signed_margin_v=.099)),
      ('wrong-fixed-sign',lambda r:screen(r)['fixed_phase_samples']['QP'].update(wrong_sign_samples=1)),
      ('preset-under100mV',lambda r:screen(r)['asynchronous_preset_during_running']['MP'].update(minimum_signed_margin_v=.099)),
      ('fitted-phase',lambda r:screen(r).update(observed_phase_fitted=True)),
      ('changed-prescribed-fall',lambda r:screen(r)['first_fall_releases'][0].update(fall_s=2.01e-9)),
      ('false-delay-summary',lambda r:screen(r)['first_fall_releases'][0].update(signed_delay_s=0)),
      ('late-edge-hidden-by-pass-flag',lambda r:screen(r)['first_fall_releases'][0].update(
        observed_release_edges_s=[2e-9+63e-12],signed_delay_s=(2e-9+63e-12)-2e-9)),
      ('extra-release-edge',lambda r:screen(r)['first_fall_releases'][0]['observed_release_edges_s'].append(2.1e-9)),
      ('old106-flags',lambda r:r['flags'].update(actual_HBT_targets=106)),
      ('extra-OP-row',lambda r:r['zero_source_op'].update(rows=2)),
      ('partial-capture',lambda r:r['capture'].update(complete_unmodified_rows=False)),
      ('missing-saved-vector',lambda r:r['capture']['logical_vector_order'].pop()),
      ('time-not-column-zero',lambda r:r['capture']['logical_vector_order'].reverse()),
      ('short-transient',lambda r:r['capture'].update(end_s=33e-9)),
      ('relaxed-step',lambda r:r['capture'].update(max_step_s=1e-12)),
      ('retained-diagnostic',lambda r:r.update(diagnostics=['warning'])),
      ('retained-error',lambda r:r.update(errors=['original failure']))]
    for name,edit in mutations:
        a=copy.deepcopy(row);edit(a)
        assert not support.gate(a,c)['passed'],name;faults.append(name)
    identity=dict(kernel_release='exact',architecture='x86_64',cpu_flags=['a','b'],CRIU_source='c'*40,
      CRIU_binary_sha256='d'*64,CRIU_version='4.2.1')
    assert support.compatible(identity,identity)
    for key in identity:
        other=copy.deepcopy(identity);other[key]=['different']if isinstance(other[key],list)else'different'
        faults.append(rejected('runtime-'+key,lambda:support.compatible(identity,other)))
    faults.extend(copy_controls())
    assert len(faults)==48
    return dict(status='PASS_PHYSICAL334_TRANSIENT_SOURCE_CONTROLS_NOT_DUT_ACCEPTANCE',
      reversible_source_derivation=der,inherited_zero_OP_controls=old,portable_controls=portable,
      negative_controls=faults,protected_files=len(m['protected']),source_fixture_is_synthetic=True,
      actual_prior_OP_summary_sha256=support.OP['summary_sha256'],native_simulator_invoked=False,
      transient_executed=False,**support.FLAGS)
if __name__=='__main__':print(json.dumps(controls(),indent=2,allow_nan=False))
