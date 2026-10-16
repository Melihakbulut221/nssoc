#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Restore a real prior-job process image; no cold-start or waveform replay."""
import hashlib,json,os,platform,re,shutil,subprocess
from pathlib import Path
import cloud_tx_input_driver as physical
from cloud_checkpoint_state_probe import verify,sha
ROOT=physical.ROOT;OUT=ROOT/'cloud-checkpoint-cross-runner-probe'
SOURCE=dict(run=38888817734,group='checkpoint-state-probe',root='cloud-checkpoint-state-probe',bytes=2453634,sha='fc5c53b7a39490ee3e12eb9534f4f6bb9e80bcb486a06b7a2a38c0fd746258de',summary='beb505bb17646936a30486095f2abf3d6c210abb904ac2583baec81a82fa5789')
def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true';OUT.mkdir(exist_ok=False)
    result=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],source=SOURCE,simulator_checkpoint_proven=False,cross_runner_restore_proven=False,full_phy_accepted=False)
    def save():(OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    def run(name,args,required=True,timeout=180):
        p=subprocess.run(args,capture_output=True,text=True,timeout=timeout);log=OUT/(name+'.log');log.write_text(p.stdout+p.stderr)
        result.setdefault('commands',[]).append(dict(name=name,args=args,returncode=p.returncode,log_sha256=sha(log)));save()
        if required and p.returncode:print((p.stdout+p.stderr)[-14000:],flush=True);raise RuntimeError(name+' failed')
        return p
    save();owned=[]
    try:
        physical.OUT=OUT;source,prior=physical.restore(SOURCE)
        assert prior['status']=='PASS_SAME_HOST_PROCESS_CHECKPOINT_ONLY_NOT_SIMULATOR_OR_CROSS_HOST_PROOF'
        assert len(prior['controls'])==3 and all(c['rejected']for c in prior['controls'])
        old_kernel=(source/'kernel.log').read_text().split();assert old_kernel[1]!=platform.node(),'Separate runner required'
        result['runner_identity']=dict(previous=old_kernel[1],current=platform.node(),previous_kernel=old_kernel[2],current_kernel=platform.release())
        assert not run('existing-containers',['docker','ps','-aq']).stdout.strip()
        build=json.loads((Path(os.environ['RUNNER_TEMP'])/'criu-build.json').read_text());assert build['source_commit']==prior['criu_build']['source_commit']
        assert sha('/usr/sbin/criu')==build['binary_sha256'];result['criu_build']=build
        run('kernel',['uname','-a']);run('criu-version',['criu','--version']);run('kernel-capabilities',['sudo','criu','check','--all'],False)
        code="import json,pathlib;p=pathlib.Path('/etc/docker/daemon.json');d=json.loads(p.read_text())if p.exists()else{};d['experimental']=True;p.write_text(json.dumps(d))"
        run('experimental',['sudo','python3','-c',code]);run('daemon-restart',['sudo','systemctl','restart','docker']);run('docker-version',['docker','version'])
        assert len(prior['image_repo_digests'])==1;image=prior['image_repo_digests'][0]
        run('pull',['docker','pull',image],timeout=300);info=json.loads(run('image',['docker','image','inspect',image]).stdout)[0]
        assert info['Id']==prior['image_id'];result['image_id']=info['Id'];result['image_repo_digests']=info['RepoDigests']
        worker=ROOT/'scripts/cloud_checkpoint_state_worker.py';assert sha(worker)==prior['worker_sha256'];result['worker_sha256']=sha(worker)
        # Recreate exactly the frozen open file prefix. This fixture's complete
        # first-run bytes are retained and prefix SHA is checked independently.
        data=ROOT/'cloud-checkpoint-state-probe/data';data.mkdir(parents=True,exist_ok=False)
        prefix=(source/'data/wave.bin').read_bytes()[:prior['checkpoint_prefix']['bytes']]
        assert hashlib.sha256(prefix).hexdigest()==prior['checkpoint_prefix']['sha256']
        (data/'wave.bin').write_bytes(prefix);shutil.copyfile(source/'data/boots.log',data/'boots.log')
        nonce=bytes.fromhex(prior['checkpoint_prefix']['nonce']);assert (data/'boots.log').read_text().splitlines()==[nonce.hex()]
        images=source/'checkpoints/state';inventory={str(p.relative_to(images)):sha(p)for p in images.rglob('*')if p.is_file()}
        assert inventory==prior['checkpoint_images'];result['checkpoint_images']=inventory;result['checkpoint_prefix']=prior['checkpoint_prefix'];save()
        clone='nssoc-checkpoint-cross-runner';owned=[clone]
        common=['--network','host','--security-opt','seccomp=unconfined','-e','PYTHONDONTWRITEBYTECODE=1','--mount','type=bind,src='+str(worker)+',dst=/probe/worker.py,readonly','--mount','type=bind,src='+str(data)+',dst=/data']
        clone_id=run('create',['docker','create','--name',clone,*common,info['Id'],'python','/probe/worker.py']).stdout.strip();assert re.fullmatch('[0-9a-f]{64}',clone_id)
        docker_root=Path(run('docker-root',['docker','info','--format','{{.DockerRootDir}}']).stdout.strip());assert docker_root.is_absolute()
        dest=docker_root/'containers'/clone_id/'checkpoints/state'
        run('prepare-default-checkpoint',['sudo','mkdir','-p',str(dest.parent)]);run('copy-checkpoint',['sudo','cp','-a',str(images),str(dest)])
        check="import pathlib,hashlib,sys,json;r=pathlib.Path(sys.argv[1]);print(json.dumps({str(p.relative_to(r)):hashlib.sha256(p.read_bytes()).hexdigest()for p in r.rglob('*')if p.is_file()},sort_keys=True))"
        copied=json.loads(run('copy-proof',['sudo','python3','-c',check,str(dest)]).stdout);assert copied==inventory
        restored=run('restore',['docker','start','--checkpoint','state',clone],False)
        if restored.returncode:
            log=Path('/run/containerd/io.containerd.runtime.v2.task/moby')/clone_id/'work/restore.log';n=run('native-restore-log',['sudo','cat',str(log)],False)
            print((restored.stdout+restored.stderr+n.stdout+n.stderr)[-14000:],flush=True);raise RuntimeError('Cross-runner restore failed')
        assert run('wait',['docker','wait',clone],timeout=120).stdout.strip()=='0'
        raw=(data/'wave.bin').read_bytes();assert raw.startswith(prefix)
        result['positive']=verify(raw,nonce,(data/'boots.log').read_text().splitlines())
        assert sha(data/'wave.bin')==prior['positive']['sha256']==sha(source/'data/wave.bin'),'Cross-runner output differs from original full continuation'
        done=json.loads((data/'done.json').read_text());assert done['sha256']==sha(data/'wave.bin') and done['nonce']==nonce.hex()
        shutil.copytree(data,OUT/'data');assert all(sha(source/p)==v for p,v in prior['outputs'].items()) and sha(worker)==prior['worker_sha256']
        result.update(status='PASS_DIFFERENT_RUNNER_PROCESS_STATE_RESTORED_EXACTLY_NOT_NATIVE_SIMULATOR_PROOF',cross_runner_restore_proven=True)
    except BaseException as error:result.update(status='FAIL_OR_ERROR',error=repr(error));raise
    finally:
        for name in owned:run('cleanup-'+name,['docker','rm','-f',name],False)
        result['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};save();print(json.dumps({k:result[k]for k in ('status','error')if k in result}),flush=True)
if __name__=='__main__':main()
