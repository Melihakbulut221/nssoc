#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Bounded isolated cloud process-state feasibility; not a simulator restart proof."""
import hashlib,json,os,subprocess,time
from pathlib import Path
from cloud_checkpoint_state_worker import COUNT,RECORD,records
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'cloud-checkpoint-state-probe'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def verify(raw,nonce,boots):
    assert boots==[nonce.hex()],'Worker restarted from its entrypoint'
    expected=b''.join(records(nonce))
    assert len(raw)==COUNT*RECORD.size+32,'Incomplete or duplicated output'
    assert raw==expected,'Heap, RNG, numeric state, sequence or open-file offset changed'
    return dict(rows=COUNT,record_bytes=RECORD.size,heap_bytes=64*1024**2,exact_binary_output=True,heap_digest_exact=True,single_entrypoint_invocation=True,sha256=hashlib.sha256(raw).hexdigest())
def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true';OUT.mkdir(exist_ok=False)
    result=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],simulator_checkpoint_proven=False,cross_host_restore_proven=False,full_phy_accepted=False,scope='Fresh disposable runner only. Same-host restore into a separate container. Exact synthetic memory/RNG/float/open-file state. Does not checkpoint or modify any active PLL/route/electrical job.')
    def save():(OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    def run(name,args,required=True,timeout=180):
        p=subprocess.run(args,capture_output=True,text=True,timeout=timeout)
        (OUT/(name+'.log')).write_text(p.stdout+p.stderr)
        result.setdefault('commands',[]).append(dict(name=name,args=args,returncode=p.returncode,log_sha256=sha(OUT/(name+'.log'))));save()
        if required and p.returncode:
            print((p.stdout+p.stderr)[-12000:],flush=True);raise RuntimeError(name+' failed')
        return p
    save();owned=[]
    try:
        assert not run('existing-containers',['docker','ps','-aq']).stdout.strip(),'Fresh runner required'
        run('kernel',['uname','-a']);run('criu-version',['criu','--version'])
        run('kernel-capabilities',['sudo','criu','check','--all'],False)
        # Merge experimental option; do not replace any runner Docker settings.
        code="import json,pathlib;p=pathlib.Path('/etc/docker/daemon.json');d=json.loads(p.read_text())if p.exists()else{};d['experimental']=True;p.write_text(json.dumps(d))"
        run('experimental',['sudo','python3','-c',code]);run('daemon-restart',['sudo','systemctl','restart','docker'])
        run('docker-version',['docker','version']);run('pull',['docker','pull','python:3.12-slim'],timeout=300)
        info=json.loads(run('image',['docker','image','inspect','python:3.12-slim']).stdout)[0]
        result['image_id']=info['Id'];result['image_repo_digests']=info['RepoDigests'];assert result['image_repo_digests']
        worker=ROOT/'scripts/cloud_checkpoint_state_worker.py';result['worker_sha256']=sha(worker)
        data=OUT/'data';data.mkdir();checkpoints=OUT/'checkpoints';checkpoints.mkdir()
        original='nssoc-checkpoint-original';clone='nssoc-checkpoint-restored';owned=[original,clone]
        common=['--network','none','--security-opt','seccomp=unconfined','-e','PYTHONDONTWRITEBYTECODE=1','--mount','type=bind,src='+str(worker)+',dst=/probe/worker.py,readonly','--mount','type=bind,src='+str(data)+',dst=/data']
        command=[result['image_id'],'python','/probe/worker.py']
        run('start',['docker','run','-d','--name',original,*common,*command])
        deadline=time.monotonic()+45
        while not (data/'wave.bin').exists()or(data/'wave.bin').stat().st_size<50*RECORD.size:
            assert time.monotonic()<deadline,'Worker did not produce initial records';time.sleep(.2)
        run('checkpoint',['docker','checkpoint','create','--checkpoint-dir',str(checkpoints),original,'state'])
        state=json.loads(run('original-state',['docker','inspect',original]).stdout)[0]['State'];assert not state['Running']
        prefix=(data/'wave.bin').read_bytes();assert 50*RECORD.size<=len(prefix)<COUNT*RECORD.size and len(prefix)%RECORD.size==0
        boots=(data/'boots.log').read_text().splitlines();assert len(boots)==1;nonce=bytes.fromhex(boots[0])
        result['checkpoint_prefix']=dict(rows=len(prefix)//RECORD.size,bytes=len(prefix),sha256=hashlib.sha256(prefix).hexdigest(),nonce=nonce.hex());save()
        run('create-restored',['docker','create','--name',clone,*common,*command])
        run('restore',['docker','start','--checkpoint-dir',str(checkpoints),'--checkpoint','state',clone])
        p=run('wait',['docker','wait',clone],timeout=120);assert p.stdout.strip()=='0'
        raw=(data/'wave.bin').read_bytes();assert raw.startswith(prefix),'Pre-checkpoint output changed'
        done=json.loads((data/'done.json').read_text());assert done['sha256']==sha(data/'wave.bin')and done['nonce']==nonce.hex()
        result['positive']=verify(raw,nonce,(data/'boots.log').read_text().splitlines());faults=[]
        for fault in ['truncated_output','changed_memory_state','cold_restart']:
            bad=raw[:-1]if fault=='truncated_output'else raw[:-1]+bytes([raw[-1]^1])if fault=='changed_memory_state'else raw
            boot=boots+['restarted']if fault=='cold_restart'else boots
            try:verify(bad,nonce,boot)
            except AssertionError as error:faults.append(dict(fault=fault,rejected=True,reason=str(error)))
            else:raise AssertionError('Checkpoint verification corruption escaped')
        result['controls']=faults;assert sha(worker)==result['worker_sha256']
        result['status']='PASS_SAME_HOST_PROCESS_CHECKPOINT_ONLY_NOT_SIMULATOR_OR_CROSS_HOST_PROOF'
    except BaseException as error:result.update(status='FAIL_OR_ERROR',error=repr(error));raise
    finally:
        for name in owned:run('cleanup-'+name,['docker','rm','-f',name],False)
        if (OUT/'checkpoints').exists():run('readable-evidence',['sudo','chown','-R',str(os.getuid())+':'+str(os.getgid()),str(OUT/'checkpoints')],False)
        result['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};save()
        print(json.dumps({k:result[k]for k in ('status','error')if k in result}),flush=True)
if __name__=='__main__':main()
