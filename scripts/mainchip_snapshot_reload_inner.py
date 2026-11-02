"""Reopen the actual retained partial route with the original frozen engine and audits."""
import json,os,signal,sys,threading,time
from pathlib import Path
sys.path.insert(0,'/work/tail-source/scripts')
import mainchip_bulk_postdrt_antenna_inner as base
from mainchip_bulk_postdrt_antenna_inner import c,p,OUT,WORK,DATA,INPUTS,ENGINE,fingerprint
PHASES=('snapshot-reload',)
def execute(label,report,runner):
    assert label=='snapshot-reload'
    runner(report,'bulk-postdrt-snapshot-reload',[ENGINE,'-no_init','-exit','-python','/work/tail-source/scripts/mainchip_snapshot_reload_native.py'],1200)
    value=c.decode((DATA/'snapshot-reload-result.json').read_bytes())
    assert value['status']=='PASS_PARTIAL_SNAPSHOT_ROUNDTRIP_AND_ORIGINAL_SCOPED_DELTA'
    assert value['snapshot_reload_qualified']is True and value['routing_complete']is False
    assert all(value[k]is False for k in p.FLAGS)
    return value
def main():
    report=dict(status='IN_PROGRESS',commands=[],terminal_errors=[],phases=[],
        current_route_calls=0,current_repair_calls=0,current_reconstruction_calls=0,current_audit_calls=0,**p.FLAGS)
    primary=None;sup=None;beat=None;handlers={};started=time.monotonic()
    def usage():
        root=Path('/sys/fs/cgroup')
        return {n:(root/n).read_text().strip()for n in ('memory.max','memory.swap.max','memory.events','memory.peak','cpu.max','pids.max')}
    def resources(v):
        assert v['memory.max']==str(c.MEMORY)and v['memory.swap.max']=='0'and v['pids.max']==str(c.PIDS)
        quota,period=v['cpu.max'].split();assert quota!='max'and int(quota)==2*int(period)
    def runtime():
        paths=set()
        for line in (OUT/'bulk-postdrt-ldd.stdout').read_text().splitlines():
            assert 'not found'not in line
            for word in line.split():
                if word.startswith('/')and Path(word).is_file():paths.add(word)
        observed={v:fingerprint(Path(v))for v in sorted(paths)}
        base.write('bulk-postdrt-runtime-observed.json',observed)
        return c.runtime_match(c.decode(Path('/work/runtime-dependencies.json').read_bytes()),observed)
    try:
        assert not any(k in os.environ for k in ('GH_TOKEN','GITHUB_TOKEN'))
        p.source_guard();assert fingerprint(Path(ENGINE))==c.ENGINE
        for name,pin in c.decode(Path('/work/scoped-source-pins.json').read_bytes()).items():assert fingerprint(Path('/work/tail-source')/name)==pin
        assert fingerprint(INPUTS['input'])==p.INPUT
        assert not WORK.exists()
        WORK.mkdir(parents=True)
        DATA.mkdir(parents=True,exist_ok=True)
        report['cgroup_initial']=usage();resources(report['cgroup_initial'])
        for n,path in INPUTS.items():os.environ['NSSOC_BULK_'+n.upper()]=str(path)
        base.run(report,'bulk-postdrt-version',[ENGINE,'-version'],30)
        base.run(report,'bulk-postdrt-ldd',['ldd',ENGINE],30)
        report['runtime_before']=runtime()
        sup=base.supervision.supervisor();sup.OUT=OUT/'bulk-postdrt-supervisor';sup.TRACE=OUT/'bulk-postdrt-supervision'
        sup.OUT.mkdir();sup.TRACE.mkdir()
        assert sup.SECONDS==1200 and sup.MAX_GROUP_RSS_KIB==10485760 and sup.MIN_AVAILABLE_KIB==2097152
        for sig in (signal.SIGINT,signal.SIGTERM):handlers[sig]=signal.signal(sig,sup.interrupted)
        beat=threading.Thread(target=sup.heartbeat,daemon=True);beat.start()
        runner=lambda rep,label,argv,seconds:base.supervised_run(rep,label,argv,seconds,sup)
        for label in PHASES:
            row=dict(phase=label,status='started');report['phases'].append(row)
            base.write('bulk-postdrt-snapshot-progress.json',report)
            report['current_audit_calls']+=1
            value=execute(label,report,runner)
            row.update(status='complete',result=value)
            base.write('bulk-postdrt-snapshot-progress.json',report)
        report['snapshot_result']=value
        report['snapshot_reload_qualified']=True
        report['routing_complete']=False
        report['restoration_complete']=False
        report['physical_audits_complete']=False
        report['new_candidate_connectivity_accepted']=False
        report['bounded_cycle_qualified']=False
    except BaseException as exc:
        primary=exc;report['error']=c.error_record('snapshot-reload',exc)
    finally:
        base.stop_supervision(report,sup,beat)
        for sig,old in handlers.items():c.attempt(report,'restore-signal-'+str(sig),lambda sig=sig,old=old:signal.signal(sig,old))
        c.attempt(report,'engine-unchanged',lambda:c.require(fingerprint(Path(ENGINE))==c.ENGINE,'ELF changed'))
        c.attempt(report,'input-unchanged',lambda:c.require(fingerprint(INPUTS['input'])==p.INPUT,'current input changed'))
        if (OUT/'bulk-postdrt-ldd.stdout').exists():c.attempt(report,'runtime-after',lambda:report.update(runtime_after=runtime()))
        def terminal():
            v=usage();resources(v);report['cgroup_terminal']=v
            first=dict(x.split()for x in report['cgroup_initial']['memory.events'].splitlines())
            last=dict(x.split()for x in v['memory.events'].splitlines())
            assert all(first.get(k,'0')==last.get(k,'0')for k in ('oom','oom_kill','oom_group_kill'))
        if 'cgroup_initial'in report:c.attempt(report,'terminal-cgroup',terminal)
        c.attempt(report,'preserve-native-census',lambda:base.write('bulk-postdrt-snapshot-available-output.json',base.preserve_available()))
        report['elapsed_seconds']=time.monotonic()-started
        report['status']='COMPLETE_PARTIAL_SNAPSHOT_NATIVE_AUDIT'if primary is None and not report['terminal_errors']and report.get('snapshot_reload_qualified')else'FAIL_PARTIAL_SNAPSHOT_NATIVE_AUDIT'
        c.finish_record(OUT/'bulk-postdrt-snapshot-inner-result.json',report,'FAIL_PARTIAL_SNAPSHOT_NATIVE_AUDIT',primary)
    return 0 if report['status']=='COMPLETE_PARTIAL_SNAPSHOT_NATIVE_AUDIT'else 1
if __name__=='__main__':sys.exit(main())
