#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Source and real temporary-file controls only. Never restores/attaches a chip."""
import ast,copy,hashlib,json,os,subprocess,sys,tempfile,traceback,types
from pathlib import Path
import cloud_mainchip_userstack_diagnostic as controller
import mainchip_userstack_native_binding as bind
import mainchip_latest_userstack_bridge as bridge
import mainchip_latest_native_stack_admission as latest
import mainchip_userstack_native_prerequisite as prerequisite
from mainchip_userstack_identity import object_id
ROOT=Path(__file__).resolve().parents[1]
def check():
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    m=controller.methods();program,edits=controller.adapted_source()
    assert len(edits)==10
    assert program.count("assert len(raw)>len(prefix),'No observable native DRT progress after cross-runner restore'")==1
    assert 'Never replay a live or rejected source'in program
    assert 'diag.admission.rejected_receipt()'in program
    assert '600<=budget<=7200'in program
    assert bridge.latest.RUN==40120760532
    assert bridge.ORIGINAL_REQUIRED==m['original_required_inputs']
    assert bridge.STAGED is None
    frozen=controller.frozen.source_controls()
    qualified=prerequisite.verify()
    # Reviewable source derivations are executable controls; no hidden import-time execution.
    for d in m['derivations']:
        old=(ROOT/d['basis_path']).read_text();text=old
        assert hashlib.sha256(old.encode()).hexdigest()==d['basis_sha256']
        for e in d['edits']:
            assert text.count(e['old'])==e['count'],e['label'];text=text.replace(e['old'],e['new'])
        assert text==(ROOT/d['output_path']).read_text()
        for e in reversed(d['edits']):
            assert text.count(e['new'])==e['reverse_count'],e['label'];text=text.replace(e['new'],e['old'])
        assert text==old
    old=ast.parse((ROOT/'hw/soc/diagnostic-source-basis/userstack/cloud_mainchip_observed_diagnostic.py').read_text())
    new=ast.parse(Path(controller.__file__).read_text())
    funcs=lambda t:{n.name:ast.dump(n)for n in t.body if isinstance(n,ast.FunctionDef)}
    a,b=funcs(old),funcs(new)
    # Reconstruct the historical generated source without importing/executing its native main.
    node=next(n for n in old.body if isinstance(n,ast.FunctionDef)and n.name=='adapted_source')
    class FrozenFile:
        def read_text(self):return (ROOT/'hw/soc/diagnostic-source-basis/userstack/cloud_mainchip_route12_drt_continuation.py').read_text()
    class FrozenRoot:
        def __truediv__(self,unused):return FrozenFile()
    scope=dict(ROOT=FrozenRoot(),FROZEN='frozen',FROZEN_SHA=controller.FROZEN_SHA,hashlib=hashlib,ast=ast)
    exec(compile(ast.Module(body=[node],type_ignores=[]),'<historical-source-only>','exec'),scope)
    historical,_=scope['adapted_source']()
    assert hashlib.sha256(historical.encode()).hexdigest()==latest.CONTROLLER
    assert bridge.descriptor()['generated_controller_sha256']==latest.CONTROLLER
    for name in ('current_inputs','recheck_inputs','verify_no_progress_site','run_inner_and_verify'):
        assert a[name]==b[name],name
    basis=(ROOT/'hw/soc/diagnostic-source-basis/userstack/mainchip_rejected_capsule_admission.py').read_text()
    assert funcs(ast.parse(basis))['validate_current_rows']==funcs(ast.parse(Path(bridge.__file__).read_text()))['validate_current_rows']
    failures=[]
    def reject(name,fn):
        try:fn()
        except(AssertionError,KeyError,TypeError,ValueError,OSError,subprocess.CalledProcessError):failures.append(name)
        else:raise AssertionError('Accepted fault '+name)
    expect=dict(id='a'*64,pid=99,started_at='fixed',image=bind.IMAGE,cpuset='0,1',
        route_tcl='/exact/work/route.tcl')
    info=dict(**expect,name='/nssoc-active-drt-cross',running=True,status='running');info.pop('route_tcl')
    bind.bound(info,expect)
    for k,v in [('id','b'*64),('pid',100),('started_at','other'),('image','sha256:'+'0'*64),
                ('cpuset','0'),('name','/other'),('running',False),('status','exited')]:
        q=copy.deepcopy(info);q[k]=v;reject('container-'+k,lambda:bind.bound(q,expect))
    inv=dict(actual_elf='/nix/store/test/openroad',actual_elf_bytes=103633024)
    ident=dict(pid=99,exe_path=inv['actual_elf'],exe_sha256=bind.ELF,exe_bytes=103633024,
        cmdline_hex=b'/nix/store/test/openroad\0-exit\0-no_init\0/exact/work/route.tcl\0'.hex(),
        cgroup_hex=('0::/docker/'+expect['id']+'\n').encode().hex())
    expect['identity']=copy.deepcopy(ident);got=dict(identity=ident)
    bind.identity_bound(got,expect,inv)
    for k,v in [('pid',100),('exe_path','/nix/store/other'),('exe_sha256','0'*64),('exe_bytes',103633023),
                ('cmdline_hex',b'other\0'.hex()),('cgroup_hex',b'0::/other\n'.hex())]:
        q=copy.deepcopy(got);q['identity'][k]=v
        # Rebind the fixture expected identity so the semantic gate itself must reject.
        w=copy.deepcopy(expect);w['identity']=copy.deepcopy(q['identity'])
        reject('semantic-'+k,lambda:bind.identity_bound(q,w,inv))
    for label,cg in [('prefix','0'+expect['id']),('suffix',expect['id']+'0')]:
        q=copy.deepcopy(got);q['identity']['cgroup_hex']=('0::/docker/'+cg+'\n').encode().hex()
        w=copy.deepcopy(expect);w['identity']=copy.deepcopy(q['identity'])
        reject('cgroup-'+label,lambda:bind.identity_bound(q,w,inv))
    # Actual descriptor-relative reads prove exact byte/identity checks and symlink confinement.
    with tempfile.TemporaryDirectory(prefix='native-stack-binding-')as td:
        root=Path(td);(root/'nix/store/test').mkdir(parents=True);p=root/'nix/store/test/elf';p.write_bytes(b'actual fixture ELF bytes\0')
        fd=os.open(root,os.O_RDONLY|os.O_DIRECTORY)
        try:
            want=dict(sha256=hashlib.sha256(p.read_bytes()).hexdigest(),bytes=p.stat().st_size)
            record=bind.file_record(fd,'/nix/store/test/elf',want);assert record['inode']==p.stat().st_ino
            for label,bad in [('hash',dict(want,sha256='0'*64)),('size',dict(want,bytes=want['bytes']+1))]:
                reject('opened-file-'+label,lambda:bind.file_record(fd,'/nix/store/test/elf',bad))
            for label,path in [('relative','nix/store/test/elf'),('dot','/nix/store/./test/elf'),
                               ('dotdot','/nix/store/test/../test/elf'),('empty','/nix/store//test/elf'),
                               ('host-path','/etc/passwd'),('nul','/nix/store/test/elf\0')]:
                reject('path-'+label,lambda:bind.open_beneath(fd,path))
            (root/'nix/store/test/link').symlink_to(p)
            reject('final-symlink',lambda:bind.file_record(fd,'/nix/store/test/link',want))
            (root/'nix/store/alias').symlink_to(root/'nix/store/test')
            reject('parent-symlink',lambda:bind.file_record(fd,'/nix/store/alias/elf',want))
            reject('missing-file',lambda:bind.file_record(fd,'/nix/store/test/missing',want))
        finally:os.close(fd)
        rows={'actual':dict(path=str(p),expected_sha256=want['sha256'],actual_sha256=want['sha256'])}
        proof=bridge.validate_current_rows(rows,'before_restore',required={})
        bridge.validate_current_rows(rows,'after_restore',proof,required={})
        q=copy.deepcopy(rows);q['actual']['actual_sha256']='0'*64
        reject('current-input-hash',lambda:bridge.validate_current_rows(q,'after_restore',proof,required={}))
        q=copy.deepcopy(rows);q['other']=q.pop('actual')
        reject('current-input-set',lambda:bridge.validate_current_rows(q,'after_restore',proof,required={}))
        reject('missing-current-input',lambda:bridge.validate_current_rows(rows,'before_restore',required={'missing':'0'*64}))
    # Wrong capsule and invented route progress fail against the exact saved small summary.
    raw=(latest.BASIS/'mainchip-observed-native-result.json').read_bytes();r=latest.source_report(raw)
    for k,v in [('run_id',40095811631),('source_head','0'*40),('native_route_returned',True)]:
        q=copy.deepcopy(r);q[k]=v;reject('latest-'+k,lambda:latest.source_report(json.dumps(q).encode()))
    # Exact same-message errors from a different code/site cannot be admitted.
    fixture="def main():\n    raw=b'';prefix=b''\n    assert len(raw)>len(prefix),"+repr(controller.NO_PROGRESS)+"\n"
    ns={};exec(compile(fixture,str(controller.PROGRAM),'exec'),ns)
    def capture(fn):
        try:fn()
        except AssertionError as e:return e
        raise AssertionError('No expected fixture rejection')
    error=capture(ns['main'])
    report=dict(status='FAIL_OR_ERROR',error=repr(error),native_process_saved=True,native_log=dict(single_entrypoint=True),
        traceback=''.join(traceback.format_exception(type(error),error,error.__traceback__)))
    controller.verify_no_progress_site(error,ns['main'],fixture,report)
    wrong="def main():\n    raise AssertionError("+repr(controller.NO_PROGRESS)+")\n"
    other={};exec(compile(wrong,str(controller.PROGRAM),'exec'),other);bad=capture(other['main'])
    reject('wrong-no-progress-code',lambda:controller.verify_no_progress_site(bad,ns['main'],fixture,report))
    reject('wrong-no-progress-site',lambda:controller.verify_no_progress_site(bad,other['main'],fixture,report))
    q=copy.deepcopy(report);q['native_process_saved']=False
    reject('missing-native-checkpoint',lambda:controller.verify_no_progress_site(error,ns['main'],fixture,q))
    q=copy.deepcopy(report);q['traceback']=q['traceback'].replace('line 3','line 4')
    reject('wrong-traceback-line',lambda:controller.verify_no_progress_site(error,ns['main'],fixture,q))
    saved=(controller.finish_probe,controller.recheck_inputs,controller.CURRENT)
    try:
        events=[];controller.CURRENT={'fixture':True}
        controller.finish_probe=lambda r,out:events.append('finish')
        controller.recheck_inputs=lambda:events.append('after')or {'phase':'after_restore'}
        def explode():raise RuntimeError('preserved-original-error')
        receipt={}
        try:controller.run_inner_and_verify(types.SimpleNamespace(main=explode),receipt,fixture)
        except RuntimeError as e:assert str(e)=='preserved-original-error'
        else:raise AssertionError('Original failure hidden')
        assert events==['finish','after']
    finally:controller.finish_probe,controller.recheck_inputs,controller.CURRENT=saved
    assert len(failures)==37,len(failures)
    assert bridge.STAGED is None
    return dict(status='PASS37_SOURCE_BINDING_CONTROLS_NOT_NATIVE_ATTACH',rejected=failures,
        exact_adapter_edits=edits,frozen_controller_controls=frozen,harmless_fixture=qualified,
        chip_restore_executed=False,chip_attachment_executed=False,normal_continuation_accepted=False)
if __name__=='__main__':print(json.dumps(check(),indent=2))
