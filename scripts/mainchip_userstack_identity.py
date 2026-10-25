#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Process identity/read-only proc records shared by host and trusted GDB reader."""
import hashlib,os,re,select,stat
from pathlib import Path
LIMIT=1024*1024

def digest(data):return hashlib.sha256(data).hexdigest()

def file_sha(path):
    with open(path,'rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

def stat_record(raw):
    text=raw.decode('ascii');end=text.rfind(')')
    assert end>0 and re.fullmatch(r'\d+',text[:text.index(' ')])
    fields=text[end+2:].split();assert len(fields)>=22
    return dict(pid=int(text[:text.index(' ')]),state=fields[0],ppid=int(fields[1]),
        pgrp=int(fields[2]),session=int(fields[3]),utime=int(fields[11]),
        stime=int(fields[12]),starttime=int(fields[19]))

def fd_read(fd,name):
    child=os.open(name,os.O_RDONLY|os.O_CLOEXEC|os.O_NOFOLLOW,dir_fd=fd)
    try:
        raw=os.read(child,LIMIT+1);assert len(raw)<=LIMIT
        return raw
    finally:os.close(child)

def object_id(stat):return dict(device=stat.st_dev,inode=stat.st_ino)

def identity_equal(got,want):
    assert got==want,'Native process identity changed'

def snapshot(pid,expected=None,tracer=None,require_running=False):
    assert type(pid)is int and pid>1
    p=Path('/proc')/str(pid)
    fd=os.open(p,os.O_RDONLY|os.O_DIRECTORY|os.O_CLOEXEC|os.O_NOFOLLOW)
    try:
        before=stat_record(fd_read(fd,'stat'));assert before['pid']==pid
        status=fd_read(fd,'status').decode()
        values=dict(line.split(':',1)for line in status.splitlines()if ':'in line)
        actual_tracer=int(values['TracerPid'].strip())
        exefd=os.open('exe',os.O_RDONLY|os.O_CLOEXEC,dir_fd=fd)
        try:
            est=os.fstat(exefd)
            with os.fdopen(os.dup(exefd),'rb')as stream:esha=hashlib.file_digest(stream,'sha256').hexdigest()
        finally:os.close(exefd)
        rootfd=os.open('root',os.O_RDONLY|os.O_DIRECTORY|os.O_CLOEXEC,dir_fd=fd)
        try:rid=object_id(os.fstat(rootfd))
        finally:os.close(rootfd)
        identity=dict(pid=pid,starttime=before['starttime'],proc_directory=object_id(os.fstat(fd)),
            exe_path=os.readlink('exe',dir_fd=fd),exe=object_id(est),exe_bytes=est.st_size,exe_sha256=esha,
            cmdline_hex=fd_read(fd,'cmdline').hex(),cgroup_hex=fd_read(fd,'cgroup').hex(),
            root=rid,namespaces={n:os.readlink('ns/'+n,dir_fd=fd)for n in ('mnt','pid','user','cgroup')})
        after=stat_record(fd_read(fd,'stat'))
        assert after['pid']==pid and after['starttime']==before['starttime']
        if expected is not None:identity_equal(identity,expected)
        if tracer is not None:assert actual_tracer==tracer,('Unexpected tracer',actual_tracer,tracer)
        if require_running:assert after['state']not in ('T','t','Z','X','x'),'Target stopped/exited'
        tasks=[]
        for entry in sorted((p/'task').iterdir(),key=lambda x:int(x.name)):
            raw=(entry/'stat').read_bytes();assert len(raw)<=LIMIT
            t=stat_record(raw);assert t['pid']==int(entry.name)
            ts=dict(line.split(':',1)for line in (entry/'status').read_text().splitlines()if ':'in line)
            t['tracer_pid']=int(ts['TracerPid'].strip())
            if tracer is not None:assert t['tracer_pid']==tracer,('Thread tracer',t['pid'],t['tracer_pid'])
            if require_running:assert t['state']not in ('T','t','Z','X','x')
            tasks.append(t)
        assert tasks and len({t['pid']for t in tasks})==len(tasks)
        final=stat_record(fd_read(fd,'stat'))
        assert final['pid']==pid and final['starttime']==before['starttime'],'Process changed during task census'
        finalexe=os.open('exe',os.O_RDONLY|os.O_CLOEXEC,dir_fd=fd)
        try:
            fest=os.fstat(finalexe)
            assert object_id(fest)==identity['exe'] and fest.st_size==identity['exe_bytes']
            with os.fdopen(os.dup(finalexe),'rb')as f:assert hashlib.file_digest(f,'sha256').hexdigest()==identity['exe_sha256']
        finally:os.close(finalexe)
        assert os.readlink('exe',dir_fd=fd)==identity['exe_path']
        return dict(identity=identity,process=final,tracer_pid=actual_tracer,tasks=tasks)
    finally:os.close(fd)


def loaded_executable_identity(pid,expected,reported):
    """Validate the loaded object itself; GDB may normalize the /proc display path."""
    assert type(pid)is int and pid==expected['pid']
    assert type(reported)is str and reported and Path(reported).is_absolute()
    proc=Path('/proc')/str(pid)/'exe'
    assert os.readlink(proc)==expected['exe_path']
    resolved=Path(reported).resolve(strict=True)
    assert str(resolved)==expected['exe_path'],'Loaded executable resolves to a different object path'
    records={}
    for label,path in (('gdb_reported',reported),('proc_executable',proc)):
        with open(path,'rb')as f:
            before=os.fstat(f.fileno())
            assert stat.S_ISREG(before.st_mode)
            assert object_id(before)==expected['exe'],'Loaded executable device/inode changed'
            assert before.st_size==expected['exe_bytes'],'Loaded executable size changed'
            digest=hashlib.file_digest(f,'sha256').hexdigest()
            after=os.fstat(f.fileno())
            assert object_id(after)==object_id(before)and after.st_size==before.st_size
            assert digest==expected['exe_sha256'],'Loaded executable bytes changed'
            records[label]=dict(device=before.st_dev,inode=before.st_ino,bytes=before.st_size,sha256=digest)
    assert records['gdb_reported']==records['proc_executable']
    assert os.readlink(proc)==expected['exe_path']
    return dict(reported=reported,resolved=str(resolved),proc_path=str(proc),files=records)

def check_frames(report,observed):
    assert report['identity']==observed['identity']
    expected={x['pid']:x['starttime']for x in observed['tasks']}
    threads=report['threads']
    assert len(threads)==len(expected)<=64
    assert {x['host_tid']:x['native_starttime']for x in threads}==expected
    for t in threads:
        assert type(t['frames'])is list and 1<=len(t['frames'])<=16
        assert [f['level']for f in t['frames']]==list(range(len(t['frames'])))
        assert all(type(f['pc'])is int and f['pc']>=0 for f in t['frames'])
        assert type(t['truncated'])is bool
    return True

def module_inventory(pid):
    root=Path('/proc')/str(pid)
    text=(root/'maps').read_text();entries=[];files={}
    for line in text.splitlines():
        parts=line.split(None,5);assert len(parts)>=5
        lo,hi=[int(x,16)for x in parts[0].split('-')]
        rec=dict(start=lo,end=hi,permissions=parts[1],offset=int(parts[2],16),
                 device=parts[3],inode=int(parts[4]),path=parts[5]if len(parts)==6 else None)
        assert lo<hi;entries.append(rec)
        path=rec['path']
        if path and path.startswith('/') and 'x'in rec['permissions']:
            assert not path.endswith(' (deleted)') and '..'not in Path(path).parts
            if path not in files:
                actual=root/'root'/path.lstrip('/')
                with actual.open('rb')as f:
                    st=os.fstat(f.fileno())
                    assert st.st_ino==rec['inode']
                    major,minor=[int(x,16)for x in rec['device'].split(':')]
                    assert os.major(st.st_dev)==major and os.minor(st.st_dev)==minor
                    files[path]=dict(sha256=hashlib.file_digest(f,'sha256').hexdigest(),
                        bytes=st.st_size,device=st.st_dev,inode=st.st_ino)
    return dict(raw_maps=text,entries=entries,files=files)

def frame_binding(pc,modules):
    hits=[m for m in modules['entries']if m['start']<=pc<m['end']]
    assert len(hits)==1 and 'x'in hits[0]['permissions']
    m=hits[0];p=m['path']
    if p and p.startswith('/'):
        f=modules['files'][p]
        return dict(native_pc=pc,module_path=p,file_offset=m['offset']+pc-m['start'],file=f,
                    file_backed=True)
    return dict(native_pc=pc,module_path=p,file_offset=None,file=None,file_backed=False)

class ProcessPin:
    """Hold native proc directory and pidfd; numeric ptrace attach still revalidates identity."""
    def __init__(self,pid,expected):
        self.pid=pid;self.expected=expected;self.directory=None;self.pidfd=None
        try:
            self.directory=os.open('/proc/'+str(pid),os.O_RDONLY|os.O_DIRECTORY|os.O_CLOEXEC|os.O_NOFOLLOW)
            self.pidfd=os.pidfd_open(pid,0)
            self.verify()
        except BaseException:self.close();raise
    def verify(self,tracer=0,require_running=True):
        poll=select.poll();poll.register(self.pidfd,select.POLLIN|select.POLLHUP|select.POLLERR)
        assert poll.poll(0)==[],'Pinned process exited'
        assert object_id(os.fstat(self.directory))==self.expected['proc_directory']
        current=stat_record(fd_read(self.directory,'stat'))
        assert current['pid']==self.pid and current['starttime']==self.expected['starttime']
        result=snapshot(self.pid,self.expected,tracer=tracer,require_running=require_running)
        assert poll.poll(0)==[],'Pinned process exited during complete task census'
        final=stat_record(fd_read(self.directory,'stat'))
        assert final['pid']==self.pid and final['starttime']==self.expected['starttime']
        return result
    def close(self):
        for name in ('pidfd','directory'):
            fd=getattr(self,name,None)
            if fd is not None:os.close(fd);setattr(self,name,None)
    def __enter__(self):return self
    def __exit__(self,*args):self.close()
