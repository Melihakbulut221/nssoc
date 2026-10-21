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
    assert str(root)=='/home/runner/work/nssoc/nssoc'
    assert case.is_relative_to(root)and out.is_relative_to(root)and case.is_dir()and not os.path.ismount(root)
    before={str(p.relative_to(case)):sha(p)for p in case.rglob('*')if p.is_file()}
    assert before and 'actual-acquisition.raw'in before and 'boots.log'in before
    # CRIU requires external mounts from the same original superblock to
    # remain on the same destination superblock. Migrate workspace AND
    # Docker's external /etc files, preserving filesystem-relative paths.
    info=json.loads(run('btrfs-original-docker-info',['docker','info','--format','{{json .}}']).stdout)
    assert info['Driver']=='overlay2','Bounded probe requires the original overlay2 driver'
    assert not run('btrfs-empty-docker-proof',['docker','ps','-aq']).stdout.strip()
    scratch=Path(os.environ['RUNNER_TEMP']).resolve()/'nssoc-btrfs-superblock-probe'
    assert not scratch.is_relative_to(root)
    scratch.mkdir(exist_ok=False)
    image=scratch/'case.img';volume=scratch/'volume';volume.mkdir()
    with image.open('xb')as f:f.truncate(12*1024**3)
    run('btrfs-format-owned-image',['sudo','mkfs.btrfs','-f','-m','single','-d','single',str(image)])
    run('btrfs-mount-owned-image',['sudo','mount','-o','loop,compress-force=zstd:3,noatime',str(image),str(volume)])
    run('btrfs-volume-owner',['sudo','chown',str(os.getuid())+':'+str(os.getgid()),str(volume)])
    relative=root.relative_to(root.anchor);nested=volume/relative
    nested.parent.mkdir(parents=True,exist_ok=True)
    immutable={str(p.relative_to(root)):sha(p)for p in root.rglob('*')if p.is_file()and not p.is_relative_to(out)}
    shutil.copytree(root,nested,symlinks=True,copy_function=shutil.copy2)
    assert all(sha(nested/n)==h for n,h in immutable.items())
    run('btrfs-bind-original-workspace',['sudo','mount','--bind',str(nested),str(root)])
    os.chdir(root)
    assert all(sha(root/n)==h for n,h in immutable.items())
    assert {str(p.relative_to(case)):sha(p)for p in case.rglob('*')if p.is_file()}==before
    assert (volume/case.relative_to(case.anchor)/'actual-acquisition.raw').samefile(case/'actual-acquisition.raw')
    docker_root=volume/Path(info['DockerRootDir']).relative_to('/')
    docker_root.mkdir(parents=True,exist_ok=False)
    config="import pathlib,json,sys;p=pathlib.Path('/etc/docker/daemon.json');d=json.loads(p.read_text())if p.exists()else{};d['data-root']=sys.argv[1];d['storage-driver']='overlay2';p.write_text(json.dumps(d));print(p.read_text())"
    run('btrfs-owned-docker-root',['sudo','python3','-c',config,str(docker_root)])
    os.sync()
    mount=json.loads(run('btrfs-mount-readback',['findmnt','--json','-T',str(case)]).stdout)['filesystems']
    assert len(mount)==1 and mount[0]['fstype']=='btrfs'and 'compress-force=zstd:3'in mount[0]['options']
    fsroot=run('btrfs-filesystem-root-readback',['findmnt','-n','-o','FSROOT','-T',str(root)]).stdout.strip()
    assert fsroot=='/'+str(relative)and os.path.ismount(root)
    assert root.stat().st_dev==case.stat().st_dev==docker_root.stat().st_dev
    sizes=run('btrfs-source-compression',['sudo','compsize','-b',str(case/'actual-acquisition.raw')]).stdout
    return dict(status='MOUNTED_EXACT_WORKSPACE_AND_CONFIGURED_SHARED_DOCKER_SUPERBLOCK_REQUIRES_NATIVE_RESTORE',
        source_files=before,mount=mount[0],compression=sizes,original_workspace_hidden_but_retained=True,
        immutable_workspace_files=immutable,filesystem_root=fsroot,volume_path=str(volume),
        docker_root=str(docker_root),original_docker_root=info['DockerRootDir'],storage_driver='overlay2',
        logical_image_bytes=image.stat().st_size,allocated_image_bytes=image.stat().st_blocks*512,
        compression_scope='Only actual bounded native raw file, not a full1us capacity proof',
        native_or_phy_acceptance=False)

def external_paths(row,root,case):
    raw=[row.get(k)for k in ('ResolvConfPath','HostnamePath','HostsPath')]
    assert all(isinstance(x,str)and x and Path(x).is_absolute()and '..'not in Path(x).parts for x in raw),'Docker external paths unavailable or relative'
    paths=[root,case,*map(Path,raw)]
    assert len(set(paths))==5,'External bind paths must be distinct'
    return paths

def external_path_controls():
    good=dict(ResolvConfPath='/native/resolv.conf',HostnamePath='/native/hostname',HostsPath='/native/hosts')
    assert len(external_paths(good,Path('/repo'),Path('/repo/case')))==5
    rejected=[]
    for label in ('empty','relative','missing','duplicate','parent-traversal'):
        bad=dict(good)
        if label=='empty':bad['HostsPath']=''
        elif label=='relative':bad['HostsPath']='hosts'
        elif label=='missing':del bad['HostsPath']
        elif label=='duplicate':bad['HostsPath']=bad['HostnamePath']
        else:bad['HostsPath']='/native/../hosts'
        try:external_paths(bad,Path('/repo'),Path('/repo/case'))
        except AssertionError:rejected.append(label)
        else:raise AssertionError('Invalid Docker path accepted: '+label)
    return dict(valid_five_paths=True,rejected=rejected)

def verify_external_superblock(container,case,out,run):
    row=json.loads(run('btrfs-container-filesystem-readback',['docker','inspect',container]).stdout)[0]
    root=Path(os.environ['GITHUB_WORKSPACE']).resolve()
    paths=external_paths(row,root,Path(case))
    # Docker owns these directories as root; inspect, never chmod/chown them.
    code="import json,pathlib,sys;ps=[pathlib.Path(x)for x in json.loads(sys.argv[1])];assert len(set(ps))==5 and all(p.is_absolute()and p.exists()for p in ps);print(json.dumps({str(p):p.stat().st_dev for p in ps}))"
    ids=json.loads(run('btrfs-five-external-device-stat',['sudo','python3','-c',code,json.dumps(list(map(str,paths)))]).stdout)
    assert set(ids)==set(map(str,paths))and len(ids)==5
    assert len(set(ids.values()))==1,'Original external superblock sharing was not preserved'
    run('btrfs-container-mount-readback',['sudo','findmnt','--json','-T',row['ResolvConfPath']])
    return dict(external_filesystem_devices=ids,same_superblock=True,source_image_and_native_command_unchanged=True)

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
