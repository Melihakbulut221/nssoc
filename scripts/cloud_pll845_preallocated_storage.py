#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Allocate a real compressed cloud workspace before restoring any native capsule.

This changes storage only. No waveform may be trimmed or omitted. A bounded
native proof does not establish the capacity of the complete full1us capture.
"""
import hashlib,json,os,shutil,subprocess
from pathlib import Path
GIB=1024**3
HOST_ALLOCATION_MARGIN=6*GIB
HOST_CHECKPOINT_RESERVE=4*GIB
NATIVE_CHECKPOINT_RESERVE=12*GIB
MIN_IMAGE=90*GIB
def sha(path):
    with Path(path).open('rb')as f:return hashlib.file_digest(f,'sha256').hexdigest()
def choose_image(free):
    assert isinstance(free,int)and free>=0
    size=((free-HOST_ALLOCATION_MARGIN)//GIB)*GIB
    assert size>=MIN_IMAGE,'Hosted capacity too small for this production-sized storage qualification'
    assert free-size>=HOST_ALLOCATION_MARGIN
    return size
def budget(inside_free,host_free,logical,allocated,same_device):
    assert logical>=MIN_IMAGE and allocated>=logical,'Backing image allocation was released'
    assert same_device,'Workspace is not the allocated Btrfs filesystem'
    assert inside_free>=0 and host_free>=0
    return dict(inside_free_bytes=inside_free,backing_host_free_bytes=host_free,
        backing_logical_bytes=logical,backing_allocated_bytes=allocated,
        native_checkpoint_reserve_bytes=NATIVE_CHECKPOINT_RESERVE,
        backing_checkpoint_reserve_bytes=HOST_CHECKPOINT_RESERVE,
        checkpoint_required=inside_free<NATIVE_CHECKPOINT_RESERVE or host_free<HOST_CHECKPOINT_RESERVE,
        preallocated_capacity_retained=True)
def controls():
    assert choose_image(100*GIB)==94*GIB
    rejected=[]
    for free in (0,95*GIB):
        try:choose_image(free)
        except AssertionError:rejected.append('insufficient-host-'+str(free))
        else:raise AssertionError('Small host accepted')
    good=(20*GIB,6*GIB,94*GIB,94*GIB,True)
    assert not budget(*good)['checkpoint_required']
    assert budget(NATIVE_CHECKPOINT_RESERVE-1,*good[1:])['checkpoint_required']
    assert budget(good[0],HOST_CHECKPOINT_RESERVE-1,*good[2:])['checkpoint_required']
    for name,args in [('released-extents',(*good[:3],93*GIB,True)),('wrong-superblock',(*good[:4],False))]:
        try:budget(*args)
        except AssertionError:rejected.append(name)
        else:raise AssertionError('Invalid storage accepted')
    return dict(rejected=rejected,independent_inside_and_outside_reserves=True,
        original12GiB_native_reserve_retained=True,full_capacity_proven=False)
def state_path():
    return Path(os.environ['RUNNER_TEMP']).resolve()/'nssoc-pll845-preallocated-storage'/'state.json'
def prepare_workspace(root,out):
    assert os.environ.get('GITHUB_ACTIONS')=='true'and os.environ.get('RUNNER_ENVIRONMENT')=='github-hosted'
    root=Path(root).resolve();out=Path(out).resolve()
    assert str(root)=='/home/runner/work/nssoc/nssoc'and out.is_relative_to(root)
    assert not out.exists()and not os.path.ismount(root)
    assert not (root/'cloud-pll845-native-acquisition').exists(),'Mount BEFORE large native capsule download'
    scratch=state_path().parent
    assert not scratch.is_relative_to(root)
    scratch.mkdir(exist_ok=False);logs=scratch/'logs';logs.mkdir()
    result=dict(status='PREPARING_PREALLOCATED_WORKSPACE',root=str(root),out=str(out),
        source_head=os.environ['GITHUB_SHA'],before_any_native_capsule_download=True,
        commands=[],full_capacity_proven=False,full_phy_accepted=False)
    def save():state_path().write_text(json.dumps(result,indent=2)+'\n')
    def run(label,args):
        p=subprocess.run(args,capture_output=True,text=True,timeout=900)
        dest=logs/(label+'.log');dest.write_text(p.stdout+p.stderr)
        result['commands'].append(dict(label=label,args=args,returncode=p.returncode,sha256=sha(dest)));save()
        assert p.returncode==0,(label,(p.stdout+p.stderr)[-5000:])
        return p.stdout
    save()
    try:
        info=json.loads(run('original-docker-info',['docker','info','--format','{{json .}}']))
        assert info['Driver']=='overlay2'
        assert not run('empty-docker',['docker','ps','-aq']).strip()
        free=shutil.disk_usage(scratch).free;size=choose_image(free)
        image=scratch/'workspace.img';volume=scratch/'volume';volume.mkdir()
        with image.open('xb')as f:os.posix_fallocate(f.fileno(),0,size)
        assert image.stat().st_size==size and image.stat().st_blocks*512>=size
        result.update(image=str(image),volume=str(volume),original_host_free_bytes=free,logical_image_bytes=size,
            initial_allocated_image_bytes=image.stat().st_blocks*512,allocation_margin_bytes=HOST_ALLOCATION_MARGIN)
        save()
        # Both are necessary: mkfs discard and mounted discard are separate.
        run('format-without-discard',['sudo','mkfs.btrfs','-K','-f','-m','single','-d','single',str(image)])
        assert image.stat().st_blocks*512>=size,'mkfs released preallocated backing extents'
        run('mount-without-discard',['sudo','mount','-o','loop,nodiscard,compress-force=zstd:3,noatime',str(image),str(volume)])
        run('volume-owner',['sudo','chown',str(os.getuid())+':'+str(os.getgid()),str(volume)])
        relative=root.relative_to('/');nested=volume/relative;nested.parent.mkdir(parents=True,exist_ok=True)
        immutable={str(p.relative_to(root)):sha(p)for p in root.rglob('*')if p.is_file()}
        shutil.copytree(root,nested,symlinks=True,copy_function=shutil.copy2)
        assert all(sha(nested/n)==h for n,h in immutable.items())
        run('bind-original-workspace',['sudo','mount','--bind',str(nested),str(root)])
        os.chdir(root)
        assert all(sha(root/n)==h for n,h in immutable.items())
        assert not out.exists()
        docker_root=volume/Path(info['DockerRootDir']).relative_to('/')
        docker_root.mkdir(parents=True,exist_ok=False)
        config="import pathlib,json,sys;p=pathlib.Path('/etc/docker/daemon.json');d=json.loads(p.read_text())if p.exists()else{};d['data-root']=sys.argv[1];d['storage-driver']='overlay2';p.write_text(json.dumps(d));print(p.read_text())"
        run('configure-shared-docker-root',['sudo','python3','-c',config,str(docker_root)])
        mount=json.loads(run('mount-readback',['findmnt','--json','-T',str(root)]))['filesystems']
        assert len(mount)==1 and mount[0]['fstype']=='btrfs'
        opts=mount[0]['options'].split(',')
        assert 'compress-force=zstd:3'in opts and not any(x=='discard'or x.startswith('discard=')for x in opts)
        assert 'nodatacow'not in opts and 'nodatasum'not in opts
        fsroot=run('filesystem-root',['findmnt','-n','-o','FSROOT','-T',str(root)]).strip()
        assert fsroot=='/'+str(relative)and os.path.ismount(root)
        assert root.stat().st_dev==volume.stat().st_dev==docker_root.stat().st_dev
        result.update(status='PREALLOCATED_SHARED_WORKSPACE_READY_BEFORE_NATIVE_DOWNLOAD',
            immutable_workspace_files=immutable,original_workspace_hidden_but_retained=True,
            docker_root=str(docker_root),original_docker_root=info['DockerRootDir'],
            filesystem_root=fsroot,mount=mount[0],workspace_device=root.stat().st_dev)
        result['capacity']=budget(shutil.disk_usage(root).free,shutil.disk_usage(scratch).free,
            image.stat().st_size,image.stat().st_blocks*512,root.stat().st_dev==volume.stat().st_dev)
        assert not result['capacity']['checkpoint_required']
        save();return result
    except BaseException as e:
        result.update(status='FAIL_PREALLOCATED_WORKSPACE',error=repr(e));save();raise
def capacity(root):
    r=json.loads(state_path().read_text());assert r['status']=='PREALLOCATED_SHARED_WORKSPACE_READY_BEFORE_NATIVE_DOWNLOAD'
    root=Path(root);volume=Path(r['volume']);image=Path(r['image'])
    assert str(root.resolve())==r['root']
    return budget(shutil.disk_usage(root).free,shutil.disk_usage(image.parent).free,
        image.stat().st_size,image.stat().st_blocks*512,root.stat().st_dev==volume.stat().st_dev==r['workspace_device'])
def capture_ready(case,out,run,prepared):
    root=Path(os.environ['GITHUB_WORKSPACE']).resolve();case=Path(case);out=Path(out)
    assert case.is_relative_to(root)and out.is_relative_to(root)
    assert case.stat().st_dev==root.stat().st_dev==prepared['workspace_device']
    measured=capacity(root);assert not measured['checkpoint_required'],'Insufficient native or backing reserve before resume'
    proof=out/'preallocated-storage-proof';proof.mkdir(exist_ok=False)
    shutil.copytree(state_path().parent/'logs',proof/'logs');shutil.copyfile(state_path(),proof/'state.json')
    compressed=run('preallocated-raw-compression',['sudo','compsize','-b',str(case/'actual-acquisition.raw')]).stdout
    return dict(status='ACTUAL_NATIVE_CASE_RESTORED_DIRECTLY_ON_PREALLOCATED_SHARED_BTRFS',
        preparation=prepared,capacity=measured,compression=compressed,
        before_download_mount_verified=True,full_capacity_proven=False,full_phy_accepted=False)
if __name__=='__main__':print(json.dumps(controls()))
