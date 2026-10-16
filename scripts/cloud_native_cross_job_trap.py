#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Restore an immutable native845 SPICE process in a separate GitHub job."""
import hashlib,json,os,re,shutil,subprocess,tarfile
from pathlib import Path
import numpy as np
import cloud_tx_input_driver as physical
import cloud_native_checkpoint_probe as native
import cloud_pll_vbic_acquisition as acquisition
from route_cloud_newer_postcts import fetch
ROOT=physical.ROOT;OUT=ROOT/'cloud-native-cross-job-trap'
SOURCE=dict(run=38897452492,group='native-checkpoint-probe',root='cloud-native-checkpoint-probe',bytes=59820019,sha='d91c84bba85f31109ad99b575e5ac402d2b064dd4ea68a22d0d6c54783be13c7',summary='61e3ba7d9af7967a41a74a4abd719954487f0cdd8c9a2e25ca9abeb27cfd24a9')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true';OUT.mkdir(exist_ok=False)
    result=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],source=SOURCE,cross_job_native_restore_proven=False,full_capture=False,acquisition_accepted=False,full_phy_accepted=False,scope='Restore the actual saved physical845 SPICE process from another completed job. Exact4ns native trajectory/34probes and single entrypoint, no cold restart or waveform splice. Not original1us acquisition, full-device safety, PVT or fullPHY acceptance.')
    def save():(OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    def run(label,args,required=True,timeout=600):
        p=subprocess.run(args,capture_output=True,text=True,timeout=timeout);(OUT/(label+'.log')).write_text(p.stdout+p.stderr)
        result.setdefault('commands',[]).append(dict(label=label,args=args,returncode=p.returncode,sha256=sha(OUT/(label+'.log'))));save()
        if required and p.returncode:raise RuntimeError(label+': '+(p.stdout+p.stderr)[-7000:])
        return p
    clone=None;case=None;diagnostic_case=None;diagnostic_reference=None;criu_config_owned=False;save()
    try:
        assert sha(native.__file__)=='28e3ca20e1d7cce96ac68f4ec19e510326d8e96ed0da77ddc16ab5b3c5e86231'
        assert not run('empty-runner',['docker','ps','-aq']).stdout.strip()
        result['diagnostic_purpose']='Separate executable/host compatibility from saved process portability. No solver, circuit, original checkpoint or numerical gate changes.'
        run('destination-lscpu',['lscpu','--json']);run('destination-kernel',['uname','-a'])
        (OUT/'destination-cpuinfo.txt').write_text(Path('/proc/cpuinfo').read_text())
        result['destination_cpu']=json.loads((OUT/'destination-lscpu.log').read_text())
        result['destination_cpuinfo_sha256']=sha(OUT/'destination-cpuinfo.txt')
        physical.OUT=OUT;restored,prior=physical.restore(SOURCE)
        assert prior['native_checkpoint_proven']and prior['status']=='PASS_NATIVE_PHYSICAL845_CHECKPOINT_BIT_EXACT_BOUNDED4NS_NOT_CROSS_JOB_OR_ACQUISITION'
        assert len(prior['controls'])==3 and all(x['rejected']for x in prior['controls'])
        assert prior['run_id']!=os.environ['GITHUB_RUN_ID']
        source=ROOT/SOURCE['root'];assert not source.exists();shutil.move(str(restored),str(source))
        result.update(source_run_id=prior['run_id'],run_id=os.environ['GITHUB_RUN_ID'],source_boot_id=prior['boot_id'],boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip())
        result['different_boot_id_observed']=result['boot_id']!=result['source_boot_id'];save()
        # Rehydrate the exact model libraries at the checkpoint's original paths.
        library_root=ROOT/'cloud-pll-snapshot';assert not library_root.exists();library_root.mkdir()
        protected=prior['preparation']['protected'];wanted={str(Path(n).relative_to(library_root)):v for n,v in protected.items()if Path(n).is_relative_to(library_root)};assert len(wanted)>=37
        packed=OUT/'models-source.tar.gz';fetch(acquisition.URL+'.tar.gz',acquisition.ARCHIVE_SHA,packed);assert packed.stat().st_size==1318040150
        found=set()
        with tarfile.open(packed)as tar:
            for m in tar:
                p=Path(m.name);assert not p.is_absolute()and'..'not in p.parts and p.parts[0]==library_root.name
                rel=str(Path(*p.parts[1:]))
                if rel not in wanted:continue
                assert m.isfile()and rel not in found;found.add(rel);data=tar.extractfile(m).read();assert hashlib.sha256(data).hexdigest()==wanted[rel]
                target=library_root/rel;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
        assert found==set(wanted);packed.unlink();assert all(sha(p)==v for p,v in protected.items())
        vectors=next(l[5:].split()for l in(source/'resumed/circuit.cir').read_text().splitlines()if l.startswith('save '));assert len(vectors)==34
        rn,rv,reference=native.inspect_capture(source/'reference',vectors,(source/'reference-log.log').read_text());assert reference==prior['reference'];result['reference']=reference
        prefix=(source/'checkpoint-prefix.raw').read_bytes();assert sha(source/'checkpoint-prefix.raw')==prior['checkpoint_prefix']['sha256'] and len(prefix)==prior['checkpoint_prefix']['bytes']
        case=source/'resumed';assert sha(case/'actual-acquisition.raw')==prior['outputs']['resumed/actual-acquisition.raw']
        (case/'actual-acquisition.raw').write_bytes(prefix);assert sha(case/'actual-acquisition.raw')==prior['checkpoint_prefix']['sha256']
        assert (case/'boots.log').read_text().splitlines()==['native-entrypoint']
        result['prefix_restore']=dict(original_checkpoint_bytes_restored=True,sha256=sha(case/'actual-acquisition.raw'),bytes=len(prefix),full_old_capture_not_used_as_process_input=True);save()
        result['criu_build']=json.loads((Path(os.environ['RUNNER_TEMP'])/'criu-build.json').read_text());assert sha('/usr/sbin/criu')==result['criu_build']['binary_sha256']
        assert result['criu_build']['source_commit']==prior['criu_build']['source_commit']=='9539417f3e3cfa4eb84c319cd71f4d52f1f08645'
        run('criu-check',['sudo','criu','check','--all'],False)
        cpu_directory=OUT/'destination-cpu-capabilities';cpu_directory.mkdir()
        run('destination-cpu-capabilities',['sudo','criu','cpuinfo','dump','-D',str(cpu_directory)])
        run('readable-cpu-capabilities',['sudo','chown','-R',str(os.getuid())+':'+str(os.getgid()),str(cpu_directory)])
        result['source_cpu_capabilities_recorded']='cpuinfo.img'in prior['checkpoint_images']
        result['cpu_compatibility_proven']=False
        decode="import sys,json;sys.path.insert(0,sys.argv[1]);from pycriu import images;print(json.dumps(images.load(open(sys.argv[2],'rb'),pretty=True),indent=2))"
        library=str(Path(os.environ['RUNNER_TEMP'])/'criu-src/lib')
        for filename in ('core-1.img','mm-1.img','files.img'):
            run('source-'+filename+'-decoded',['/usr/bin/python3','-c',decode,library,str(source/'checkpoints/state'/filename)])
        run('destination-cpu-decoded',['/usr/bin/python3','-c',decode,library,str(cpu_directory/'cpuinfo.img')])
        config="import json,pathlib;p=pathlib.Path('/etc/docker/daemon.json');d=json.loads(p.read_text())if p.exists()else{};d['experimental']=True;p.write_text(json.dumps(d))"
        run('docker-experimental',['sudo','python3','-c',config]);run('docker-restart',['sudo','systemctl','restart','docker'])
        assert sha(source/'native-image.tar')==prior['native_image_sha256'];run('load-native-image',['docker','load','-i',str(source/'native-image.tar')])
        image=json.loads(run('loaded-image',['docker','image','inspect',prior['image_id']]).stdout)[0];assert image['Id']==prior['image_id']
        original_command=next(x['args']for x in prior['commands']if x['label']=='start-native');cpu=original_command[original_command.index('--cpuset-cpus')+1];assert int(cpu)in os.sched_getaffinity(0)
        engine=source/'runtime/patched-ngspice';assert sha(engine)==native.ENGINE_SHA
        clone='nssoc-native-cross-job';code='printf "native-entrypoint\\n" >> boots.log; exec "'+str(engine)+'" -n -b actual-acquisition.cir'
        cmd=['docker','create','--name',clone,'--network','host','--security-opt','seccomp=unconfined','--cpuset-cpus',cpu,'--mount','type=bind,src='+str(ROOT)+',dst='+str(ROOT)+',readonly','--mount','type=bind,src='+str(case)+',dst='+str(case),'-w',str(case),'-e','SPICE_SCRIPTS='+str(case),'-e','OMP_NUM_THREADS=1','-e','RAYON_NUM_THREADS=1','--entrypoint','/bin/dash',prior['image_id'],'-c',code]
        assert cmd[cmd.index('--network'):]==original_command[original_command.index('--network'):]
        # Execute the same immutable circuit, libraries and solver afresh on this
        # destination. This is an independent diagnostic control, never a replacement
        # trajectory for the restored process or a splice into its native raw capture.
        diagnostic_case=source/'destination-reference';diagnostic_case.mkdir()
        for filename in ('circuit.cir','parent865.spice','actual-acquisition.cir','spinit'):
            shutil.copyfile(source/'reference'/filename,diagnostic_case/filename)
            assert sha(diagnostic_case/filename)==sha(source/'reference'/filename)
        diagnostic_reference='nssoc-native-destination-reference'
        reference_cmd=[a.replace(str(case),str(diagnostic_case))for a in cmd]
        reference_cmd[reference_cmd.index('--name')+1]=diagnostic_reference
        run('create-destination-reference',reference_cmd)
        run('start-destination-reference',['docker','start',diagnostic_reference])
        reference_exit=run('wait-destination-reference',['docker','wait',diagnostic_reference],timeout=900).stdout.strip()
        run('destination-reference-log',['docker','logs',diagnostic_reference],False)
        result['destination_reference_exit']=reference_exit;save()
        assert reference_exit=='0',('Destination fresh native reference failed',reference_exit)
        dn,dv,destination_reference=native.inspect_capture(diagnostic_case,vectors,(OUT/'destination-reference-log.log').read_text())
        result['destination_reference']=destination_reference
        result['destination_reference_bit_exact_to_source']=bool(dn==rn and dv.shape==rv.shape and np.array_equal(dv,rv))
        result['destination_reference_single_entrypoint']=(diagnostic_case/'boots.log').read_text().splitlines()==['native-entrypoint'];save()
        clone_id=run('create-native-clone',cmd).stdout.strip();assert re.fullmatch('[0-9a-f]{64}',clone_id)
        root=Path(run('docker-root',['docker','info','--format','{{.DockerRootDir}}']).stdout.strip());destination=root/'containers'/clone_id/'checkpoints/state'
        checkpoints=source/'checkpoints/state'
        assert {str(p.relative_to(checkpoints)):sha(p)for p in checkpoints.rglob('*')if p.is_file()}==prior['checkpoint_images']
        run('default-checkpoint-dir',['sudo','mkdir','-p',str(destination.parent)]);run('copy-native-checkpoint',['sudo','cp','-a',str(checkpoints),str(destination)])
        check="import pathlib,hashlib,sys,json;scan=lambda r:{str(p.relative_to(r)):hashlib.sha256(p.read_bytes()).hexdigest()for p in r.rglob('*')if p.is_file()};a=scan(pathlib.Path(sys.argv[1]));b=scan(pathlib.Path(sys.argv[2]));assert a and a==b;print(json.dumps(a))"
        transfer=json.loads(run('copy-proof',['sudo','python3','-c',check,str(checkpoints),str(destination)]).stdout);assert transfer==prior['checkpoint_images'];result['checkpoint_images']=transfer;save()
        # Diagnostic only: stop at restore before executing user instructions so
        # GDB can catch the actual fault rather than guessing from an exit string.
        configuration="import pathlib;p=pathlib.Path('/etc/criu/runc.conf');assert not p.exists();p.parent.mkdir(exist_ok=True);p.write_text('leave-stopped\\n')"
        run('leave-stopped-config',['sudo','python3','-c',configuration]);criu_config_owned=True
        started=run('restore-native',['docker','start','--checkpoint','state',clone],False)
        if started.returncode:
            run('restore-native-detail',['sudo','cat','/run/containerd/io.containerd.runtime.v2.task/moby/'+clone_id+'/work/restore.log'],False);raise RuntimeError('Separate-job native restore failed')
        state=json.loads(run('stopped-restored-process',['docker','inspect',clone]).stdout)[0]['State'];pid=state['Pid']
        assert state['Running'] and isinstance(pid,int) and pid>1
        proc_status=run('stopped-kernel-status',['sudo','cat','/proc/'+str(pid)+'/status']).stdout
        assert re.search(r'(?m)^State:\s+T',proc_status),'Restore did not leave the actual process stopped'
        (OUT/'restored-process-maps.txt').write_text(run('restored-process-maps',['sudo','cat','/proc/'+str(pid)+'/maps']).stdout)
        commands=['set pagination off','set confirm off','set debuginfod enabled off','set sysroot /proc/'+str(pid)+'/root',
                  'attach '+str(pid),'handle SIGSTOP nostop noprint nopass','handle SIGCONT nostop noprint pass','handle SIGILL stop print nopass',
                  'signal SIGCONT','python','import gdb,json',
                  "detail={'pc':int(gdb.parse_and_eval('$pc')),'signal':str(gdb.parse_and_eval('$_siginfo')),'instruction':gdb.execute('x/12i $pc',to_string=True),'bytes':gdb.execute('x/32bx $pc',to_string=True),'symbol':gdb.execute('info symbol $pc',to_string=True),'backtrace':gdb.execute('bt 20',to_string=True),'registers':gdb.execute('info registers',to_string=True),'library':gdb.solib_name(int(gdb.parse_and_eval('$pc')))}",
                  "print('NSSOC_NATIVE_TRAP_JSON '+json.dumps(detail))",'end','detach','quit']
        gdb_script=OUT/'capture-native-trap.gdb';gdb_script.write_text('\n'.join(commands)+'\n')
        probe=run('native-trap-gdb',['sudo','gdb','--batch','-nx','-nh','-x',str(gdb_script)],False,timeout=300)
        records=[l.split('NSSOC_NATIVE_TRAP_JSON ',1)[1]for l in probe.stdout.splitlines()if l.startswith('NSSOC_NATIVE_TRAP_JSON ')]
        result['trap_probe']=dict(debugger_returncode=probe.returncode,record_count=len(records),acceptance=False)
        if records:
            assert len(records)==1;result['trap_probe']['observation']=json.loads(records[0])
        save()
        run('remove-leave-stopped-config',['sudo','rm','/etc/criu/runc.conf']);criu_config_owned=False
        exitcode=run('wait-native',['docker','wait',clone],timeout=900).stdout.strip();run('continued-log',['docker','logs',clone],False)
        log=(source/'original-prefix-log.log').read_text()+(OUT/'continued-log.log').read_text();(OUT/'full-native.log').write_text(log)
        assert exitcode=='0',(exitcode,log[-7000:])
        sn,sv,continued=native.inspect_capture(case,vectors,log);result['continued']=continued
        result['positive']=native.verify((rn,rv),(sn,sv),(case/'boots.log').read_text().splitlines())
        assert result['destination_reference_bit_exact_to_source'] and result['destination_reference_single_entrypoint']
        raw=(case/'actual-acquisition.raw').read_bytes();assert raw.split(b'Binary:\n',1)[1].startswith(prefix.split(b'Binary:\n',1)[1])
        assert sha(case/'actual-acquisition.raw')==prior['outputs']['resumed/actual-acquisition.raw'],'Complete native raw bytes differ from original restored process'
        controls=[]
        for fault in ('truncation','state_corruption','cold_restart'):
            bad=sv[:-1]if fault=='truncation'else sv.copy();boots=['native-entrypoint']
            if fault=='state_corruption':bad[-1,1]+=1e-6
            if fault=='cold_restart':boots.append('native-entrypoint')
            try:native.verify((rn,rv),(sn,bad),boots)
            except AssertionError as e:controls.append(dict(fault=fault,rejected=True,error=str(e)))
            else:raise AssertionError('Native continuation fault escaped')
        result['controls']=controls;assert all(sha(p)==v for p,v in protected.items())
        shutil.copyfile(case/'actual-acquisition.raw',OUT/'continued.raw');shutil.copyfile(case/'op.raw',OUT/'op.raw')
        result.update(status='PASS_NATIVE_PHYSICAL845_SEPARATE_JOB_RESTORE_BIT_EXACT_BOUNDED4NS_NOT_ACQUISITION',cross_job_native_restore_proven=True,complete_raw_sha256=sha(OUT/'continued.raw'),unchanged_native_inputs=True)
    except BaseException as e:result.update(status='FAIL_OR_ERROR',error=repr(e));raise
    finally:
        if criu_config_owned:run('cleanup-leave-stopped-config',['sudo','rm','-f','/etc/criu/runc.conf'],False)
        if clone:
            run('final-native-log',['docker','logs',clone],False);run('cleanup-native',['docker','rm','-f',clone],False)
        if diagnostic_reference:
            run('final-destination-reference-log',['docker','logs',diagnostic_reference],False)
            run('cleanup-destination-reference',['docker','rm','-f',diagnostic_reference],False)
        run('kernel-traps',['sudo','dmesg','--level=err,warn'],False)
        for label,folder in (('continued',case),('destination-reference',diagnostic_case)):
            if folder is None:continue
            kept=OUT/('retained-'+label);kept.mkdir(exist_ok=True)
            for filename in ('actual-acquisition.raw','op.raw','boots.log'):
                f=folder/filename
                if f.exists():shutil.copyfile(f,kept/filename)
            raw=kept/'actual-acquisition.raw'
            if raw.exists():
                try:
                    names,values,meta=native.pll.decode_prefix(raw.read_bytes())
                    result.setdefault('retained_captures',{})[label]=dict(metadata=meta,rows=len(values),end_s=float(values[-1,0])if len(values)else None,sha256=sha(raw),finite=bool(np.isfinite(values).all()),complete=False)
                except Exception as capture_error:
                    result.setdefault('retained_captures',{})[label]=dict(sha256=sha(raw),decode_error=repr(capture_error),complete=False)
        result['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};save()
        print(json.dumps({k:result[k]for k in ('status','error','cross_job_native_restore_proven')if k in result}),flush=True)
if __name__=='__main__':main()
