#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Fresh current-model portable34ns source wrapper; no transient until exact reviewed activation."""
import argparse,copy,hashlib,json,os,subprocess,sys,traceback
from pathlib import Path
import ensure_cloud_tested_source_release as release
import wait_cloud_tested_source_release as waiter
ROOT=Path(__file__).resolve().parents[1]
METHOD=ROOT/'scripts/tx-phase-reset334-tail-m4-transient-methods.json'
ORIGINAL='scripts/cloud_tx_phase_reset334_transient.py'
ORIGINAL_SHA='db0108b0b553d24d1ce8d4813806f41821bbf607053538a2ebe59127629eb0f0'
WORKFLOW='.github/workflows/tx-phase-reset334-tail-m4-transient-cloud.yml'
EDITS=[{'before': 'import tx_phase_reset334_transient_support as review', 'after': 'from tx_phase_reset334_tail_m4_transient_adapter import session\nreview=session()', 'count': 1}, {'before': 'tx-phase-reset334-transient-native-', 'after': 'tx-phase-reset334-tail-m4-transient-native-', 'count': 4}, {'before': 'codex/tx-clock-phase-parent', 'after': 'codex/phase318-saved-capture-diagnosis', 'count': 2}, {'before': 'tx-phase-reset334-transient-cloud.yml', 'after': 'tx-phase-reset334-tail-m4-transient-cloud.yml', 'count': 2}, {'before': '.reset334-portable-stage-', 'after': '.reset334-tail-m4-portable-stage-', 'count': 1}, {'before': 'cloud-tx-phase-reset334-prepared-', 'after': 'cloud-tx-phase-reset334-tail-m4-prepared-', 'count': 1}, {'before': "        r['original_parent_TX_rejection']=proof['original_parent_TX_rejection']", 'after': "        r['original_parent_TX_rejection']=proof['original_parent_TX_rejection']\n        r.update(original17_HBT_rejection=proof['original17_HBT_rejection'],prior_four_tail_rejection=proof['prior_four_tail_rejection'],current_RC_model_hashes=proof['current_models'],old_R_rescaled=False,geometry_generation_executed=False,new_extraction_performed=False)", 'count': 1}, {'before': "                a=next(a for a in rel['assets']if a['name'].endswith(suffix))", 'after': "                expected=spec['group']+'-'+str(spec['run'])+'-1'+suffix\n                matches=[a for a in rel['assets']if a['name']==expected];assert len(matches)==1\n                a=matches[0]", 'count': 1}]

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def group(stage,case):
    assert stage in ('initial','cross')and case=='p-initial-high'
    return 'tx-phase-reset334-tail-m4-transient-native-'+stage+'-'+case

def methods():
    assert os.environ.get('GITHUB_ACTIONS')=='true'and os.environ.get('RUNNER_ENVIRONMENT')=='github-hosted'
    assert os.environ.get('GITHUB_REPOSITORY')=='Melihakbulut221/nssoc'and os.environ.get('GITHUB_RUN_ATTEMPT')=='1'
    m=json.loads(METHOD.read_bytes())
    for p,h in m['protected'].items():assert sha(ROOT/p)==h,p
    assert m['source_unit_complete']is True,'Incomplete source unit is not runnable'
    for key in ('source_controls_authorized','native_transient_authorized','simulation_authorized','native_continuation_authorized','geometry_generation_authorized','extraction_authorized','other_cases_authorized'):
        assert type(m[key])is bool,key
    assert m['segment_seconds']==13200 and m['initial_case']=='p-initial-high'
    assert m['original_minimum_VCE_v']==.4 and m['original_step_s']==.3125e-12 and m['original_stop_s']==34e-9
    assert m['original_UI_samples']==[.3,.5,.7]
    assert m['original_first_fall_limit_s']==62.5e-12 and m['minimum_signed_margin_v']==.1
    assert m['native_transient_authorized']is m['simulation_authorized']
    for key in ('geometry_generation_authorized','extraction_authorized','other_cases_authorized'):assert m[key]is False
    return m

def completed_controls(m):
    c=m['completed_source_controls'];assert isinstance(c,dict)
    for p,h in c['proof_files'].items():assert m['protected'][p]==h and sha(ROOT/p)==h
    tested=json.loads((ROOT/c['tested_method_path']).read_bytes())
    assert set(m['protected'])==set(tested['protected'])|set(c['proof_files'])
    assert all(m['protected'][p]==h for p,h in tested['protected'].items())
    normalized=copy.deepcopy(m)
    normalized.update(native_transient_authorized=False,simulation_authorized=False,native_continuation_authorized=False,completed_source_controls=None)
    normalized['protected']=tested['protected'];assert normalized==tested
    r=json.loads((ROOT/c['result_path']).read_bytes());assert r['status']=='PASS_CURRENT_TAIL_M4_PORTABLE_SOURCE_CONTROLS_ONLY'
    run=release.api('actions/runs/'+str(c['run']));job=release.api('actions/jobs/'+str(c['job']))
    assert run['id']==job['run_id']==c['run']and job['id']==c['job']
    assert run['head_sha']==job['head_sha']==c['head']and run['run_attempt']==job['run_attempt']==1
    assert run['status']==job['status']=='completed'and run['conclusion']==job['conclusion']=='success'
    assert run['path']==WORKFLOW and run['head_branch']=='codex/phase318-saved-capture-diagnosis'and job['name']=='source-controls'
    log=subprocess.check_output(['gh','api','--allow-escape-sequences','repos/Melihakbulut221/nssoc/actions/jobs/'+str(c['job'])+'/logs'])
    assert log==(ROOT/c['log_path']).read_bytes()
    return dict(run=c['run'],job=c['job'],head=c['head'],all_tested_source_pins_preserved=True,log_sha256=hashlib.sha256(log).hexdigest())

def preflight(stage,case):
    m=methods();assert m['native_transient_authorized']is True
    assert os.environ.get('ImageOS')=='ubuntu24'
    if stage=='cross':assert m['native_continuation_authorized']is True
    name=group(stage,case);proof=completed_controls(m);waiter.wait(name,os.environ)
    tag,head=release.context(name,os.environ)
    result=release.validate_release(release.api('releases/tags/'+tag),release.api('git/ref/tags/'+tag),tag,head)
    assert not result['existing_assets'];result['completed_controls']=proof
    return result

def derived_program(text=None):
    if text is None:text=(ROOT/ORIGINAL).read_text()
    assert hashlib.sha256(text.encode()).hexdigest()==ORIGINAL_SHA
    changed=text
    for e in EDITS:
        assert changed.count(e['before'])==e['count'];changed=changed.replace(e['before'],e['after'])
    reversed_text=changed
    for e in reversed(EDITS):
        assert reversed_text.count(e['after'])==e['count'];reversed_text=reversed_text.replace(e['after'],e['before'])
    assert reversed_text==text
    return changed,dict(original_sha256=ORIGINAL_SHA,generated_sha256=hashlib.sha256(changed.encode()).hexdigest(),
      literal_edits=EDITS,reversed_byte_exact=True,original_Docker_CRIU_13200s_lifecycle_preserved=True)

def program_namespace():
    text,proof=derived_program()
    ns=dict(__name__='current_TAIL_M4_portable_lifecycle',__file__=str(Path(__file__)))
    exec(compile(text,'<current-TAIL-M4-portable-lifecycle>','exec'),ns)
    return ns,proof


def preserve_partial(path):
    """Keep a preexisting or failed atomic fragment under a unique evidence name."""
    assert path.is_file()and not path.is_symlink(),'Terminal fragment is not a regular file'
    number=0
    while True:
        destination=path.with_name(path.name+'.preserved-'+str(number))
        if not destination.exists()and not destination.is_symlink():break
        number+=1
    path.replace(destination)
    return destination.name

def write_terminal(out,result):
    temporary=out/'result.json.writing'
    assert not temporary.exists()and not temporary.is_symlink(),'Terminal fragment must be preserved before another write'
    with temporary.open('x')as stream:
        json.dump(result,stream,indent=2,allow_nan=False);stream.write('\n')
    temporary.replace(out/'result.json')

def output_inventory(out):
    files={};errors=[]
    for path in sorted(out.rglob('*')):
        if path==out/'result.json':continue
        try:
            assert not path.is_symlink(),'Symlink in native output'
            assert path.is_file()or path.is_dir(),'Nonregular native output'
            if path.is_file():files[str(path.relative_to(out))]=sha(path)
        except BaseException as error:
            errors.append(dict(phase='terminal-output-inventory',path=str(path.relative_to(out)),error=repr(error)))
    return files,errors


def finalize(out,preflight,derivation,primary_error=None,primary_traceback=None):
    """Keep full original result/partials, then save terminal failure even if encoding fails."""
    out.mkdir(parents=True,exist_ok=True)
    path=out/'result.json';raw=None;parsed=None;errors=[]
    if path.exists():
        try:
            assert path.is_file()and not path.is_symlink(),'Native result is not a regular file'
            candidate=path.read_bytes()
            saved=out/'native-lifecycle-result.json'
            if saved.exists()or saved.is_symlink():
                previous=preserve_partial(saved)
                errors.append(dict(phase='previous-native-result-copy',preserved_path=previous,
                    error='A preexisting native result copy was preserved'))
            saved.write_bytes(candidate);raw=candidate
            parsed=json.loads(raw);assert isinstance(parsed,dict),'Native result is not an object'
        except BaseException as error:
            errors.append(dict(phase='native-result-read-or-parse',error=repr(error),traceback=traceback.format_exc()))
    else:errors.append(dict(phase='native-result',error='Native lifecycle result was not produced'))
    temporary=out/'result.json.writing'
    if temporary.exists()or temporary.is_symlink():
        try:
            preserved=preserve_partial(temporary)
            errors.append(dict(phase='previous-terminal-fragment',preserved_path=preserved,
                error='A preexisting terminal write fragment was preserved'))
        except BaseException as error:
            errors.append(dict(phase='previous-terminal-fragment',error=repr(error)))
    result=dict(parsed)if isinstance(parsed,dict)else{}
    if primary_error is None and result.get('status')not in (
        'SAVED_PHYSICAL334_THREE_MODEL_NATIVE_PROCESS_REQUIRES_CONTINUATION_AND_FULL_REVIEW',
        'COMPLETE_PHYSICAL334_THREE_MODEL_FULL_NATIVE_CAPTURE_REQUIRES_REVIEW_AND_FULL_PHY',
        'REJECTED_PHYSICAL334_THREE_MODEL_ORIGINAL_LOADED_GATES'):
        errors.append(dict(phase='native-terminal-state',error='Native lifecycle did not produce a terminal state',
            observed_status=result.get('status')))
    result.update(source_head=os.environ.get('GITHUB_SHA'),run_id=int(os.environ.get('GITHUB_RUN_ID','0')),
      run_attempt=int(os.environ.get('GITHUB_RUN_ATTEMPT','0')),
      current_source_release_prerequisite=preflight,current_lifecycle_derivation=derivation,
      native_lifecycle_result_present=raw is not None,
      native_lifecycle_result_sha256=None if raw is None else hashlib.sha256(raw).hexdigest(),
      native_lifecycle_result_bytes=None if raw is None else len(raw),
      native_lifecycle_result_raw_path=None if raw is None else 'native-lifecycle-result.json',
      wrapper_primary_error=None if primary_error is None else repr(primary_error),
      wrapper_primary_traceback=primary_traceback,
      scope='Only three current tail-M4 RC macros under the exact original external fixture; original17 and prior4 HBT failures retained; no all31/PLL/fullPHY acceptance.')
    try:methods()
    except BaseException as error:
        errors.append(dict(phase='terminal-protected-source-integrity',error=repr(error),traceback=traceback.format_exc()))
    files,inventory_errors=output_inventory(out);errors.extend(inventory_errors)
    result['outputs']=files;result['wrapper_finalization_errors']=errors
    if primary_error is not None or errors:
        if not str(result.get('status','')).startswith('REJECTED_'):result['status']='FAIL_OR_ERROR'
        result['electrical_screen_passed']=False
    result['wrapper_terminal_complete']=not errors
    try:
        write_terminal(out,result)
    except BaseException as error:
        errors.append(dict(phase='terminal-result-write',error=repr(error),traceback=traceback.format_exc()))
        if temporary.exists()or temporary.is_symlink():
            try:preserve_partial(temporary)
            except BaseException as partial_error:
                errors.append(dict(phase='terminal-fragment-preservation',error=repr(partial_error)))
        files,inventory_errors=output_inventory(out);errors.extend(inventory_errors)
        # Full native observations remain byte-exact in native-lifecycle-result.json.
        # This small envelope never converts an incomplete encoding into a pass.
        result=dict(status='FAIL_OR_ERROR',electrical_screen_passed=False,wrapper_terminal_complete=False,
          source_head=os.environ.get('GITHUB_SHA'),run_id=os.environ.get('GITHUB_RUN_ID'),
          wrapper_primary_error=None if primary_error is None else repr(primary_error),
          wrapper_primary_traceback=primary_traceback,wrapper_finalization_errors=errors,
          native_lifecycle_result_present=raw is not None,
          native_lifecycle_result_raw_path=None if raw is None else 'native-lifecycle-result.json',
          native_lifecycle_result_sha256=None if raw is None else hashlib.sha256(raw).hexdigest(),
          native_lifecycle_result_bytes=None if raw is None else len(raw),outputs=files,
          full_native_observations_preserved_by_raw_result=raw is not None,
          scope='Terminal failure envelope only; full original result and all available write fragments retained.')
        write_terminal(out,result)
    return result


def main(stage,case):
    pre=None;derivation=None;primary=None;trace=None;tb=None;old=sys.argv;terminal=None
    out=ROOT/('cloud-'+group(stage,case));result=None
    try:
        pre=preflight(stage,case);ns,derivation=program_namespace()
        sys.argv=[str(Path(__file__)),'--stage',stage,'--case',case]
        ns['main']()
    except BaseException as error:
        primary=error;tb=error.__traceback__;trace=traceback.format_exc()
    finally:
        sys.argv=old
        try:result=finalize(out,pre,derivation,primary,trace)
        except BaseException as error:
            terminal=error
            print(json.dumps(dict(status='FAIL_OR_ERROR',terminal_result_write_failed=True,
                primary_error=None if primary is None else repr(primary),terminal_error=repr(error)),
                allow_nan=False),file=sys.stderr,flush=True)
    if primary is not None:raise primary.with_traceback(tb)
    if terminal is not None:raise terminal
    if result['wrapper_finalization_errors']:
        raise RuntimeError('Portable native terminal finalization failed; complete available evidence preserved')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--controls',action='store_true');p.add_argument('--preflight',action='store_true')
    p.add_argument('--stage',choices=('initial','cross'),default='initial');p.add_argument('--case',default='p-initial-high')
    args=p.parse_args()
    assert not(args.controls and args.preflight)
    if args.controls:
        assert methods()['source_controls_authorized']is True
        from check_tx_phase_reset334_tail_m4_transient import controls
        print(json.dumps(controls(),indent=2,allow_nan=False),flush=True)
    elif args.preflight:print(json.dumps(preflight(args.stage,args.case),indent=2,allow_nan=False))
    else:main(args.stage,args.case)
