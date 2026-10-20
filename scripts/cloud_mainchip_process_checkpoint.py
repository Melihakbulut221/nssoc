#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Actual OpenROAD loaded-design checkpoint across isolated cloud jobs.

No detailed-route worker or final timing acceptance is inferred from this test.
"""
import argparse,copy,hashlib,json,os,re,shutil,subprocess,time
from pathlib import Path
import compare_cloud_routed_endpoints as reports
from run_cloud_tx_layout_repair import sha
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'cloud-mainchip-process-runtime'
REPO='repos/Melihakbulut221/nssoc/'
TUNABLES='glibc.cpu.hwcaps=-AVX512F,-AVX512CD,-AVX512BW,-AVX512DQ,-AVX512ER,-AVX512PF,-AVX512VL,-RTM'
CRIU_COMMIT='9539417f3e3cfa4eb84c319cd71f4d52f1f08645'
def api(path):return json.loads(subprocess.check_output(['gh','api',REPO+path]))
def digest(raw):return hashlib.sha256(raw).hexdigest()
def journal(raw,boots):
    lines=raw.decode().splitlines();b=boots.decode().splitlines()
    assert len(b)==1 and b[0],'Cold restart or missing entrypoint'
    rows=[line.split()for line in lines]
    assert len(rows)==120 and all(len(row)==3 for row in rows),'Missing checkpoint continuation rows'
    assert [int(row[1])for row in rows]==list(range(120)),'Lost, repeated or reordered memory counter'
    assert all(row[0]==b[0]and row[2]=='152762'for row in rows),'Native memory token or design changed'
    return dict(rows=120,token=b[0],single_entrypoint=True,all_native_instance_counts=152762,sha256=digest(raw))
def controls(raw,boots):
    rows=raw.splitlines(keepends=True);bad=[('missing_row',b''.join(rows[1:]),boots),
        ('repeated_row',rows[0]+raw,boots),('reordered_row',rows[1]+rows[0]+b''.join(rows[2:]),boots),
        ('changed_memory_token',raw.replace(rows[0].split()[0],b'FAULT',1),boots),
        ('second_entrypoint',raw,boots+boots)]
    out=[]
    for name,w,b in bad:
        assert w!=raw or b!=boots
        try:journal(w,b)
        except (AssertionError,ValueError):out.append(dict(name=name,rejected=True))
        else:raise AssertionError('Accepted '+name)
    return out
def initial_receipt():
    group='mainchip-checkpoint-initial';run=int(os.environ['GITHUB_RUN_ID'])
    release=api('releases/tags/cloud-results-'+str(run)+'-1-'+group);assets={}
    for suffix in ('.summary.json','.parts.json'):
        a=next(a for a in release['assets']if a['name'].endswith(suffix))
        raw=subprocess.check_output(['gh','api',REPO+'releases/assets/'+str(a['id']),'-H','Accept: application/octet-stream'])
        assert len(raw)==a['size']and a['digest']=='sha256:'+digest(raw);assets[suffix]=(a,raw)
    a,raw=assets['.summary.json'];b,parts=assets['.parts.json'];r=json.loads(raw)
    assert r['source_head']==os.environ['GITHUB_SHA']and r['sources_unchanged']
    assert r['status']=='PASS_ACTUAL_OPENROAD_SAME_JOB_CHECKPOINT_REQUIRES_SEPARATE_RUNNER'
    return dict(run=run,group=group,summary_sha256=digest(raw),parts_sha256=digest(parts),report=r)
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--stage',choices=('initial','cross'),required=True);args=parser.parse_args()
    assert os.environ.get('GITHUB_ACTIONS')=='true'and os.environ['GITHUB_RUN_ATTEMPT']=='1'
    out=ROOT/('cloud-mainchip-checkpoint-'+args.stage);out.mkdir(exist_ok=False);BASE.mkdir(exist_ok=False);reports.OUT=out
    r=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],stage=args.stage,route_complete=False,final_timing_complete=False,
        drt_worker_checkpoint_proven=False,scope='Actual152762-instance native OpenROAD process, open journal and Tcl/native design memory across checkpoint. Not yet an active detailed-route worker checkpoint or routed/timing acceptance.')
    def save():(out/'result.json').write_text(json.dumps(r,indent=2)+'\n')
    def run(label,command,required=True,timeout=900):
        p=subprocess.run(command,capture_output=True,text=True,timeout=timeout)
        (out/(label+'.log')).write_text(p.stdout+p.stderr)
        r.setdefault('commands',[]).append(dict(label=label,returncode=p.returncode,log_sha256=sha(out/(label+'.log'))));save()
        if required and p.returncode:
            print((p.stdout+p.stderr)[-14000:],flush=True);raise RuntimeError(label+' failed')
        return p
    owned=[];save()
    try:
        pin=json.loads((ROOT/'docs/evidence/mainchip-portable-runtime-pass-20261020.json').read_text())
        names=['native-image.tar','runtime-inventory.json','source/run/1-openroad-detailedrouting/fresh-fanout-global.odb','source/run/1-openroad-detailedrouting/fresh_fanout_native.tcl','source/run/1-openroad-detailedrouting/fresh-fanout.guide']
        runtime,proof=reports.restore_report(pin['group'],pin['run'],pin['summary_sha256'],pin['parts_sha256'],BASE/'input',names)
        assert runtime==pin['report']and runtime['sources_unchanged']
        assert runtime['isolated_db_equivalence']['byte_identical']and runtime['isolated_db_equivalence']['instances']==152762
        r['runtime_source']=proof;r['image_id']=runtime['image_id']
        r['saved_route_tcl']=(BASE/'input'/names[3]).read_text()
        r['boot_id']=Path('/proc/sys/kernel/random/boot_id').read_text().strip()
        r['run_id']=int(os.environ['GITHUB_RUN_ID']);r['job']=os.environ['GITHUB_JOB'];r['cpu_index']=min(os.sched_getaffinity(0))
        run('kernel',['uname','-a']);run('cpu',['lscpu','--json']);run('criu-check',['sudo','criu','check','--all'],False)
        build=json.loads((Path(os.environ['RUNNER_TEMP'])/'criu-build.json').read_text())
        assert build['source_commit']==CRIU_COMMIT and sha('/usr/sbin/criu')==build['binary_sha256'];r['criu_build']=build
        assert not run('empty-containers',['docker','ps','-aq']).stdout.strip()
        config="import json,pathlib;p=pathlib.Path('/etc/docker/daemon.json');d=json.loads(p.read_text())if p.exists()else{};d['experimental']=True;p.write_text(json.dumps(d))"
        run('docker-experimental',['sudo','python3','-c',config]);run('docker-restart',['sudo','systemctl','restart','docker'])
        run('load-native-image',['docker','load','-i',str(BASE/'input/native-image.tar')])
        info=json.loads(run('native-image',['docker','image','inspect',r['image_id']]).stdout)[0];assert info['Id']==r['image_id']
        inventory=json.loads((BASE/'input/runtime-inventory.json').read_text())
        assert inventory['actual_elf_sha256']==runtime['actual_elf']['actual_elf_sha256']
        odb=BASE/'input'/names[2];expected_odb=runtime['isolated_db_equivalence']['original_global_odb_sha256']
        assert sha(odb)==expected_odb
        probe=ROOT/'scripts/mainchip_process_checkpoint_probe.tcl';r['probe_sha256']=sha(probe)
        cases={name:BASE/name for name in ('reference','resumed')}
        for case in cases.values():case.mkdir()
        def command(name,case,create=False):
            env=['-e','GLIBC_TUNABLES='+TUNABLES,'-e','NSSOC_CHECKPOINT_CASE='+str(case),'-e','NSSOC_CHECKPOINT_ODB='+str(odb)]
            for key,value in sorted(inventory['environment'].items()):env+=['-e',key+'='+value]
            return ['docker','create'if create else'run',*([]if create else['-d']),'--name',name,'--network','host','--security-opt','seccomp=unconfined',
                '--cpuset-cpus',str(r['cpu_index']),'--mount','type=bind,src='+str(ROOT)+',dst='+str(ROOT)+',readonly',
                '--mount','type=bind,src='+str(case)+',dst='+str(case),'-w',str(case),*env,'--entrypoint',inventory['actual_elf'],r['image_id'],'-exit','-no_init',str(probe)]
        def verify_case(case,prefix=None):
            raw=(case/'journal.log').read_bytes();boots=(case/'boots.log').read_bytes()
            got=journal(raw,boots)
            if prefix is not None:assert raw.startswith(prefix),'Frozen open-file prefix changed'
            got['final_odb_sha256']=sha(case/'final.odb')
            assert got['final_odb_sha256']==expected_odb,'Native design memory/geometry changed'
            assert (case/'done').read_text().strip()==got['token']
            return got
        def resume(images,case):
            name='nssoc-openroad-restored';owned.append(name)
            ident=run('create-restored',command(name,case,True)).stdout.strip();assert re.fullmatch('[a-f0-9]{64}',ident)
            docker_root=Path(run('docker-root',['docker','info','--format','{{.DockerRootDir}}']).stdout.strip())
            destination=docker_root/'containers'/ident/'checkpoints/state'
            run('checkpoint-parent',['sudo','mkdir','-p',str(destination.parent)])
            run('copy-checkpoint',['sudo','cp','-a',str(images),str(destination)])
            compare="import pathlib,hashlib,sys,json;scan=lambda d:{str(p.relative_to(d)):hashlib.sha256(p.read_bytes()).hexdigest()for p in d.rglob('*')if p.is_file()};a=scan(pathlib.Path(sys.argv[1]));b=scan(pathlib.Path(sys.argv[2]));assert a and a==b;print(json.dumps({'files':len(a),'copied_exactly':True}))"
            r['checkpoint_copy']=json.loads(run('verify-checkpoint-copy',['sudo','python3','-c',compare,str(images),str(destination)]).stdout)
            restored=run('restore-native',['docker','start','--checkpoint','state',name],False)
            if restored.returncode:
                run('native-restore-diagnostic',['sudo','cat','/run/containerd/io.containerd.runtime.v2.task/moby/'+ident+'/work/restore.log'],False)
                raise RuntimeError('Native OpenROAD checkpoint restoration failed')
            assert run('wait-restored',['docker','wait',name],timeout=180).stdout.strip()=='0'
            run('restored-log',['docker','logs',name],False)
        if args.stage=='initial':
            name='nssoc-openroad-reference';owned.append(name)
            run('reference-start',command(name,cases['reference']))
            assert run('reference-wait',['docker','wait',name],timeout=180).stdout.strip()=='0'
            run('reference-log',['docker','logs',name],False);r['reference']=verify_case(cases['reference']);save()
            name='nssoc-openroad-original';owned.append(name)
            run('native-start',command(name,cases['resumed']))
            deadline=time.monotonic()+180;path=cases['resumed']/'journal.log'
            while not path.exists()or len(path.read_bytes().splitlines())<8:
                state=json.loads(subprocess.check_output(['docker','inspect',name]))[0]['State']
                assert state['Running'],'Native process exited before checkpoint'
                assert time.monotonic()<deadline,'No native checkpoint prefix';time.sleep(.1)
            state=json.loads(run('actual-native-process',['docker','inspect',name]).stdout)[0]['State']
            actual=run('actual-executable-hash',['sudo','sha256sum','/proc/'+str(state['Pid'])+'/exe']).stdout.split()[0]
            assert actual==inventory['actual_elf_sha256'];r['checkpointed_elf_sha256']=actual
            images=out/'checkpoints';images.mkdir()
            run('checkpoint-native',['docker','checkpoint','create','--checkpoint-dir',str(images),name,'state'])
            state=json.loads(run('checkpointed-state',['docker','inspect',name]).stdout)[0]['State'];assert not state['Running']
            prefix=path.read_bytes();boots=(cases['resumed']/'boots.log').read_bytes()
            assert 8<=len(prefix.splitlines())<120 and len(boots.splitlines())==1
            (out/'checkpoint-prefix.log').write_bytes(prefix);(out/'checkpoint-boots.log').write_bytes(boots)
            r['checkpoint_prefix']=dict(bytes=len(prefix),rows=len(prefix.splitlines()),sha256=digest(prefix),boots_sha256=digest(boots))
            run('readable-checkpoint',['sudo','chown','-R',str(os.getuid())+':'+str(os.getgid()),str(images)])
            r['checkpoint_images']={str(p.relative_to(images/'state')):sha(p)for p in (images/'state').rglob('*')if p.is_file()}
            assert r['checkpoint_images'];save()
            resume(images/'state',cases['resumed'])
            r['positive']=verify_case(cases['resumed'],prefix)
            r['controls']=controls((cases['resumed']/'journal.log').read_bytes(),boots)
            shutil.copytree(cases['resumed'],out/'completed')
            r['status']='PASS_ACTUAL_OPENROAD_SAME_JOB_CHECKPOINT_REQUIRES_SEPARATE_RUNNER'
        else:
            initial=initial_receipt()
            old,oldproof=reports.restore_report(initial['group'],initial['run'],initial['summary_sha256'],initial['parts_sha256'],out/'initial',list(initial['report']['outputs']))
            assert old==initial['report']and old['sources_unchanged']and old['probe_sha256']==r['probe_sha256']
            assert old['boot_id']!=r['boot_id'],'Different hosted VM boot required'
            assert old['job']!=r['job']and old['run_id']==r['run_id']
            assert old['image_id']==r['image_id']and old['cpu_index']==r['cpu_index']
            assert old['criu_build']['source_commit']==build['source_commit']
            r['initial_source']=oldproof;r['previous_boot_id']=old['boot_id']
            images=out/'initial/checkpoints/state'
            assert {str(p.relative_to(images)):sha(p)for p in images.rglob('*')if p.is_file()}==old['checkpoint_images']
            prefix=(out/'initial/checkpoint-prefix.log').read_bytes();boots=(out/'initial/checkpoint-boots.log').read_bytes()
            assert digest(prefix)==old['checkpoint_prefix']['sha256']and digest(boots)==old['checkpoint_prefix']['boots_sha256']
            (cases['resumed']/'journal.log').write_bytes(prefix);(cases['resumed']/'boots.log').write_bytes(boots)
            resume(images,cases['resumed']);r['positive']=verify_case(cases['resumed'],prefix)
            assert r['positive']==old['positive'],'Same actual native process continued differently across runners'
            r['controls']=controls((cases['resumed']/'journal.log').read_bytes(),boots)
            assert all(sha(out/'initial'/n)==v for n,v in old['outputs'].items())
            shutil.copytree(cases['resumed'],out/'completed')
            r['status']='PASS_ACTUAL_OPENROAD_LOADED_DB_PROCESS_ACROSS_DISTINCT_RUNNERS_REQUIRES_ACTIVE_DRT_PROOF'
        assert all(sha(BASE/'input'/n)==runtime['outputs'][n]for n in names)
        assert sha(probe)==r['probe_sha256'];r['sources_unchanged']=True
    except BaseException as error:
        import traceback
        r.update(status='FAIL_OR_ERROR',error=repr(error),traceback=traceback.format_exc());raise
    finally:
        for name in owned:run('cleanup-'+name,['docker','rm','-f',name],False)
        r['outputs']={str(p.relative_to(out)):sha(p)for p in out.rglob('*')if p.is_file()and p!=out/'result.json'}
        save()
if __name__=='__main__':main()
