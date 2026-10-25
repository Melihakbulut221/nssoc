#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Exact restored-container runtime binding; source-only until separate authorization."""
import hashlib,json,os,re,stat,subprocess,time
from pathlib import Path
from mainchip_userstack_identity import snapshot,object_id,ProcessPin,file_sha,module_inventory
ROOT=Path(__file__).resolve().parents[1]
INVENTORY_SHA='f0dd493a1f5106da8a86bf0de6821d6ddbeed25050717c5706225c3d4fdfdbfa'
INVENTORY_BYTES=6246138
ELF='25a5e9ba1cbb76b820af97cfc8d87b7a2d1bc1203091d83ee4eee859c2e9a04b'
IMAGE='sha256:113cc2e5500e0152a2137336ae092c7caeccb5f8b95b17874fd649d097b8daf8'
MODE='EXACT_RESTORED_OPENROAD_STACK_DIAGNOSTIC'
def inventory(raw):
    assert len(raw)==INVENTORY_BYTES and hashlib.sha256(raw).hexdigest()==INVENTORY_SHA
    x=json.loads(raw)
    assert x['actual_elf_sha256']==ELF and x['actual_elf_bytes']==103633024
    assert x['files'][x['actual_elf']]==dict(sha256=ELF,bytes=103633024)
    assert len(x['files'])==x['runtime_file_count'] and sum(v['bytes']for v in x['files'].values())==x['runtime_bytes']
    for p,row in x['files'].items():
        components(p);assert set(row)=={'bytes','sha256'}
        assert type(row['bytes'])is int and row['bytes']>=0 and re.fullmatch('[0-9a-f]{64}',row['sha256'])
    for p,target in x['symlinks'].items():components(p);assert type(target)is str and target and '\0'not in target
    assert not(set(x['files'])&set(x['symlinks']))
    assert all(p in x['files'] and x['files'][p]['sha256']==h for p,h in x['mapped_libraries'].items())
    assert x['actual_elf']in x['mapped_libraries']
    return x
def components(path):
    assert type(path)is str and path.startswith('/nix/store/') and '\0'not in path
    parts=path.split('/')[1:];assert all(p not in ('','.','..')for p in parts)
    return parts
def open_beneath(rootfd,path,directory=False):
    """Each component is relative to the held target root; absolute symlinks cannot escape to host."""
    parts=components(path);fd=os.dup(rootfd)
    try:
        for i,name in enumerate(parts):
            last=i==len(parts)-1
            child=os.open(name,os.O_RDONLY|os.O_CLOEXEC|os.O_NOFOLLOW|(os.O_DIRECTORY if not last or directory else 0),dir_fd=fd)
            os.close(fd);fd=child
        return fd
    except BaseException:os.close(fd);raise
def file_record(rootfd,path,expected=None):
    fd=open_beneath(rootfd,path)
    try:
        before=os.fstat(fd);assert stat.S_ISREG(before.st_mode)
        with os.fdopen(os.dup(fd),'rb')as f:digest=hashlib.file_digest(f,'sha256').hexdigest()
        after=os.fstat(fd);assert object_id(before)==object_id(after)and before.st_size==after.st_size
        record=dict(sha256=digest,bytes=before.st_size,device=before.st_dev,inode=before.st_ino)
        if expected is not None:assert {k:record[k]for k in ('sha256','bytes')}==expected,path
        return record
    finally:os.close(fd)
def inspect(ident):
    rows=json.loads(subprocess.check_output(['docker','inspect',ident],timeout=10));assert len(rows)==1
    c=rows[0]
    return dict(id=c['Id'],image=c['Image'],name=c['Name'],pid=c['State']['Pid'],
        started_at=c['State']['StartedAt'],running=c['State']['Running'],status=c['State']['Status'],
        cpuset=c['HostConfig']['CpusetCpus'])
def bound(info,expect):
    for k in ('id','image','pid','started_at','cpuset'):assert info[k]==expect[k],k
    assert info['image']==IMAGE and info['name']=='/nssoc-active-drt-cross'
    assert info['running']is True and info['status']=='running'
    assert re.fullmatch('[0-9a-f]{64}',info['id'])and type(info['pid'])is int and info['pid']>1
    return True
def identity_bound(got,expect,inv):
    assert got['identity']==expect['identity']
    ident=got['identity'];assert ident['pid']==expect['pid']
    assert ident['exe_sha256']==ELF and ident['exe_bytes']==inv['actual_elf_bytes']and ident['exe_path']==inv['actual_elf']
    assert bytes.fromhex(ident['cmdline_hex'])==b'\0'.join(os.fsencode(v)for v in (inv['actual_elf'],'-exit','-no_init',expect['route_tcl']))+b'\0'
    assert re.search(rb'(?<![0-9a-f])'+expect['id'].encode()+rb'(?![0-9a-f])',bytes.fromhex(ident['cgroup_hex']))
    return True
def runtime_closure(pid,expected,inv,deadline):
    rootfd=os.open('/proc/'+str(pid)+'/root',os.O_RDONLY|os.O_DIRECTORY|os.O_CLOEXEC)
    try:
        assert object_id(os.fstat(rootfd))==expected['root']
        count=0;total=0
        for p,want in sorted(inv['files'].items()):
            assert time.monotonic()<deadline,'Runtime-closure deadline'
            row=file_record(rootfd,p,want);count+=1;total+=row['bytes']
        for p,target in sorted(inv['symlinks'].items()):
            assert time.monotonic()<deadline,'Runtime-link deadline'
            parent,name=p.rsplit('/',1);fd=open_beneath(rootfd,parent,directory=True)
            try:
                st=os.stat(name,dir_fd=fd,follow_symlinks=False);assert stat.S_ISLNK(st.st_mode)
                assert os.readlink(name,dir_fd=fd)==target,p
            finally:os.close(fd)
        assert count==inv['runtime_file_count']and total==inv['runtime_bytes']
        assert object_id(os.fstat(rootfd))==expected['root']
        return dict(inventory_sha256=INVENTORY_SHA,files=count,bytes=total,symlinks=len(inv['symlinks']),full_declared_closure_verified=True)
    finally:os.close(rootfd)
def mapped_runtime(pid,expected,inv):
    rootfd=os.open('/proc/'+str(pid)+'/root',os.O_RDONLY|os.O_DIRECTORY|os.O_CLOEXEC)
    try:
        assert object_id(os.fstat(rootfd))==expected['root']
        text=(Path('/proc')/str(pid)/'maps').read_text();entries=[];files={}
        for line in text.splitlines():
            f=line.split(None,5);assert len(f)>=5
            lo,hi=(int(v,16)for v in f[0].split('-'));assert lo<hi
            row=dict(start=lo,end=hi,permissions=f[1],offset=int(f[2],16),device=f[3],inode=int(f[4]),path=f[5]if len(f)==6 else None)
            entries.append(row);p=row['path']
            if p and p.startswith('/'):
                assert p in inv['files'],'Mapped file outside exact runtime inventory'
                if p not in files:files[p]=file_record(rootfd,p,inv['files'][p])
                rec=files[p];major,minor=(int(v,16)for v in row['device'].split(':'))
                assert rec['inode']==row['inode']and os.major(rec['device'])==major and os.minor(rec['device'])==minor
        assert inv['actual_elf']in files and all(p in files for p in inv['mapped_libraries'])
        assert object_id(os.fstat(rootfd))==expected['root']
        return dict(raw_maps=text,entries=entries,files=files,inventory_sha256=INVENTORY_SHA)
    finally:os.close(rootfd)
def loaded_native_executable(pid,expected,reported):
    """GDB display names are admitted only through target-root and exact opened object identity."""
    assert pid==expected['pid']and type(reported)is str
    exe=expected['exe_path'];components(exe)
    allowed={exe,'/proc/'+str(pid)+'/exe','/proc/'+str(pid)+'/root'+exe}
    assert reported in allowed,'Unexpected GDB target executable spelling'
    rootfd=os.open('/proc/'+str(pid)+'/root',os.O_RDONLY|os.O_DIRECTORY|os.O_CLOEXEC)
    try:
        assert object_id(os.fstat(rootfd))==expected['root']
        row=file_record(rootfd,exe,dict(sha256=expected['exe_sha256'],bytes=expected['exe_bytes']))
        assert {k:row[k]for k in ('device','inode')}==expected['exe']
        assert os.readlink('/proc/'+str(pid)+'/exe')==exe
        with open('/proc/'+str(pid)+'/exe','rb')as f:
            st=os.fstat(f.fileno());assert object_id(st)==expected['exe']and st.st_size==expected['exe_bytes']
            assert hashlib.file_digest(f,'sha256').hexdigest()==expected['exe_sha256']
        return dict(reported=reported,target_namespace_path=exe,opened_via_held_target_root=True,file=row)
    finally:os.close(rootfd)
def verify_live(expect,inv,tracer=0,require_running=True):
    before=inspect(expect['id']);bound(before,expect)
    got=snapshot(expect['pid'],expect['identity'],tracer=tracer,require_running=require_running)
    identity_bound(got,expect,inv)
    env=(Path('/proc')/str(expect['pid'])/'environ').read_bytes().split(b'\0')
    actual={}
    for row in env:
        if b'='in row:
            k,v=row.split(b'=',1)
            if k.decode()in inv['environment']:
                key=k.decode();assert key not in actual;actual[key]=v.decode()
    assert actual==inv['environment']
    bound(inspect(expect['id']),expect)
    return got

def main():
    import argparse
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    m=json.loads((ROOT/'scripts/mainchip-userstack-native-methods.json').read_text())
    assert m['native_process_restore_authorized']is True and m['native_attachment_authorized']is True
    for p,h in m['protected'].items():assert file_sha(ROOT/p)==h,p
    a=argparse.ArgumentParser();a.add_argument('--verify',action='store_true',required=True)
    a.add_argument('--expect',required=True);a.add_argument('--inventory',required=True);args=a.parse_args()
    expect=json.loads(Path(args.expect).read_text());inv=inventory(Path(args.inventory).read_bytes())
    with ProcessPin(expect['pid'],expect['identity'])as pin:
        pin.verify();r=verify_live(expect,inv);pin.verify()
    print(json.dumps(dict(status='PASS_EXACT_NATIVE_DETACHED_IDENTITY',identity=r['identity'],
        tasks=r['tasks'],target_detached=True,normal_continuation_accepted=False)))
if __name__=='__main__':main()
