#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Hosted controls for rejected-process diagnostic admission and target binding."""
import ast,copy,json,os,subprocess,sys,tempfile
from pathlib import Path
import cloud_mainchip_observed_diagnostic as controller
import mainchip_bound_native_observer as probe
def check():
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    m=controller.methods()
    text,edits=controller.adapted_source()
    assert len(edits)==10 and 'diag.admission.rejected_receipt()'in text
    assert text.count("assert len(raw)>len(prefix),'No observable native DRT progress after cross-runner restore'")==1
    assert 'Never replay a live or rejected source'in text
    assert 'historical_sources_unchanged_proven=False'in Path(controller.__file__).read_text()
    assert not any(isinstance(n,ast.Attribute)and n.attr=='read_bytes'for n in ast.walk(ast.parse(controller.COPY_PROGRAM)))
    old=controller.frozen.source_controls()
    failures=[]
    def rejected(name,fn):
        try:fn()
        except (AssertionError,KeyError,TypeError,ValueError,subprocess.CalledProcessError):failures.append(name)
        else:raise AssertionError('Accepted injected fault '+name)
    expect=dict(id='a'*64,pid=100,started_at='2026-10-24T00:00:00Z',image='sha256:'+'b'*64,
        cpuset='0,1,2,3',elf_path='/exact/openroad',route_tcl='/exact/work/route.tcl')
    info=dict(id=expect['id'],image=expect['image'],name='/nssoc-active-drt-cross',
        state=dict(Running=True,Status='running',Pid=100,StartedAt=expect['started_at']),cpuset=expect['cpuset'])
    probe.bound(info,expect)
    for label,path,value in [
       ('other-container',['id'],'c'*64),('other-image',['image'],'sha256:'+'d'*64),
       ('other-name',['name'],'/other'),('other-cpuset',['cpuset'],'0,1'),
       ('stopped',['state','Running'],False),('exited-status',['state','Status'],'exited'),
       ('different-pid',['state','Pid'],101),('different-start',['state','StartedAt'],'other')]:
        q=copy.deepcopy(info);target=q
        for key in path[:-1]:target=target[key]
        target[path[-1]]=value;rejected(label,lambda:probe.bound(q,expect))
    sample=dict(status='OBSERVED_IDENTITY_BOUND_PROCESS',derived=dict(identity=dict(pid=100,executable=dict(sha256=probe.ELF))))
    argv=b'/exact/openroad\0-exit\0-no_init\0/exact/work/route.tcl\0'
    cg=b'0::/system.slice/docker-'+expect['id'].encode()+b'.scope\n'
    probe.proc_binding(sample,argv,cg,expect)
    for label,mutate in [
        ('unobserved-process',lambda q:q.__setitem__('status','REJECTED_PROCESS_OBSERVATION')),
        ('reused-pid',lambda q:q['derived']['identity'].__setitem__('pid',101)),
        ('wrong-elf',lambda q:q['derived']['identity']['executable'].__setitem__('sha256','0'*64))]:
        q=copy.deepcopy(sample);mutate(q);rejected(label,lambda:probe.proc_binding(q,argv,cg,expect))
    for label,command,cgroup in [
        ('changed-native-tcl',argv.replace(b'route.tcl',b'other.tcl'),cg),
        ('extra-native-argument',argv+b'-other\0',cg),
        ('unterminated-native-argv',argv[:-1],cg),
        ('wrong-cgroup',argv,b'0::/system.slice/docker-'+b'c'*64+b'.scope\n'),
        ('container-id-prefix-alias',argv,cg.replace(b'docker-',b'docker-0')),
        ('container-id-suffix-alias',argv,cg.replace(b'.scope',b'0.scope'))]:
        rejected(label,lambda:probe.proc_binding(sample,command,cgroup,expect))
    with tempfile.TemporaryDirectory(prefix='copy-controls-')as td:
        root=Path(td);a=root/'a';b=root/'b';a.mkdir();b.mkdir()
        payload=(b'\0\1\2\3'*65536)*9+b'tail'
        (a/'image').write_bytes(payload);(b/'image').write_bytes(payload)
        def compare():return subprocess.run([sys.executable,'-c',controller.COPY_PROGRAM,str(a),str(b)],capture_output=True,text=True,check=True)
        proof=json.loads(compare().stdout);assert proof==dict(files=1,source_and_destination_equal=True,streaming_bytes=1048576)
        (b/'image').write_bytes(payload[:-1]);rejected('truncated-copy',compare)
        (b/'image').write_bytes(payload[:-1]+b'X');rejected('corrupt-final-byte',compare)
        (b/'image').write_bytes(payload);(b/'extra').write_bytes(b'x');rejected('extra-image',compare);(b/'extra').unlink()
        (b/'image').unlink();rejected('missing-image',compare)
        (b/'image').symlink_to(a/'image');rejected('symlink-image',compare)
    assert len(failures)==22,len(failures)
    return dict(status='PASS22_BINDING_STREAMING_CONTROLS_AND_FROZEN20_SOURCE_FAULTS',
        rejected=failures,frozen_normal_source=old,exact_adapter_edits=edits,
        current_process_binding_is_fixture_only=True,actual_native_process_not_run=True,
        normal_continuation_accepted=False,full_phy_accepted=False)
if __name__=='__main__':print(json.dumps(check(),indent=2))
