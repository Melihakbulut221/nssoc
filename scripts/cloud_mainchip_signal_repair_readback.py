#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Hosted text-only recovery of exact failed-route reports. No native executable."""
import argparse,json,os,shutil,signal,sys,threading,traceback
from pathlib import Path
import mainchip_original_clock_restoration as c
import cloud_mainchip_original_clock_restoration as base
import cdr_v59_tail_access_runtime as runtime
import mainchip_signal_repair_readback as capture
ROOT=c.ROOT
OUT=ROOT/'cloud-mainchip-signal-repair-readback'
TRANSPORT=ROOT/'transport-mainchip-signal-repair-readback'
METHOD=ROOT/'scripts/mainchip-signal-repair-readback-methods.json'
GROUP='mainchip-signal-repair-readback'
LABEL='complete-saved-signal-repair-readback'
DIRECT=('full-saved-report.json','classification-index.json','source-admission.json',
 'saved/work/drc-audit-result.json','saved/work/unfix-audit-result.json',
 'saved/work/route-audit-result.json','saved/work/guide-audit-result.json','saved/work/prepare-result.json',
 'saved/work/original-gate-before-repair/result.json','saved/work/original-gate-after-repair/result.json',
 'saved/work/original-gate-after-final-drc/result.json','saved/work/initial-drc-markers.json',
 'saved/work/initial-drc.rpt','saved/work/initial-drc-reread.rpt',
 'saved/supervision/drc-audit.command.json')
def methods():
    m=capture.value(c.regular(METHOD).read_bytes())
    for p,h in m['protected'].items():assert c.file_sha(ROOT/p)==h,('Changed readback source',p)
    for k in ('native_execution_authorized','native_routing_authorized','simulation_authorized',
              'rc_sta_execution_authorized','full_phy_accepted'):assert m[k]is False
    for k in ('source_controls_authorized','cloud_readback_authorized'):assert type(m[k])is bool
    assert m['readback_seconds']==1200 and m['original_run']==capture.RUN
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
    # Copy all selected JSON/TR/stream evidence before interpreting any result.
    # The large exact DEF is used for typed net membership, kept in the original cloud capsule.
    for name in capture.SELECTED:
        assert c.file_sha(source/name)==report['outputs'][name],name
        if name.endswith('.def'):continue
        target=OUT/'saved'/name;target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(source/name,target)
        assert c.file_sha(target)==report['outputs'][name]
    result=capture.inspect_saved(source,report)
    save(OUT/'full-saved-report.json',result)
    classification=result['classification']
    index={k:v for k,v in classification.items()if k!='records'}
    index.update(original_run_conclusion='failure',resource_guard_failure_preserved=True,
        postroute_bridge_eligible=False,full_saved_report_sha256=c.file_sha(OUT/'full-saved-report.json'))
    save(OUT/'classification-index.json',index)
    for name in capture.SELECTED:assert c.file_sha(source/name)==report['outputs'][name]
    methods()
def run():
    m=methods();assert m['cloud_readback_authorized']is True
    import ensure_cloud_tested_source_release as guard
    tag,head=guard.context(GROUP,os.environ)
    guard.validate_release(guard.api('releases/tags/'+tag),guard.api('git/ref/tags/'+tag),tag,head)
    assert not OUT.exists()and not TRANSPORT.exists()
    assert shutil.disk_usage(ROOT).free>=8*1024**3
    OUT.mkdir();(OUT/'supervision').mkdir()
    result=dict(status='RUNNING_FAILED_SIGNAL_REPAIR_READBACK',source_head=head,accepted=False,
        native_execution=False,native_routing_started=False,final_timing_complete=False,full_phy_accepted=False,
        original_run=capture.RUN,original_run_conclusion='failure',resource_guard_failure_preserved=True,
        postroute_bridge_eligible=False,automatic_retry=False)
    save(OUT/'result.json',result)
    sup=runtime.supervisor(ROOT,OUT,OUT/'supervision',methods,m['protected'][runtime.SAMPLER])
    previous={s:signal.signal(s,sup.interrupted)for s in (signal.SIGINT,signal.SIGTERM)}
    beat=threading.Thread(target=sup.heartbeat,daemon=True);beat.start()
    try:
        sup.supervised([sys.executable,str(Path(__file__).resolve()),'--worker'],LABEL,seconds=1200,cwd=ROOT)
        row=capture.value(c.regular(sup.TRACE/(LABEL+'.command.json')).read_bytes())
        base.terminal_stream(row,sup.TRACE,LABEL)
        assert row['returncode']==0 and row['supervision_failure']is None
        index=capture.value(c.regular(OUT/'classification-index.json').read_bytes())
        result.update(status='COMPLETE_SAVED_SIGNAL_REPAIR_REPORTS_ORIGINAL_FAILURE_RETAINED',
            phase=row,classification=index,capture_proof=capture.value(c.regular(OUT/'source-admission.json').read_bytes()))
    except BaseException as error:
        result.update(status='FAIL_OR_INTERRUPTED_SIGNAL_REPAIR_READBACK',error=repr(error),traceback=traceback.format_exc())
        raise
    finally:
        try:
            result['owned_cleanup']=sup.stop_process(sup.ACTIVE)
        finally:
            sup.STOP.set();beat.join(timeout=2)
            for signum,handler in previous.items():signal.signal(signum,handler)
            finalize(result,sup.TRACE)
    assert result['status']=='COMPLETE_SAVED_SIGNAL_REPAIR_REPORTS_ORIGINAL_FAILURE_RETAINED'
    return result
def finalize(result,trace):
    command=trace/(LABEL+'.command.json')
    if command.is_file():
        raw=c.regular(command).read_bytes()
        result['terminal_command_raw']=dict(bytes=len(raw),sha256=c.digest(raw))
        try:result['terminal_command_record']=capture.value(raw)
        except Exception as error:
            result.update(status='FAIL_OR_INTERRUPTED_SIGNAL_REPAIR_READBACK',
                terminal_command_parse_error=repr(error),terminal_command_parse_traceback=traceback.format_exc())
    try:methods()
    except BaseException as error:
        result.update(status='FAIL_OR_INTERRUPTED_SIGNAL_REPAIR_READBACK',
            source_integrity_error=repr(error),source_integrity_traceback=traceback.format_exc())
    result['outputs']={p:x['sha256']for p,x in inventory(OUT).items()if p!='result.json'}
    save(OUT/'result.json',result)
    return result
def direct_files(output,summary,stem):
    result=[]
    for name in DIRECT:
        source=OUT/name
        if name not in summary['outputs']:
            assert not source.exists(),('Unrecorded direct diagnostic',name)
            continue
        source=c.regular(source);assert c.file_sha(source)==summary['outputs'][name]
        # Empty TR bytes are represented in the manifest/summary and complete archive.
        # No empty-file omission can become a zero-marker claim.
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
        assert shutil.disk_usage(ROOT).free>=max(1024**3,2*size+128*1024**2)
        output=ROOT/('publication-'+GROUP)
        complete=publisher.publish_evidence(OUT,output)
        summary=capture.value(c.regular(OUT/'result.json').read_bytes())
        stem=GROUP+'-'+os.environ['GITHUB_RUN_ID']+'-1'
        paths=direct_files(output,summary,stem)
        direct=publish_files(GROUP,paths)if paths else None
        return dict(complete_archive_publication=complete,direct_diagnostics=direct,
            direct_file_hashes={p.name:c.file_sha(p)for p in paths},
            original_failure_preserved=True,accepted=False)
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
