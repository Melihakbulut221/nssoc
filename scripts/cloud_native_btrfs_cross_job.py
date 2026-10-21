#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Restore an immutable native845 SPICE process in a separate GitHub job."""
import hashlib,json,os,re,shutil,subprocess,tarfile
from pathlib import Path
import numpy as np
import cloud_native_btrfs_case as compressed
import cloud_tx_input_driver as physical
import cloud_native_checkpoint_probe as native
import cloud_pll_vbic_acquisition as acquisition
from route_cloud_newer_postcts import fetch
ROOT=physical.ROOT;OUT=ROOT/'cloud-native-btrfs-cross-job'
SOURCE={'run': 38904997140, 'group': 'native-portable-checkpoint', 'root': 'cloud-native-portable-checkpoint', 'bytes': 59772311, 'sha': '30bad1656b8c6f291d805b3161b8336825d7608c3a04355c57e10a6f8c0f7331', 'summary': '5f261d535f386661979ef9854e26dead27b6ba1d4d681eed931d5c300faed176'}
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
    clone=None;case=None;save()
    try:
        assert sha(native.__file__)=='28e3ca20e1d7cce96ac68f4ec19e510326d8e96ed0da77ddc16ab5b3c5e86231'
        assert not run('empty-runner',['docker','ps','-aq']).stdout.strip()
        result['destination_cpu']=json.loads(run('destination-lscpu',['lscpu','--json']).stdout)
        fields={r['field']:r['data']for r in result['destination_cpu']['lscpu']}
        result['destination_has_avx512f']='avx512f'in fields['Flags:'].split();save()
        result['probe_target']='Ext4 checkpoint to compressed Btrfs, then native Btrfs checkpoint/restore; CPU features recorded independently'
        run('destination-kernel',['uname','-a'])
        physical.OUT=OUT;restored,prior=physical.restore(SOURCE)
        assert prior['native_checkpoint_proven']and prior['status']=='PASS_NATIVE_PHYSICAL845_MASKED_IFUNC_CHECKPOINT_BIT_EXACT_BOUNDED4NS_NOT_CROSS_JOB_OR_ACQUISITION'
        assert len(prior['controls'])==3 and all(x['rejected']for x in prior['controls'])
        assert prior['glibc_tunables']=='glibc.cpu.hwcaps=-AVX512F,-AVX512CD,-AVX512BW,-AVX512DQ,-AVX512ER,-AVX512PF,-AVX512VL,-RTM'
        assert prior['original_bounded_trajectory_unchanged'] and prior['positive']['values_sha256']=='633f0aaa88c7c08655e6d1b7f99d08284916746331f7c50c03091161ca2bbd1e'
        source_fields={r['field']:r['data']for r in prior['cpu']['lscpu']};assert 'avx512f'in source_fields['Flags:'].split()
        result.update(source_cpu=prior['cpu'],source_has_avx512f=True,glibc_tunables=prior['glibc_tunables'])
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
        result['compressed_case']=compressed.mount_case(case,OUT,run);save()
        result['criu_log_configuration']=compressed.durable_logs(OUT,run);save()
        result['criu_build']=json.loads((Path(os.environ['RUNNER_TEMP'])/'criu-build.json').read_text());assert sha('/usr/sbin/criu')==result['criu_build']['binary_sha256']
        assert result['criu_build']['source_commit']==prior['criu_build']['source_commit']=='9539417f3e3cfa4eb84c319cd71f4d52f1f08645'
        run('criu-check',['sudo','criu','check','--all'],False)
        config="import json,pathlib;p=pathlib.Path('/etc/docker/daemon.json');d=json.loads(p.read_text())if p.exists()else{};d['experimental']=True;d['debug']=True;p.write_text(json.dumps(d))"
        run('docker-experimental',['sudo','python3','-c',config]);run('docker-restart',['sudo','systemctl','restart','docker'])
        assert sha(source/'native-image.tar')==prior['native_image_sha256'];run('load-native-image',['docker','load','-i',str(source/'native-image.tar')])
        image=json.loads(run('loaded-image',['docker','image','inspect',prior['image_id']]).stdout)[0];assert image['Id']==prior['image_id']
        original_command=next(x['args']for x in prior['commands']if x['label']=='start-native');cpu=original_command[original_command.index('--cpuset-cpus')+1];assert int(cpu)in os.sched_getaffinity(0)
        engine=source/'runtime/patched-ngspice';assert sha(engine)==native.ENGINE_SHA
        clone='nssoc-native-cross-job';code='printf "native-entrypoint\\n" >> boots.log; exec "'+str(engine)+'" -n -b actual-acquisition.cir'
        cmd=['docker','create','--name',clone,'--network','host','--security-opt','seccomp=unconfined','--cpuset-cpus',cpu,'--mount','type=bind,src='+str(ROOT)+',dst='+str(ROOT)+',readonly','--mount','type=bind,src='+str(case)+',dst='+str(case),'-w',str(case),'-e','SPICE_SCRIPTS='+str(case),'-e','OMP_NUM_THREADS=1','-e','RAYON_NUM_THREADS=1','-e','GLIBC_TUNABLES='+prior['glibc_tunables'],'--entrypoint','/bin/dash',prior['image_id'],'-c',code]
        assert cmd[cmd.index('--network'):]==original_command[original_command.index('--network'):]
        clone_id=run('create-native-clone',cmd).stdout.strip();assert re.fullmatch('[0-9a-f]{64}',clone_id)
        root=Path(run('docker-root',['docker','info','--format','{{.DockerRootDir}}']).stdout.strip());destination=root/'containers'/clone_id/'checkpoints/state'
        checkpoints=source/'checkpoints/state'
        assert {str(p.relative_to(checkpoints)):sha(p)for p in checkpoints.rglob('*')if p.is_file()}==prior['checkpoint_images']
        run('default-checkpoint-dir',['sudo','mkdir','-p',str(destination.parent)]);run('copy-native-checkpoint',['sudo','cp','-a',str(checkpoints),str(destination)])
        check="import pathlib,hashlib,sys,json;scan=lambda r:{str(p.relative_to(r)):hashlib.sha256(p.read_bytes()).hexdigest()for p in r.rglob('*')if p.is_file()};a=scan(pathlib.Path(sys.argv[1]));b=scan(pathlib.Path(sys.argv[2]));assert a and a==b;print(json.dumps(a))"
        transfer=json.loads(run('copy-proof',['sudo','python3','-c',check,str(checkpoints),str(destination)]).stdout);assert transfer==prior['checkpoint_images'];result['checkpoint_images']=transfer;save()
        result['external_superblock']=compressed.verify_external_superblock(clone,case,OUT,run);save()
        started=run('restore-native',['docker','start','--checkpoint','state',clone],False)
        if started.returncode:
            compressed.restore_failure(clone_id,OUT,run)
            run('restore-native-detail',['sudo','cat','/run/containerd/io.containerd.runtime.v2.task/moby/'+clone_id+'/work/restore.log'],False);raise RuntimeError('Separate-job native restore failed')
        run('pre-redump-log',['docker','logs',clone],False)
        result['compressed_redump']=compressed.redump(clone,cmd,OUT,run);save()
        exitcode=run('wait-native',['docker','wait',clone],timeout=900).stdout.strip();run('continued-log',['docker','logs',clone],False)
        log=(source/'original-prefix-log.log').read_text()+(OUT/'pre-redump-log.log').read_text()+(OUT/'continued-log.log').read_text();(OUT/'full-native.log').write_text(log)
        assert exitcode=='0',(exitcode,log[-7000:])
        sn,sv,continued=native.inspect_capture(case,vectors,log);result['continued']=continued
        result['positive']=native.verify((rn,rv),(sn,sv),(case/'boots.log').read_text().splitlines())
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
        result['compressed_case']['final_compression']=run('btrfs-final-compression',['sudo','compsize','-b',str(case/'actual-acquisition.raw')]).stdout
        shutil.copyfile(case/'actual-acquisition.raw',OUT/'continued.raw');shutil.copyfile(case/'op.raw',OUT/'op.raw')
        result.update(status='PASS_NATIVE_PHYSICAL845_EXT4_TO_ZSTD_BTRFS_REDUMP_RESTORE_BIT_EXACT_BOUNDED4NS_NOT_FULL_STORAGE_OR_ACQUISITION',cross_job_native_restore_proven=True,complete_raw_sha256=sha(OUT/'continued.raw'),unchanged_native_inputs=True)
    except BaseException as e:result.update(status='FAIL_OR_ERROR',error=repr(e));raise
    finally:
        if clone:
            run('final-native-log',['docker','logs',clone],False);run('cleanup-native',['docker','rm','-f',clone],False)
        if case is not None:
            for filename in ('actual-acquisition.raw','op.raw','boots.log'):
                if (case/filename).exists():shutil.copyfile(case/filename,OUT/('retained-'+filename))
        run('readable-durable-criu-log',['sudo','chown',str(os.getuid())+':'+str(os.getgid()),str(OUT/'criu-durable.log')],False)
        result['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};save()
        print(json.dumps({k:result[k]for k in ('status','error','cross_job_native_restore_proven')if k in result}),flush=True)
if __name__=='__main__':main()
