#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Hosted controls for rejected-process diagnostic admission and target binding."""
import ast,copy,json,os,subprocess,sys,tempfile,traceback,types
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
    import check_mainchip_rejected_capsule_admission as admission_check
    admission_controls=admission_check.controls(controller.admission.rejected_receipt())
    failures=[]
    def rejected(name,fn):
        try:fn()
        except (AssertionError,KeyError,TypeError,ValueError,subprocess.CalledProcessError):failures.append(name)
        else:raise AssertionError('Accepted injected fault '+name)
    expect=dict(id='a'*64,pid=100,started_at='2026-10-24T00:00:00Z',image='sha256:'+'b'*64,
        cpuset='0,1',elf_path='/exact/openroad',route_tcl='/exact/work/route.tcl')
    info=dict(id=expect['id'],image=expect['image'],name='/nssoc-active-drt-cross',
        state=dict(Running=True,Status='running',Pid=100,StartedAt=expect['started_at']),cpuset=expect['cpuset'])
    probe.bound(info,expect)
    for label,path,value in [
       ('other-container',['id'],'c'*64),('other-image',['image'],'sha256:'+'d'*64),
       ('other-name',['name'],'/other'),('other-cpuset',['cpuset'],'0,1,2,3'),
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
    # Same-message wrong-site/wrong-code errors must not be relabelled as the
    # original no-log rejection. This tiny function never invokes native DRT.
    fixture="def main():\n    raw=b'';prefix=b''\n    assert len(raw)>len(prefix),"+repr(controller.NO_PROGRESS)+"\n"
    ns={};exec(compile(fixture,str(controller.PROGRAM),'exec'),ns)
    def capture(fn):
        try:fn()
        except AssertionError as error:return error
        raise AssertionError('Fixture failed to raise')
    error=capture(ns['main'])
    report=dict(status='FAIL_OR_ERROR',error=repr(error),native_process_saved=True,
        native_log=dict(single_entrypoint=True),
        traceback=''.join(traceback.format_exception(type(error),error,error.__traceback__)))
    controller.verify_no_progress_site(error,ns['main'],fixture,report)
    wrong="def main():\n    raw=b'';prefix=b''\n    assert True,"+repr(controller.NO_PROGRESS)+"\n    raise AssertionError("+repr(controller.NO_PROGRESS)+")\n"
    other={};exec(compile(wrong,str(controller.PROGRAM),'exec'),other)
    wrong_error=capture(other['main'])
    rejected('same-message-wrong-site',lambda:controller.verify_no_progress_site(wrong_error,other['main'],fixture,report))
    rejected('same-message-wrong-code',lambda:controller.verify_no_progress_site(wrong_error,ns['main'],fixture,report))
    q=copy.deepcopy(report);q['traceback']=q['traceback'].replace('line 3','line 4')
    rejected('wrong-reported-error-site',lambda:controller.verify_no_progress_site(error,ns['main'],fixture,q))
    q=copy.deepcopy(report);q['native_process_saved']=False
    rejected('missing-saved-process',lambda:controller.verify_no_progress_site(error,ns['main'],fixture,q))
    rejected('different-assertion-message',lambda:controller.verify_no_progress_site(AssertionError('other'),ns['main'],fixture,report))
    # After-input verification runs on unexpected errors as well as success.
    saved=(controller.finish_probe,controller.recheck_inputs,controller.CURRENT)
    try:
        events=[];controller.CURRENT={'fixture':True}
        controller.finish_probe=lambda r,out:events.append('finish')
        controller.recheck_inputs=lambda:events.append('after')or {'phase':'after_restore'}
        def explode():raise RuntimeError('original-native-fixture')
        receipt={}
        try:controller.run_inner_and_verify(types.SimpleNamespace(main=explode),receipt,fixture)
        except RuntimeError as e:assert str(e)=='original-native-fixture'
        else:raise AssertionError('Lost original error')
        assert events==['finish','after'] and receipt['current_inputs_after']['phase']=='after_restore'
        events.clear()
        def failed_after():events.append('after');raise ValueError('changed-input-fixture')
        controller.recheck_inputs=failed_after;receipt={}
        try:controller.run_inner_and_verify(types.SimpleNamespace(main=explode),receipt,fixture)
        except RuntimeError as e:assert str(e)=='original-native-fixture'
        else:raise AssertionError('After failure hid original native error')
        assert events==['finish','after'] and receipt['after_errors'][0]['stage']=='current-inputs-after'
    finally:
        controller.finish_probe,controller.recheck_inputs,controller.CURRENT=saved
    with tempfile.TemporaryDirectory(prefix='atomic-observer-')as td:
        target=Path(td)/'ready.json'
        probe.write(target,dict(status='first'));assert json.loads(target.read_text())=={'status':'first'}
        probe.write(target,dict(status='second'));assert json.loads(target.read_text())=={'status':'second'}
        assert sorted(p.name for p in Path(td).iterdir())==['ready.json']
    assert probe.raw_binding(argv,cg)==probe.proc_binding(sample,argv,cg,expect)
    assert len(failures)==27,len(failures)
    return dict(status='PASS27_BINDING_STREAMING_EXCEPTION_CONTROLS_WITH71_ADMISSION_AND_FROZEN20_FAULTS',
        rejected=failures,admission=admission_controls,frozen_normal_source=old,exact_adapter_edits=edits,
        atomic_publication_checked=True,after_error_paths_checked=True,
        current_process_binding_is_fixture_only=True,actual_native_process_not_run=True,
        normal_continuation_accepted=False,full_phy_accepted=False)
if __name__=='__main__':print(json.dumps(check(),indent=2))
