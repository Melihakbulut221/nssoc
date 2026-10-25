#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Physical334 three-model transient support; fixture scope, no full-PHY claim."""
import copy,json,math,os,platform,re,traceback
from pathlib import Path
import tx_phase_reset334_loaded_native_adapter as initialization
import tx_phase_reset334_zero_op_runtime as paths
import cloud_tx_phase_reset334_zero_op as zero
import cloud_tx_phase_reset334_loaded_preparation as preparation
import cloud_tx_phase_async_preset_intrinsic as native
import cloud_tx_stream as stream
import compare_cloud_routed_endpoints as reports
import ensure_cloud_tested_source_release as publication
ROOT=Path(__file__).resolve().parents[1]
METHOD='scripts/tx-phase-reset334-transient-methods.json'
OP=dict(run=40175085823,head='63a4c761e08442f037027916233acb78f4dfd8c1',summary_asset=674456611,
 summary_sha256='1ea5094100e4815c4ca26dcefcb7457c5a070b1fd849107f9c88cd3293258929')
LABELS=('p-initial-high','p-initial-low','n-initial-high','n-initial-low')
FLAGS=dict(all31_clock_tree_accepted=False,actual_PLL_waveform_replayed=False,PLL_connected=False,
 full_PHY_accepted=False,mainchip_integrated=False,routed_parent_accepted=False,physical_reset_distribution_accepted=False)
def digest(v):return initialization.digest(v)
def write(p,d):Path(p).write_text(json.dumps(d,indent=2,allow_nan=False)+'\n')
def methods():
    m=json.loads((ROOT/METHOD).read_text())
    for p,h in m['protected'].items():assert digest((ROOT/p).read_bytes())==h,p
    assert m['segment_seconds']==13200 and m['initial_case']=='p-initial-high'
    assert m['original_first_fall_limit_s']==paths.bench.original.UI/2==62.5e-12
    assert m['native_engine_sha256']==native.ENGINE_SHA
    return m
def validate_OP(d,run):
    assert run['id']==OP['run']and run['head_sha']==OP['head']and run['run_attempt']==1
    assert run['status']=='completed'and run['conclusion']=='success'
    assert run['path']=='.github/workflows/tx-phase-reset334-zero-op-cloud.yml'
    assert d['source_head']==OP['head']and d['run_id']==OP['run']
    assert d['status']=='PASS_FOUR_FRESH318_ZERO_OPS_NOT_TRANSIENT_OR_PHASE_ACCEPTANCE'
    assert d['validation_errors']==[]and d['sources_unchanged']and d['all_four_expanded_zero_OPs_passed']
    assert set(d['cases'])==set(LABELS)and d['native_simulator_invoked']and d['runtime_installed']
    assert all(d[k]is False for k in ('transient_executed','electrical_phase_accepted','all31_clock_tree_accepted','PLL_connected','full_PHY_accepted'))
    for label,row in d['cases'].items():
        assert row['complete']and row['passed']and row['errors']==[]
        assert paths.gate(row)['passed']and row['zero_OP_gate']==paths.gate(row)
        assert row['expected_HBT_count']==318 and row['expected_saved_vectors']==4726
        assert re.fullmatch('[0-9a-f]{64}',row['zero_source_op']['sha256'])
        assert row['contract_sha256']==d['outputs'][label+'/contract.json']
        assert row['native_log_sha256']==d['outputs'][label+'/native.log']
        assert row['zero_source_op']['sha256']==d['outputs'][label+'/op.raw']
        assert row['path_binding']['byte_exact_reversal']and len(row['path_binding']['six_path_cards'])==6
    assert d['original_parent_TX_rejection']['electrical_screen_passed']is False
    return True
def runtime_identity(build):
    flags=[]
    for line in Path('/proc/cpuinfo').read_text().splitlines():
        if line.startswith('flags')and ':'in line:
            flags=line.split(':',1)[1].split();break
    assert flags and len(flags)==len(set(flags))
    return dict(kernel_release=platform.release(),architecture=platform.machine(),cpu_flags=sorted(flags),
      CRIU_source=build['source_commit'],CRIU_binary_sha256=build['binary_sha256'],CRIU_version=build['version'])
def compatible(current,prior):
    assert set(current)==set(prior)=={'kernel_release','architecture','cpu_flags','CRIU_source','CRIU_binary_sha256','CRIU_version'}
    assert current==prior,'Kernel/CPU/CRIU identity changed; preserve capsule instead of restarting'
    return True
def prepare(label,prepared_root,out,group):
    m=methods();assert m['native_transient_authorized']is True
    assert label==m['initial_case']=='p-initial-high','Other cases require separate evidence-based activation'
    tag,head=publication.context(group,os.environ)
    release=publication.validate_release(publication.api('releases/tags/'+tag),publication.api('git/ref/tags/'+tag),tag,head)
    op_raw=preparation.asset(OP['summary_asset'],OP['summary_sha256'])
    op=json.loads(op_raw);validate_OP(op,preparation.api('actions/runs/'+str(OP['run'])))
    (out/'qualified-zero-OP.summary.json').write_bytes(op_raw)
    spec=initialization.PREPARATION
    old=preparation.api('actions/runs/'+str(spec['run']))
    assert old['head_sha']==spec['head']and old['run_attempt']==1 and old['status']=='completed'and old['conclusion']=='success'
    summary_raw=preparation.asset(spec['summary_asset'],spec['summary_sha256']);summary=json.loads(summary_raw)
    (out/'qualified-preparation.summary.json').write_bytes(summary_raw)
    prepared_root.mkdir(exist_ok=False)
    selected=['cases/'+label+'/'+n for n in ('bench.cir','contract.json')]
    selected+=['qualified-binding/qualified-rc/'+s+'/composition/reset334-wire.spice'for s in ('p','n')]
    restored,proof=reports.restore_report('tx-phase-reset334-loaded-preparation',spec['run'],
      spec['summary_sha256'],spec['parts_sha256'],prepared_root/'prepared',selected)
    assert restored==summary
    base=(prepared_root/'prepared/cases'/label/'bench.cir').read_text()
    c=json.loads((prepared_root/'prepared/cases'/label/'contract.json').read_bytes())
    initialization.prepared_contract(label,base,c,summary_raw)
    assert op['cases'][label]['contract_sha256']==digest(json.dumps(c,indent=2,allow_nan=False)+'\n')
    models_at={s:prepared_root/'prepared/qualified-binding/qualified-rc'/s/'composition/reset334-wire.spice'for s in ('p','n')}
    models={s:p.read_text()for s,p in models_at.items()}
    native.OUT=prepared_root/'runtime';native.OUT.mkdir()
    engine,libs,engine_proof=native.restore()
    assert engine_proof['engine_sha256']==op['runtime_and_models']['engine_sha256']==native.ENGINE_SHA
    assert engine_proof['model_manifest']==op['runtime_and_models']['model_manifest']
    op_deck,path_proof=paths.runtime_deck(label,base,c,summary_raw,models,models_at,libs/'models',libs/'r3_cmc.osdi')
    rows=base.splitlines(keepends=True)
    for edit in path_proof['six_path_cards']:
        assert rows[edit['line']]==edit['old'];rows[edit['line']]=edit['new']
    runtime_base=''.join(rows);assert digest(runtime_base)==path_proof['runtime_base_sha256']
    a=initialization.adapters()
    assert a.op_only(runtime_base,c,True)==op_deck
    deck=a.initialized_deck(runtime_base,c)
    assert deck.replace(a.flag_block(c,True),'')==runtime_base
    assert [r for r in deck.splitlines()if r.startswith('V')]==[r for r in base.splitlines()if r.startswith('V')]
    assert len([r for r in deck.splitlines()if r.startswith('V')])==5
    assert [r for r in deck.splitlines()if r.startswith('save ')]==[r for r in base.splitlines()if r.startswith('save ')]
    assert [r for r in deck.splitlines()if r.startswith('.tran ')]==[r for r in base.splitlines()if r.startswith('.tran ')]
    assert deck.count('\nrun wave.raw\n')==1 and not re.search(r'(?im)^\s*\.(?:ic|nodeset)\b|\buic\b',deck)
    case=prepared_root/'native';case.mkdir()
    (case/'bench.cir').write_text(deck);write(case/'contract.json',c);(case/'spinit').write_text('set num_threads=1\n')
    protected={str(p):digest(p.read_bytes())for p in (case/'bench.cir',case/'contract.json',case/'spinit',*models_at.values())}
    for name,record in engine_proof['model_manifest']['files'].items():
        p=libs/name;assert p.is_file()and p.stat().st_size==record['bytes']and digest(p.read_bytes())==record['sha256']
        protected[str(p)]=record['sha256']
    for p in models_at.values():assert digest(p.read_bytes())in paths.bench.binding.MODELS.values()
    prepared=dict(protected_inputs=protected,outputs={'native/'+n:digest((case/n).read_bytes())for n in ('bench.cir','contract.json','spinit')})
    proof.update(zero_OP_run=OP['run'],zero_OP_summary_sha256=OP['summary_sha256'],path_binding=path_proof,
      full_initialized_deck_sha256=digest(deck),runtime_models=engine_proof,release_prerequisite=release,
      original_parent_TX_rejection=summary['original_parent_TX_rejection'])
    assert not proof['original_parent_TX_rejection']['electrical_screen_passed']
    return prepared,proof,c,engine,spec

def measurement_checks(measurement,c):
    """Inspect every actual numerical row and prescribed event, not summary booleans."""
    h=measurement.get('hbt_safety',{});s=measurement.get('three_model_screens',{})
    checks=dict(exact318_native_identity=set(h)==set(c['hbt'])and len(h)==318,
      exact_three_physical_roles=set(s)=={p['instance']for p in c['instances']}=={'xdut','xloadm','xloadq'},
      no_claimed_full_PHY=all(measurement.get(k)is False for k in paths.bench.FLAGS))
    hbt_good=checks['exact318_native_identity'];phase_good=checks['exact_three_physical_roles']
    for name in c['hbt']:
        row=h.get(name,{})
        try:
            values=[row[k]for k in ('min_post_vce_v','max_whole_abs_vce_v','max_whole_abs_vbe_v','max_whole_abs_ic_per_emitter_a')]
            hbt_good &= all(type(v)in(int,float)and math.isfinite(v)for v in values)
            hbt_good &= row['passed']is True and values[0]>=.4 and 0<=values[1]<=1.6 and 0<=values[2]<=1 and 0<=values[3]<=.003
        except (KeyError,TypeError):hbt_good=False
    for spec in c['instances']:
        try:
            row=s[spec['instance']];signals=row['signals']
            assert row['physical_role']==spec['physical_role']
            assert signals['observed_phase_fitted']is False and signals['production_startup_or_recovery_removal_qualified']is False
            fixed=signals['fixed_phase_samples'];preset=signals['asynchronous_preset_during_running']
            assert set(fixed)==set(preset)=={'MP','QP','release'}
            for r in fixed.values():
                assert r['fixed_original_UI_centers']==256 and r['wrong_sign_samples']==r['margin_violations']==0
                assert math.isfinite(r['minimum_signed_margin_v'])and r['minimum_signed_margin_v']>=.1
            for r in preset.values():
                assert r['wrong_sign_samples']==0 and math.isfinite(r['minimum_signed_margin_v'])and r['minimum_signed_margin_v']>=.1
            release=signals['first_fall_releases'];assert len(release)==len(spec['oracle']['first_falls'])==2
            for observed,prescribed in zip(release,spec['oracle']['first_falls'],strict=True):
                assert all(observed[k]==v for k,v in prescribed.items())
                edges=observed['observed_release_edges_s'];assert len(edges)==1 and math.isfinite(edges[0])
                delay=edges[0]-prescribed['fall_s']
                assert observed['signed_delay_s']==delay and 0<=delay<=paths.bench.original.UI/2
                assert observed['exactly_one']is True and observed['before_first_fall']is False and observed['within_original_UI_center']is True
            assert all(signals[k]is True for k in ('fixed_phase_and_margin_passed','preset_passed','first_fall_passed','diagnostic_signal_screen_passed'))
        except (KeyError,TypeError,AssertionError,ValueError):phase_good=False
    checks.update(all318_numeric_safety=bool(hbt_good),all_three_fixed_event_metrics=bool(phase_good))
    return checks
def gate(row,c):
    answer=initialization.check_gate(row)
    answer['checks'].update(measurement_checks(row.get('measurement',{}),c))
    capture=row.get('capture',{})
    answer['checks'].update(one_zero_OP=row.get('zero_source_op',{}).get('rows')==1,
      exact_native_vector_identity=capture.get('logical_vector_order')is not None and
        len(capture.get('logical_vector_order',[]))==4727 and set(capture.get('logical_vector_order',[]))=={'time',*c['vectors']},
      original34ns=capture.get('start_s')==0 and capture.get('end_s')is not None and abs(capture['end_s']-34e-9)<1e-18,
      unchanged_native_maxstep=capture.get('max_step_s')is not None and 0<capture['max_step_s']<=.3125e-12*1.00001)
    answer['passed']=all(answer['checks'].values());answer.update(FLAGS)
    answer['scope']='Three actual distributed-RC macros driven by the documented scalar external fixture; not routed31-tree, actual PLL waveform or PHY qualification.'
    answer['original_first_fall_limit_s']=paths.bench.original.UI/2
    answer['separate_31_25ps_requirement_proven']=False
    return answer
def review_capture(case,c,returncode):
    row=dict(returncode=returncode,errors=[])
    log=(case/'native.log').read_text(errors='strict');a=initialization.adapters()
    for key,fn in [
      ('solver',lambda:native.verify_solver_options(log,paths.bench.original.PROFILE)),
      ('diagnostics',lambda:native.native_diagnostics(log,paths.bench.original.PROFILE)),
      ('flags',lambda:a.flags(log,c,True)),
      ('zero_source_op',lambda:native.zero_op(case/'op.raw',c['vectors']))]:
        try:row[key]=fn()
        except BaseException as error:row['errors'].append(dict(stage=key,error=repr(error),traceback=traceback.format_exc()))
    try:
        t,values,capture=stream.read_streamed_wave(case/'wave.raw',c['vectors'],paths.bench.original.STOP,paths.bench.original.STEP)
        row['capture']=capture;row['measurement']=paths.bench.review(t,values,c)
    except BaseException as error:row['errors'].append(dict(stage='full_capture_or_measurement',error=repr(error),traceback=traceback.format_exc()))
    row['gate']=gate(row,c);row['passed']=row['gate']['passed']
    return row
