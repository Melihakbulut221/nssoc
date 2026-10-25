#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Cloud saved-text readback only: no native executable, restore process, or routing."""
import argparse,json,os,shutil,signal,sys,threading,traceback
from pathlib import Path
import mainchip_original_clock_restoration as c
import cloud_mainchip_original_clock_restoration as base
import mainchip_clock_marker_capture as capture
import mainchip_clock_marker_classification as core
ROOT=c.ROOT
OUT=ROOT/'cloud-mainchip-clock-marker-classification'
TRANSPORT=ROOT/'transport-mainchip-clock-marker-classification'
METHOD=ROOT/'scripts/mainchip-clock-marker-classification-methods.json'
GROUP='mainchip-clock-marker-classification'

def methods():
    m=core.json_read(c.regular(METHOD).read_bytes())
    for p,h in m['protected'].items():assert c.file_sha(ROOT/p)==h,('source',p)
    for k in ('native_execution_authorized','native_routing_authorized','simulation_authorized','full_phy_accepted'):assert m[k]is False
    return m

def save(path,value):
    base.save(path,value)

def verify_selected(source,report):
    for name in capture.SELECTED:assert c.file_sha(source/name)==report['outputs'][name],name

def worker():
    assert methods()['cloud_readback_authorized']is True
    report,proof=capture.restore(TRANSPORT)
    save(OUT/'source-admission.json',proof)
    source=TRANSPORT/'selected'
    verify_selected(source,report)
    for name in capture.SELECTED:
        if name.endswith('.def'):continue
        target=OUT/'saved'/Path(name).name;target.parent.mkdir(exist_ok=True)
        shutil.copyfile(source/name,target)
    plan=core.selected_plan(c.regular(source/'work/audit-restored-result.json').read_bytes())
    raw=c.regular(source/'work/restored.def').read_bytes()
    assert c.digest(raw)==plan['expected_def_sha256']
    inventory=core.net_inventory(raw,plan['all_clock_names']);del raw
    save(OUT/'restored-net-inventory.json',inventory)
    save(OUT/'selected-clock-fixed-plan.json',plan)
    raw=c.regular(source/capture.SELECTED[0]).read_bytes()
    tr=c.regular(source/capture.SELECTED[1]).read_bytes()
    result=core.analyze(raw,tr,report['initial_DRT']['measurement'],inventory,plan['all_clock_names'])
    assert result['marker_count']==762 and result['selected_clock_fixed_count']==1691
    save(OUT/'full-marker-classification.json',result)
    compact={k:v for k,v in result.items()if k!='records'}
    compact.update(full_result_sha256=c.file_sha(OUT/'full-marker-classification.json'),
        marker_json_sha256=c.digest(raw),TR_sha256=c.digest(tr))
    save(OUT/'classification-index.json',compact)
    verify_selected(source,report);methods()

def run():
    m=methods();assert m['cloud_readback_authorized']is True
    import ensure_cloud_tested_source_release as g
    tag,head=g.context(GROUP,os.environ)
    g.validate_release(g.api('releases/tags/'+tag),g.api('git/ref/tags/'+tag),tag,head)
    assert not OUT.exists()and not TRANSPORT.exists()
    assert shutil.disk_usage(ROOT).free>=4*1024**3
    OUT.mkdir();(OUT/'supervision').mkdir()
    r=dict(status='RUNNING_SAVED_MARKER_CLASSIFICATION',source_head=head,accepted=False,
        native_execution=False,native_routing_started=False,final_timing_complete=False,full_phy_accepted=False)
    save(OUT/'result.json',r)
    sup=base.supervisor();oldout,oldtrace=sup.OUT,sup.TRACE;sup.OUT=OUT;sup.TRACE=OUT/'supervision'
    previous={s:signal.signal(s,sup.interrupted)for s in (signal.SIGINT,signal.SIGTERM)}
    heartbeat=threading.Thread(target=sup.heartbeat,daemon=True);heartbeat.start()
    try:
        label='complete-saved-marker-readback'
        sup.supervised([sys.executable,str(Path(__file__).resolve()),'--worker'],label,seconds=1200,cwd=ROOT)
        record=core.json_read(c.regular(sup.TRACE/(label+'.command.json')).read_bytes())
        base.terminal_stream(record,sup.TRACE,label)
        r.update(status='COMPLETE_SAVED_MARKER_CLASSIFICATION_NOT_ROUTE_ACCEPTANCE',
            phase=record,classification=core.json_read(c.regular(OUT/'classification-index.json').read_bytes()),
            capture_proof=core.json_read(c.regular(OUT/'source-admission.json').read_bytes()))
    except BaseException as e:
        r.update(status='FAIL_OR_INTERRUPTED_SAVED_MARKER_CLASSIFICATION',error=repr(e),traceback=traceback.format_exc());raise
    finally:
        try:sup.stop_process(sup.ACTIVE)
        finally:
            sup.STOP.set();heartbeat.join(timeout=2)
            for s,f in previous.items():signal.signal(s,f)
            sup.OUT,sup.TRACE=oldout,oldtrace
            r['outputs']={str(p.relative_to(OUT)):c.file_sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'}
            save(OUT/'result.json',r)
        methods()

def publish():
    methods()
    import publish_mainchip_saved_postroute as p
    previous=p.GROUP
    try:
        p.GROUP=GROUP
        size=sum(x.stat().st_size for x in OUT.rglob('*')if x.is_file())if OUT.exists()else 0
        assert shutil.disk_usage(ROOT).free>=max(1024**3,size+128*1024**2)
        return p.publish_evidence(OUT,ROOT/('publication-'+GROUP))
    finally:p.GROUP=previous

def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true'and os.environ.get('GITHUB_RUN_ATTEMPT')=='1'
    p=argparse.ArgumentParser();g=p.add_mutually_exclusive_group()
    g.add_argument('--worker',action='store_true');g.add_argument('--publish',action='store_true')
    a=p.parse_args()
    if a.worker:worker()
    elif a.publish:print(json.dumps(publish(),indent=2),flush=True)
    else:run()
if __name__=='__main__':main()
