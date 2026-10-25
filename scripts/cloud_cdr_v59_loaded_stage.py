#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Preserve one original loaded case and its full evidence in a reserved release."""
import argparse,json,os,shutil,subprocess,sys,traceback
from pathlib import Path
import cdr_v59_loaded_admission as a
import cloud_cdr_v59_binding_rc as evidence
import migrate_outputs_to_cloud as publisher
import ensure_cloud_tested_source_release as release
import wait_cloud_tested_source_release as waiter
from cloud_chunked_results import pack,verify_parts
ROOT=a.ROOT
CASES=['nominal_early','nominal_late','hot_early','hot_late','cold_early','cold_late','constant_zero','constant_one','clock_stopped','vi_bias_off']
def context(case,prepare):
    assert case in CASES and type(prepare)is bool
    assert not prepare or case=='nominal_early'
    assert os.environ.get('GITHUB_RUN_ATTEMPT')=='1'
    group='cdr-v59-loaded-'+('preparation'if prepare else case)
    root=ROOT/('cloud-cdr-v59-loaded-'+case)
    transport=ROOT/'hw/soc/out'/('cloud-'+group+'-publication')
    return group,root,transport
def write(path,value):
    tmp=path.with_suffix(path.suffix+'.tmp')
    tmp.write_text(json.dumps(value,indent=2,allow_nan=False)+'\n');tmp.replace(path)
def preflight(case,prepare):
    m=a.methods();group,root,transport=context(case,prepare)
    assert m['preparation_authorized'if prepare else'simulation_authorized']is True
    assert m['stage_publication_wrapper_implemented']is True
    return waiter.wait(group,os.environ)
def validate_result(r,case,prepare,code):
    assert code==0 and r['source_head']==os.environ['GITHUB_SHA']and r['case']==case
    assert r['sources_unchanged']is True
    assert len(r['source_bits'])==256 and len(r['binding_controls']['rejected'])==13
    assert r['current_saved_input_integrity']==dict(files=5549,all_hashes_unchanged=True)
    assert len(r['devices'])==124 and len(r['mos_devices'])==50 and len(r['native_caps'])==7
    assert len(r['binding']['groups']['rppd'])==98 and len(r['binding']['groups']['ptap1'])==221
    assert r['vector_census']['hbt_collector_currents']==124 and r['vector_census']['mos_drain_currents']==50
    assert r['vector_census']['total']==len(r['vectors'])and len(set(r['vectors']))==len(r['vectors'])
    assert all(r[k]is False for k in ('accepted','qualified_pex','full_phy_accepted','cdr_accepted','closed_loop'))
    if prepare:
        assert r['status']=='PASS_PD500_LOADED_PREPARATION_AND13_BINDING_CONTROLS_NO_TRANSIENT'and r['transient_executed']is False
    else:
        assert r['status']=='PASS_WHOLE_MIM_PD500_LOADED_SCREEN_NOT_CLOSED_LOOP_OR_PHY_SIGNOFF'
        assert r['returncode']==0 and not r['diagnostics']and r['native_flags_verified']==124
        assert 0<=r['zero_source_op_maximum']<1e-9
        assert r['actual_fault_detected']if case in ('clock_stopped','vi_bias_off')else r['devices_passed']and r['data_passed']and r['vi']['passed']
    return True
def run_case(case,prepare):
    reservation=preflight(case,prepare);group,root,transport=context(case,prepare)
    assert not root.exists()and not root.is_symlink()and not transport.exists()
    logs=ROOT/'hw/soc/out'/('cloud-'+group+'-controller');logs.mkdir(parents=True,exist_ok=False)
    log=logs/'controller.log';code=None
    command=[sys.executable,str(ROOT/'scripts/cloud_cdr_v59_loaded.py'),'--case',case]
    if prepare:command.append('--prepare-only')
    result=dict(status='RUNNING_CURRENT_V59_LOADED_CASE',source_head=os.environ['GITHUB_SHA'],
      run_id=int(os.environ['GITHUB_RUN_ID']),run_attempt=1,case=case,preparation_only=prepare,
      group=group,reservation=reservation,native_case_passed=False,accepted=False,
      full_phy_accepted=False,cdr_accepted=False,qualified_pex=False,
      geometry_regenerated=False,native_extraction_executed=False,original_electrical_failures_preserved=True)
    try:
        with log.open('wb')as stream:
            code=subprocess.call(command,cwd=ROOT,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'},stdout=stream,stderr=subprocess.STDOUT)
    except BaseException as error:
        result.update(error=repr(error),traceback=traceback.format_exc())
    finally:
        root.mkdir(parents=True,exist_ok=True);assert root.is_dir()and not root.is_symlink()
        result['command']=dict(argv=command,returncode=code)
        if log.is_file():
            target=root/'controller-transport.log'
            with log.open('rb')as src,target.open('xb')as dst:shutil.copyfileobj(src,dst,4*1024**2)
            assert a.sha(log)==a.sha(target);result['command']['log_sha256']=a.sha(log)
        original=root/'result.json';inner=root/'native-controller-result.json'
        if original.exists():
            assert original.is_file()and not original.is_symlink()
            with original.open('rb')as src,inner.open('xb')as dst:shutil.copyfileobj(src,dst,4*1024**2)
            assert a.sha(inner)==a.sha(original)
            result['native_controller_result_sha256']=a.sha(inner)
            try:
                native=json.loads(inner.read_bytes());result['native_status']=native.get('status')
                validate_result(native,case,prepare,code)
                result['current_saved_input_integrity']=a.verify_restored(root);a.methods()
                result.update(status='PASS_CURRENT_V59_LOADED_PREPARATION'if prepare else'PASS_CURRENT_V59_ORIGINAL_LOADED_CASE',
                  native_case_passed=True)
            except BaseException as error:
                result.update(status='REJECTED_OR_FAILED_CURRENT_V59_LOADED_CASE',validation_error=repr(error),validation_traceback=traceback.format_exc())
        else:result.update(status='FAIL_MISSING_NATIVE_CASE_RESULT',native_case_passed=False)
        result['outputs']={str(p.relative_to(root)):a.sha(p)for p in root.rglob('*')if p.is_file()and p!=original}
        write(original,result)
    assert result['native_case_passed']is True,result.get('validation_error',result['status'])
    return result
def publish_existing(case,prepare):
    a.methods();group,root,transport=context(case,prepare)
    waiter.wait(group,os.environ)
    assert not root.is_symlink()
    root.mkdir(parents=True,exist_ok=True);assert root.is_dir()
    for p in root.rglob('*'):assert not p.is_symlink()and(p.is_file()or p.is_dir())
    result=root/'result.json'
    if not result.exists():
        write(result,dict(status='FAIL_BEFORE_NATIVE_CASE_RESULT',source_head=os.environ['GITHUB_SHA'],
          run_id=int(os.environ['GITHUB_RUN_ID']),run_attempt=1,case=case,preparation_only=prepare,
          native_case_passed=False,accepted=False,full_phy_accepted=False,cdr_accepted=False,qualified_pex=False))
    actual=json.loads(result.read_bytes());assert actual['source_head']==os.environ['GITHUB_SHA']
    assert actual['run_id']==int(os.environ['GITHUB_RUN_ID'])and actual['run_attempt']==1
    assert actual['case']==case and actual['preparation_only']is prepare
    assert all(actual[k]is False for k in ('accepted','full_phy_accepted','cdr_accepted','qualified_pex'))
    for name,digest in actual.get('outputs',{}).items():
        relative=Path(name)
        assert name and not relative.is_absolute()and '..'not in relative.parts and str(relative)==name
        path=root/relative;assert path.is_file()and not path.is_symlink()and a.sha(path)==digest
    transport.mkdir(parents=True,exist_ok=False)
    stem=group+'-'+os.environ['GITHUB_RUN_ID']+'-1'
    summary=transport/(stem+'.summary.json');shutil.copyfile(result,summary);assert a.sha(summary)==a.sha(result)
    if summary.stat().st_size<=4*1024**2:evidence.emit(summary,'CDR_V59_LOADED_RESULT')
    else:print(json.dumps(dict(full_result_retained_for_publication=summary.name,bytes=summary.stat().st_size,sha256=a.sha(summary))),flush=True)
    proof=dict(status='RUNNING',original_status=actual['status'],assets=[])
    write(transport/'publication.json',proof)
    try:
        manifest=pack(root,stem,transport,512*1024**2)
        assert manifest['source_directory']==root.name
        assert summary.read_bytes()==result.read_bytes()
        proof['archive']=verify_parts(manifest,transport)
        files=evidence.publication_files(transport,summary,transport/(stem+'.parts.json'),manifest)
        inner=root/'native-controller-result.json'
        if inner.is_file():
            copied=transport/(stem+'.native-result.json');shutil.copyfile(inner,copied)
            assert a.sha(copied)==a.sha(inner);files.append(copied)
        tag,_=release.context(group,os.environ)
        old=publisher.release;publisher.release=evidence.only_reserved(group,os.environ,release.api)
        try:
            for path in files:
                before=a.sha(path);proof['assets'].append(publisher.publish(path,tag));assert a.sha(path)==before
                write(transport/'publication.json',proof)
        finally:publisher.release=old
        proof['status']='PASS_COMPLETE_CURRENT_V59_LOADED_EVIDENCE_PUBLISHED_NOT_ACCEPTANCE'
    except BaseException as error:proof.update(status='FAIL_PUBLICATION',error=repr(error));raise
    finally:write(transport/'publication.json',proof)
    return proof
def main():
    p=argparse.ArgumentParser();p.add_argument('--case',choices=CASES,required=True)
    p.add_argument('--prepare-only',action='store_true')
    modes=p.add_mutually_exclusive_group();modes.add_argument('--preflight',action='store_true');modes.add_argument('--publish',action='store_true')
    args=p.parse_args()
    if args.preflight:result=preflight(args.case,args.prepare_only)
    elif args.publish:result=publish_existing(args.case,args.prepare_only)
    else:result=run_case(args.case,args.prepare_only)
    if args.preflight or args.publish:print(json.dumps(result,indent=2),flush=True)
if __name__=='__main__':main()
