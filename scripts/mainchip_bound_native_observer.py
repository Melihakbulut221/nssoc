#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Bind read-only proc observations to the exact restored OpenROAD container."""
import argparse,base64,hashlib,json,os,re,subprocess,time,traceback
from pathlib import Path
from mainchip_proc_observer import ProcObserver
ELF='25a5e9ba1cbb76b820af97cfc8d87b7a2d1bc1203091d83ee4eee859c2e9a04b'
FLAGS=dict(route_progress_accepted=False,continuation_accepted=False,
    process_liveness_accepted=False,routing_complete=False,target_modified=False)
def digest(b):return hashlib.sha256(b).hexdigest()
def write(path,obj):path.write_text(json.dumps(obj,indent=2)+'\n')
def inspect(ident):
    raw=subprocess.check_output(['docker','inspect',ident])
    rows=json.loads(raw);assert len(rows)==1
    c=rows[0]
    return dict(id=c['Id'],image=c['Image'],name=c['Name'],state={k:c['State'][k]
        for k in ('Running','Pid','StartedAt','Status')},cpuset=c['HostConfig']['CpusetCpus'])
def bound(info,expect):
    assert info['id']==expect['id'] and info['image']==expect['image']
    assert info['name']=='/nssoc-active-drt-cross' and info['cpuset']==expect['cpuset']
    assert info['state']['Running']is True and info['state']['Status']=='running'
    assert info['state']['Pid']==expect['pid'] and info['state']['StartedAt']==expect['started_at']
def read_at(observer,name):
    fd=os.open(name,os.O_RDONLY|os.O_CLOEXEC|os.O_NOFOLLOW,dir_fd=observer.directory)
    try:
        b=os.read(fd,1024*1024+1);assert len(b)<=1024*1024
        return b
    finally:os.close(fd)
def proc_binding(sample,cmdline,cgroup,expect):
    assert sample['status']=='OBSERVED_IDENTITY_BOUND_PROCESS'
    ident=sample['derived']['identity'];assert ident['pid']==expect['pid']
    assert ident['executable']['sha256']==ELF
    args=cmdline.split(b'\0')
    assert args[-1]==b'' and args[:-1]==[os.fsencode(expect['elf_path']),b'-exit',b'-no_init',os.fsencode(expect['route_tcl'])]
    # Require the complete container identifier as a cgroup path component/token.
    assert re.search(rb'(?<![0-9a-f])'+expect['id'].encode()+rb'(?![0-9a-f])',cgroup)
    return dict(cmdline_base64=base64.b64encode(cmdline).decode(),cmdline_sha256=digest(cmdline),
        cgroup_base64=base64.b64encode(cgroup).decode(),cgroup_sha256=digest(cgroup))
def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    a=argparse.ArgumentParser();a.add_argument('--expect',required=True);a.add_argument('--out',required=True)
    args=a.parse_args();expect=json.loads(Path(args.expect).read_text());out=Path(args.out)
    assert out.is_dir() and re.fullmatch('[0-9a-f]{64}',expect['id'])
    assert type(expect['pid'])is int and expect['pid']>0
    result=dict(status='RUNNING',expected=expect,observations=0,**FLAGS)
    samples=out/'samples.jsonl';ready=out/'ready.json';stop=out/'stop'
    try:
        with ProcObserver(expect['pid']) as observer,samples.open('x') as stream:
            first_identity=None
            for index in range(45):
                if index:
                    deadline=time.monotonic()+15
                    while time.monotonic()<deadline and not stop.exists():time.sleep(.25)
                    if stop.exists():break
                record=dict(index=index,monotonic_begin_ns=time.monotonic_ns())
                try:
                    record['container_before']=inspect(expect['id']);bound(record['container_before'],expect)
                    cmd=read_at(observer,'cmdline');cg=read_at(observer,'cgroup')
                    sample=observer.snapshot(expected_identity=first_identity)
                    record['sample']=sample
                    record['binding']=proc_binding(sample,cmd,cg,expect)
                    record['container_after']=inspect(expect['id']);bound(record['container_after'],expect)
                    assert read_at(observer,'cmdline')==cmd and read_at(observer,'cgroup')==cg
                    if first_identity is None:first_identity=sample['derived']['identity']
                    record['status']='BOUND_READ_ONLY_SAMPLE'
                except BaseException as error:
                    record.update(status='REJECTED_BOUND_SAMPLE',error=repr(error),traceback=traceback.format_exc())
                record['monotonic_end_ns']=time.monotonic_ns()
                stream.write(json.dumps(record)+'\n');stream.flush();os.fsync(stream.fileno())
                result['observations']+=1
                if not ready.exists():write(ready,record)
                if record['status']!='BOUND_READ_ONLY_SAMPLE':raise AssertionError('Bound process observation rejected')
            result['status']='COMPLETED_BOUND_READ_ONLY_OBSERVATIONS'
            result['stop_requested']=stop.exists()
            result['identity']=first_identity
    except BaseException as error:
        result.update(status='REJECTED_BOUND_READ_ONLY_OBSERVATIONS',error=repr(error),traceback=traceback.format_exc())
        if not ready.exists():write(ready,result)
        raise
    finally:
        if samples.exists():result['samples_sha256']=digest(samples.read_bytes())
        write(out/'result.json',result)
if __name__=='__main__':main()
