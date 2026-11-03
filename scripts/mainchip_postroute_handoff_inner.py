"""Original full64 route phases with explicitly qualified bounded-guide engine."""
import json,os,signal,sys,threading,time
from pathlib import Path
sys.path.insert(0,'/work/tail-source/scripts')
import mainchip_bulk_postdrt_antenna_inner as base
import mainchip_route47_memory as memory_policy
from mainchip_bulk_postdrt_antenna_inner import c,p,OUT,WORK,DATA,INPUTS,ENGINE as ORIGINAL_ENGINE,fingerprint
import mainchip_guide_route_qualification as qualification
ENGINE="/work/guide-engine/openroad"
CONFIG=json.loads(Path("/work/tail-source/scripts/mainchip-guide-engine-built-inputs.json").read_bytes())
QUALIFIED=json.loads(Path("/work/tail-source/scripts/mainchip-guide-engine-qualified-inputs.json").read_bytes())
PHASES=('prepare','restore-import','restored','export','relink','relinked','final-check','measure')
def execute(label,report,runner):
    script='/work/tail-source/scripts/mainchip_postroute_handoff_native.py'
    native_outputs={'prepare':'handoff-prepare.json','restored':'handoff-restoration.json',
                    'relinked':'handoff-netlist-proof.json','measure':'handoff-result.json'}
    if label in native_outputs:
        os.environ['NSSOC_HANDOFF_PHASE']=label
        runner(report,'handoff-'+label,[ENGINE,'-no_init','-exit','-python',script],1200)
        return c.decode((DATA/native_outputs[label]).read_bytes())
    programs={'restore-import':'handoff-restore.tcl','export':'handoff-export.tcl',
              'relink':'handoff-relink.tcl','final-check':'final-check.tcl'}
    path=WORK/programs[label]
    assert path.is_file()
    runner(report,'handoff-'+label,[ENGINE,'-no_init','-exit',str(path)],1200)
    return dict(native_stage_returned=True,script=fingerprint(path))
def main():
    report=dict(status='IN_PROGRESS',commands=[],terminal_errors=[],phases=[],
        current_route_calls=0,current_repair_calls=0,current_reconstruction_calls=0,current_audit_calls=0,current_class_import_phases=0,**p.FLAGS)
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
        p.source_guard();assert fingerprint(Path(ORIGINAL_ENGINE))==c.ENGINE
        assert fingerprint(Path(ENGINE))==CONFIG["binary"] and CONFIG["image"]==c.IMAGE
        assert c.decode(Path("/work/runtime-dependencies.json").read_bytes())==CONFIG["runtime_dependencies"]
        assert fingerprint(Path("/work/guide-engine/runtime-dependencies.json"))==CONFIG["runtime_pin"]
        report["actual_engine_qualification"]=qualification.load_and_validate("/work/guide-qualification",QUALIFIED,CONFIG)
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
        report['execution_memory_policy']=memory_policy.configure(sup,int(report['cgroup_initial']['memory.max']))
        actual_checker,checker_proof=memory_policy.checker(Path(base.command_evidence.__file__).read_bytes())
        report['execution_memory_checker']=checker_proof
        base.command_evidence=actual_checker
        for sig in (signal.SIGINT,signal.SIGTERM):handlers[sig]=signal.signal(sig,sup.interrupted)
        beat=threading.Thread(target=sup.heartbeat,daemon=True);beat.start()
        runner=lambda rep,label,argv,seconds:base.supervised_run(rep,label,argv,seconds,sup)
        for label in PHASES:
            row=dict(phase=label,status='started');report['phases'].append(row)
            base.write('bulk-postdrt-snapshot-progress.json',report)
            if label=='route':report['current_route_calls']+=1
            elif label in('freeze-import','reverse-import','restore-import'):
                report['current_reconstruction_calls']+=2;report['current_class_import_phases']+=1
            else:report['current_audit_calls']+=1
            value=execute(label,report,runner)
            row.update(status='complete',result=value)
            base.write('bulk-postdrt-snapshot-progress.json',report)
        report['handoff_result']=value
        report['handoff_observation_complete']=True
        report['snapshot_reload_qualified']=True
        report['routing_complete']=False
        report['restoration_complete']=True
        report['physical_audits_complete']=False
        report['new_candidate_connectivity_accepted']=False
        report['bounded_cycle_qualified']=False
    except BaseException as exc:
        primary=exc;report['error']=c.error_record('snapshot-reload',exc)
    finally:
        base.stop_supervision(report,sup,beat)
        for sig,old in handlers.items():c.attempt(report,'restore-signal-'+str(sig),lambda sig=sig,old=old:signal.signal(sig,old))
        c.attempt(report,'original-engine-unchanged',lambda:c.require(fingerprint(Path(ORIGINAL_ENGINE))==c.ENGINE,'original ELF changed'))
        c.attempt(report,'new-engine-unchanged',lambda:c.require(fingerprint(Path(ENGINE))==CONFIG["binary"],'new ELF changed'))
        c.attempt(report,'actual-qualification-unchanged',lambda:qualification.load_and_validate("/work/guide-qualification",QUALIFIED,CONFIG))
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
        report['status']='COMPLETE_ACTUAL_POSTROUTE_RESTORATION_NETLIST_OBSERVATION'if primary is None and not report['terminal_errors']and report.get('handoff_observation_complete')else'FAIL_ACTUAL_POSTROUTE_RESTORATION_NETLIST_OBSERVATION'
        c.finish_record(OUT/'bulk-postdrt-snapshot-inner-result.json',report,'FAIL_ACTUAL_POSTROUTE_RESTORATION_NETLIST_OBSERVATION',primary)
    return 0 if report['status']=='COMPLETE_ACTUAL_POSTROUTE_RESTORATION_NETLIST_OBSERVATION'else 1
if __name__=='__main__':sys.exit(main())
