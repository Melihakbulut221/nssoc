#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Cloud-only lossless case storage probe; no equation, vector or time change."""
import hashlib,json,os,shutil
from pathlib import Path
def sha(path):
    with Path(path).open('rb')as f:return hashlib.file_digest(f,'sha256').hexdigest()
def mount_case(case,out,run):
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    root=Path(os.environ['GITHUB_WORKSPACE']).resolve();case=Path(case).resolve();out=Path(out).resolve()
    assert case.is_relative_to(root)and out.is_relative_to(root)and case.is_dir()and not os.path.ismount(case)
    before={str(p.relative_to(case)):sha(p)for p in case.rglob('*')if p.is_file()}
    assert before and 'actual-acquisition.raw'in before and 'boots.log'in before
    backup=out/'uncompressed-case-proof';assert not backup.exists()
    image=root/'native-btrfs-case-probe.img'
    with image.open('xb')as f:f.truncate(8*1024**3)
    shutil.move(str(case),str(backup));case.mkdir()
    run('btrfs-format-owned-image',['sudo','mkfs.btrfs','-f','-m','single','-d','single',str(image)])
    run('btrfs-mount-owned-image',['sudo','mount','-o','loop,compress-force=zstd:3,noatime',str(image),str(case)])
    run('btrfs-case-owner',['sudo','chown',str(os.getuid())+':'+str(os.getgid()),str(case)])
    shutil.copytree(backup,case,dirs_exist_ok=True,copy_function=shutil.copy2)
    assert {str(p.relative_to(case)):sha(p)for p in case.rglob('*')if p.is_file()}==before
    os.sync()
    mount=json.loads(run('btrfs-mount-readback',['findmnt','--json','-T',str(case)]).stdout)['filesystems']
    assert len(mount)==1 and mount[0]['fstype']=='btrfs'and 'compress-force=zstd:3'in mount[0]['options']
    assert os.path.ismount(case)
    sizes=run('btrfs-source-compression',['sudo','compsize','-b',str(case/'actual-acquisition.raw')]).stdout
    return dict(status='MOUNTED_EXACT_NATIVE_CASE_BYTES_ON_ZSTD_BTRFS_REQUIRES_NATIVE_RESTORE',
        source_files=before,mount=mount[0],compression=sizes,original_backup_retained=True,
        logical_image_bytes=image.stat().st_size,allocated_image_bytes=image.stat().st_blocks*512,
        compression_scope='Only actual bounded native raw file, not a full1us capacity proof',
        native_or_phy_acceptance=False)
def redump(container,cmd,out,run):
    directory=out/'btrfs-checkpoints';directory.mkdir(exist_ok=False)
    run('checkpoint-btrfs-native',['docker','checkpoint','create','--checkpoint-dir',str(directory),container,'state'])
    state=json.loads(run('btrfs-stopped-native',['docker','inspect',container]).stdout)[0]['State']
    assert not state['Running']
    run('readable-btrfs-checkpoint',['sudo','chown','-R',str(os.getuid())+':'+str(os.getgid()),str(directory)])
    images={str(p.relative_to(directory/'state')):sha(p)for p in (directory/'state').rglob('*')if p.is_file()}
    assert images and 'pages-1.img'in images
    run('remove-first-restored-container',['docker','rm','-f',container])
    ident=run('recreate-btrfs-native',cmd).stdout.strip()
    root=Path(run('btrfs-docker-root',['docker','info','--format','{{.DockerRootDir}}']).stdout.strip())
    target=root/'containers'/ident/'checkpoints/state'
    run('btrfs-default-checkpoint-dir',['sudo','mkdir','-p',str(target.parent)])
    run('btrfs-copy-checkpoint',['sudo','cp','-a',str(directory/'state'),str(target)])
    check="import pathlib,hashlib,json,sys;r=pathlib.Path(sys.argv[1]);print(json.dumps({str(p.relative_to(r)):hashlib.sha256(p.read_bytes()).hexdigest()for p in r.rglob('*')if p.is_file()}))"
    got=json.loads(run('btrfs-checkpoint-copy-proof',['sudo','python3','-c',check,str(target)]).stdout)
    assert got==images
    q=run('restore-btrfs-checkpoint',['docker','start','--checkpoint','state',container],False)
    if q.returncode:
        run('btrfs-restore-detail',['sudo','cat','/run/containerd/io.containerd.runtime.v2.task/moby/'+ident+'/work/restore.log'],False)
        raise RuntimeError('Native Btrfs redump/restore failed')
    return dict(checkpoint_images=images,exact_copied_images=True,same_native_command=True)

def restore_failure(container_id,out,run):
    code="""import pathlib,json,sys
cid=sys.argv[1];roots=[pathlib.Path('/run/containerd'),pathlib.Path('/run/docker/containerd'),pathlib.Path('/var/lib/docker/containers')/cid]
rows=[]
for root in roots:
 if root.exists():
  for p in root.rglob('*.log'):
   if p.name in ('restore.log','dump.log')or 'criu'in p.name:
    try:rows.append(dict(path=str(p),text=p.read_text(errors='replace')))
    except OSError as e:rows.append(dict(path=str(p),error=repr(e)))
print(json.dumps(rows))
"""
    run('durable-criu-error-log',['sudo','cat',str(out/'criu-durable.log')],False)
    run('all-owned-criu-restore-logs',['sudo','python3','-c',code,container_id],False)
    run('docker-restore-journal',['sudo','journalctl','-u','docker','--no-pager','-n','500'],False)
    run('runtime-versions',['docker','version'],False)

def durable_logs(out,run):
    config='log-file '+str(out/'criu-durable.log')+'\n'
    code="import pathlib,sys;p=pathlib.Path('/etc/criu/runc.conf');assert not p.exists()or not p.read_text().strip();p.parent.mkdir(parents=True,exist_ok=True);p.write_text(sys.argv[1]);print(p.read_text())"
    run('configure-durable-criu-log',['sudo','python3','-c',code,config])
    return dict(config='/etc/criu/runc.conf',text=config,scope='Log destination only; no restore behavior or native input change')
