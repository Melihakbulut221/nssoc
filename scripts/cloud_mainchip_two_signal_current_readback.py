#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Owned, supervised selected-text readback; never starts a native CAD process."""
import argparse,copy,json,os,shutil,signal,sys,threading,traceback
from pathlib import Path
import mainchip_original_clock_restoration as c
import cloud_mainchip_original_clock_restoration as base
import cdr_v59_tail_access_runtime as runtime
import mainchip_two_signal_current_readback as capture
ROOT=c.ROOT
OUT=ROOT/'cloud-mainchip-two-signal-current-readback'
TRANSPORT=ROOT/'transport-mainchip-two-signal-current-readback'
METHOD=ROOT/'scripts/mainchip-two-signal-current-readback-methods.json'
GROUP='mainchip-two-signal-current-readback'
LABEL='complete-current-two-signal-text-readback'
DIRECT=('full-saved-report.json','classification-index.json','source-admission.json',
 *['saved/'+p for p in capture.SELECTED if not p.endswith('.def')])
def completed_controls(m):
    proof=m['completed_controls'];assert type(proof)is dict
    paths=proof['proof_paths']
    assert type(paths)is list and len(paths)==len(set(paths))and proof['tested_method']in paths
    assert all(p in m['protected']for p in paths)
    tested=capture.value(c.regular(ROOT/proof['tested_method']).read_bytes())
    assert tested['source_controls_authorized']is True and tested['cloud_readback_authorized']is False
    assert tested['completed_controls']is None
    assert all(m['protected'].get(p)==h for p,h in tested['protected'].items())
    assert set(m['protected'])-set(tested['protected'])==set(paths)
    normalized=copy.deepcopy(m);normalized['cloud_readback_authorized']=False;normalized['completed_controls']=None
    normalized['protected']={p:h for p,h in normalized['protected'].items()if p not in paths}
    assert normalized==tested,'Readback metadata differs from the exactly tested unit'
    for key,status in (('boundary','PASS_CURRENT_TWO_SIGNAL_TEXT_READBACK_SOURCE_CONTROLS'),
                       ('imports','PASS_ACTUAL_CURRENT_TWO_SIGNAL_READBACK_IMPORT_DATA_CLOSURE')):
        assert proof[key]in paths
        r=capture.value(c.regular(ROOT/proof[key]).read_bytes())
        assert r['status']==status
        if key=='boundary':assert r['source_head']==proof['source_head']
    return dict(source_head=proof['source_head'],tested_method_sha256=c.file_sha(ROOT/proof['tested_method']),
      exact_tested_source_normalization=True)
def methods():
    m=capture.value(c.regular(METHOD).read_bytes())
    for p,h in m['protected'].items():assert c.file_sha(ROOT/p)==h,('Changed current readback source',p)
    for k in ('native_execution_authorized','native_routing_authorized','simulation_authorized',
              'rc_sta_execution_authorized','full_phy_accepted'):assert m[k]is False
    for k in ('source_controls_authorized','cloud_readback_authorized'):assert type(m[k])is bool
    assert m['readback_seconds']==1200 and m['original_run']==capture.RUN and m['source_unit_complete']is True
    if m['cloud_readback_authorized']:
        assert m['source_controls_authorized']is True
        completed_controls(m)
    else:assert m['completed_controls']is None
    return m
def save(path,value):base.save(path,value)
def inventory(root):
    assert root.is_dir()and not root.is_symlink()
    result={}
    for p in root.rglob('*'):
        assert not p.is_symlink()and(p.is_file()or p.is_dir())
        if p.is_file():result[str(p.relative_to(root))]=dict(bytes=p.stat().st_size,sha256=c.file_sha(p))
    return result
def worker():
    assert methods()['cloud_readback_authorized']is True
    report,proof=capture.restore(TRANSPORT)
    save(OUT/'source-admission.json',proof)
    source=TRANSPORT/'selected'
    # All selected raw diagnostics survive any interpretation failure.
    for name in capture.SELECTED:
        assert c.file_sha(source/name)==report['outputs'][name],name
        if name.endswith('.def'):continue
        target=OUT/'saved'/name;target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(source/name,target);assert c.file_sha(target)==report['outputs'][name]
    result=capture.inspect_saved(source,report);save(OUT/'full-saved-report.json',result)
    index={k:v for k,v in result['classification'].items()if k!='records'}
    index.update(execution_conclusion='success',repair_succeeded=False,
      original_guard_failure_preserved=True,postroute_bridge_eligible=False,
      changed_signal_count=0,root_cause_established=False,
      full_saved_report_sha256=c.file_sha(OUT/'full-saved-report.json'))
    save(OUT/'classification-index.json',index)
    for name in capture.SELECTED:assert c.file_sha(source/name)==report['outputs'][name]
    methods()
def finalize(result,trace):
    error=None
    command=trace/(LABEL+'.command.json')
    if command.is_file():
        raw=c.regular(command).read_bytes()
        result['terminal_command_raw']=dict(bytes=len(raw),sha256=c.digest(raw))
        try:result['terminal_command_record']=capture.value(raw)
        except BaseException as exc:
            error=exc;result.update(terminal_command_parse_error=repr(exc),terminal_command_parse_traceback=traceback.format_exc())
    try:methods()
    except BaseException as exc:
        if error is None:error=exc
        result.update(source_integrity_error=repr(exc),source_integrity_traceback=traceback.format_exc())
    try:result['outputs']={p:x['sha256']for p,x in inventory(OUT).items()if p!='result.json'}
    except BaseException as exc:
        if error is None:error=exc
        result.update(inventory_error=repr(exc),inventory_traceback=traceback.format_exc())
    if error is not None:result['status']='FAIL_OR_INTERRUPTED_CURRENT_TWO_SIGNAL_READBACK'
    save(OUT/'result.json',result)
    return error
def run():
    m=methods();assert m['cloud_readback_authorized']is True
    import ensure_cloud_tested_source_release as guard
    tag,head=guard.context(GROUP,os.environ)
    guard.validate_release(guard.api('releases/tags/'+tag),guard.api('git/ref/tags/'+tag),tag,head)
    assert not OUT.exists()and not TRANSPORT.exists()
    assert shutil.disk_usage(ROOT).free>=16*1024**3
    OUT.mkdir();(OUT/'supervision').mkdir()
    result=dict(status='RUNNING_CURRENT_TWO_SIGNAL_TEXT_READBACK',source_head=head,accepted=False,
      native_execution=False,native_routing_started=False,final_timing_complete=False,full_phy_accepted=False,
      original_run=capture.RUN,execution_conclusion='success',repair_succeeded=False,
      original_guard_failure_preserved=True,postroute_bridge_eligible=False,automatic_retry=False)
    save(OUT/'result.json',result)
    sup=runtime.supervisor(ROOT,OUT,OUT/'supervision',methods,m['protected'][runtime.SAMPLER])
    previous={s:signal.signal(s,sup.interrupted)for s in (signal.SIGINT,signal.SIGTERM)}
    beat=threading.Thread(target=sup.heartbeat,daemon=True);beat.start()
    primary=None;result['terminal_checks']=[]
    try:
        sup.supervised([sys.executable,str(Path(__file__).resolve()),'--worker'],LABEL,seconds=1200,cwd=ROOT)
        row=capture.value(c.regular(sup.TRACE/(LABEL+'.command.json')).read_bytes())
        base.terminal_stream(row,sup.TRACE,LABEL)
        assert row['returncode']==0 and row['supervision_failure']is None
        index=capture.value(c.regular(OUT/'classification-index.json').read_bytes())
        result.update(status='COMPLETE_CURRENT_TWO_SIGNAL_TEXT_READBACK_UNSUCCESSFUL_REPAIR_RETAINED',
          phase=row,classification=index,capture_proof=capture.value(c.regular(OUT/'source-admission.json').read_bytes()))
    except BaseException as exc:
        primary=exc;result.update(error=repr(exc),traceback=traceback.format_exc(),
          status='FAIL_OR_INTERRUPTED_CURRENT_TWO_SIGNAL_READBACK')
    finally:
        def attempt(label,fn):
            nonlocal primary
            try:
                value=fn();result['terminal_checks'].append(dict(label=label,status='PASS'))
                return value
            except BaseException as exc:
                result['terminal_checks'].append(dict(label=label,status='FAIL',error=repr(exc),traceback=traceback.format_exc()))
                result['status']='FAIL_OR_INTERRUPTED_CURRENT_TWO_SIGNAL_READBACK'
                if primary is None:primary=exc
        result['owned_cleanup']=attempt('owned-process-cleanup',lambda:sup.stop_process(sup.ACTIVE))
        attempt('heartbeat-stop',lambda:(sup.STOP.set(),beat.join(timeout=2)))
        for signum,handler in previous.items():attempt('restore-signal-'+str(signum),lambda s=signum,h=handler:signal.signal(s,h))
        try:
            terminal_error=finalize(result,sup.TRACE)
            if primary is None:primary=terminal_error
        except BaseException as exc:
            if primary is None:primary=exc
    if primary is not None:raise primary
    assert result['status']=='COMPLETE_CURRENT_TWO_SIGNAL_TEXT_READBACK_UNSUCCESSFUL_REPAIR_RETAINED'
    return result
def direct_files(output,summary,stem):
    result=[]
    for name in DIRECT:
        source=OUT/name
        if name not in summary['outputs']:
            assert not source.exists(),('Unrecorded direct diagnostic',name)
            continue
        source=c.regular(source);assert c.file_sha(source)==summary['outputs'][name]
        # Empty streams/reports remain authenticated in the output map and archive.
        if source.stat().st_size==0:continue
        dest=output/(stem+'.diagnostic.'+name.replace('/','__'))
        assert not dest.exists()
        shutil.copyfile(source,dest);assert c.file_sha(dest)==summary['outputs'][name]
        result.append(dest)
    assert len({p.name for p in result})==len(result)
    return result
def publish():
    methods()
    import publish_mainchip_saved_postroute as publisher
    from mainchip_saved_postroute_publisher_base import publish_files
    prior=publisher.GROUP
    try:
        publisher.GROUP=GROUP
        size=sum(x['bytes']for x in inventory(OUT).values())if OUT.exists()else 0
        assert size<=2*1024**3
        assert shutil.disk_usage(ROOT).free>=max(1024**3,2*size+128*1024**2)
        output=ROOT/('publication-'+GROUP)
        complete=publisher.publish_evidence(OUT,output)
        summary=capture.value(c.regular(OUT/'result.json').read_bytes())
        stem=GROUP+'-'+os.environ['GITHUB_RUN_ID']+'-1'
        paths=direct_files(output,summary,stem)
        direct=publish_files(GROUP,paths)if paths else None
        return dict(complete_archive_publication=complete,direct_diagnostics=direct,
          direct_file_hashes={p.name:c.file_sha(p)for p in paths},
          unsuccessful_repair_preserved=True,original_failure_preserved=True,accepted=False)
    finally:publisher.GROUP=prior
def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true'and os.environ.get('GITHUB_RUN_ATTEMPT')=='1'
    parser=argparse.ArgumentParser();group=parser.add_mutually_exclusive_group()
    group.add_argument('--worker',action='store_true');group.add_argument('--publish',action='store_true')
    args=parser.parse_args()
    if args.worker:worker()
    elif args.publish:print(json.dumps(publish(),indent=2),flush=True)
    else:run()
if __name__=='__main__':main()
