#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Owned hosted launcher smoke; never creates geometry or runs a simulator."""
import argparse,ast,base64,hashlib,json,os,signal,subprocess,sys,tempfile,time
from pathlib import Path
import cdr_v59_mim_admission as admission
from cloud_cdr_v59_binding_rc import emit
APP_SHA='d6a349ec65be11456e96c4981d35f63ca34d3c85daf79a51e1ccb907bb5d7466'
MARKER='CDR_V59_MIM_INTERPRETER '
OUT=admission.ROOT/'hw/soc/out/cdr-v59-mim-runtime-preflight'
CODE="""import hashlib,json,platform,sys
from pathlib import Path
import pya
assert hasattr(pya,'Layout')
def digest(path):
    h=hashlib.sha256()
    with open(path,'rb')as stream:
        for b in iter(lambda:stream.read(1024*1024),b''):h.update(b)
    return h.hexdigest()
r=dict(schema='cdr-v59-mim-interpreter-v1',executable=sys.executable,
    executable_sha256=digest(sys.executable),version=sys.version,
    version_info=list(sys.version_info[:3]),implementation=sys.implementation.name,
    platform=sys.platform,pya_imported=True,pya_file=pya.__file__,
    pya_file_sha256=digest(pya.__file__),pya_version=getattr(pya,'__version__',None))
print('CDR_V59_MIM_INTERPRETER '+json.dumps(r,sort_keys=True),flush=True)
"""
def digest(path):
    h=hashlib.sha256()
    with Path(path).open('rb')as stream:
        for b in iter(lambda:stream.read(1024*1024),b''):h.update(b)
    return h.hexdigest()
def validate_report(raw):
    lines=raw.decode('utf-8').splitlines()
    rows=[line[len(MARKER):]for line in lines if line.startswith(MARKER)]
    assert len(rows)==1,'Exactly one native interpreter record is required'
    r=json.loads(rows[0])
    assert r['schema']=='cdr-v59-mim-interpreter-v1'
    assert Path(r['executable']).is_absolute()and Path(r['pya_file']).is_absolute()
    assert r['implementation']=='cpython'and r['platform']=='linux'
    assert len(r['version_info'])==3 and all(type(x)is int and x>=0 for x in r['version_info'])
    assert r['version_info'][0]==3 and r['pya_imported']is True
    for key in ('executable_sha256','pya_file_sha256'):
        assert len(r[key])==64 and all(c in '0123456789abcdef'for c in r[key])
    return r
SUPERVISOR='docs/evidence/cdr-v59-mim-qualified-process-supervisor-20261025.py'
SUPERVISOR_SHA='e326e548ebe11550d18a049d639bdf063f03602d4ba08299b00a5747d3281c0b'
SUPERVISOR_NAMES=('SupervisionFailure','safe_read','group_members','live_members','stop_process')
def supervisor():
    path=admission.ROOT/SUPERVISOR;raw=path.read_bytes()
    assert hashlib.sha256(raw).hexdigest()==SUPERVISOR_SHA
    tree=ast.parse(raw.decode())
    nodes=[n for n in tree.body if isinstance(n,(ast.FunctionDef,ast.ClassDef))and n.name in SUPERVISOR_NAMES]
    assert [n.name for n in nodes]==list(SUPERVISOR_NAMES)
    scope=dict(Path=Path,os=os,signal=signal,time=time,json=json)
    exec(compile(ast.Module(body=nodes,type_ignores=[]),str(path),'exec'),scope)
    return scope
def probe(app,expected_sha,out,timeout=60,env=None):
    app=Path(app);out=Path(out);out.mkdir(parents=True,exist_ok=False)
    stdout=out/'stdout.bin';stderr=out/'stderr.bin'
    stdout.touch();stderr.touch()
    r=dict(status='FAIL_RUNTIME_LAUNCH',accepted=False,launcher_started=False,
      timed_out=False,command=[str(app),'python','-c',CODE],
      expected_appimage_sha256=expected_sha,simulation_executed=False,
      geometry_executed=False,cleanup_helper_sha256=SUPERVISOR_SHA)
    process=None
    try:
        owned=supervisor()
        assert app.is_absolute()and app.is_file()and not app.is_symlink()
        r['appimage_before_sha256']=digest(app)
        assert r['appimage_before_sha256']==expected_sha,'Pinned launcher hash mismatch'
        with stdout.open('wb')as outlog,stderr.open('wb')as errlog:
            process=subprocess.Popen(r['command'],stdout=outlog,stderr=errlog,
                env=env,start_new_session=True)
            r['launcher_started']=True;r['pid']=process.pid
            try:
                try:process.wait(timeout=timeout)
                except subprocess.TimeoutExpired:r['timed_out']=True
            finally:
                if process.poll()is not None:
                    r['live_after_leader_exit']=owned['live_members'](process.pid)
                r['cleanup']=owned['stop_process'](process)
                r['returncode']=process.returncode
        assert not r.get('live_after_leader_exit',[]),'Live descendant after launcher leader exit'
        assert not r['cleanup']['remaining_live'],'Owned group did not terminate'
        r['appimage_after_sha256']=digest(app)
        assert r['appimage_after_sha256']==expected_sha,'Launcher changed during smoke'
        assert not r['timed_out']and r['returncode']==0,('launcher_return',r['returncode'],r['timed_out'])
        assert stdout.stat().st_size<=262144 and stderr.stat().st_size<=262144
        r['interpreter']=validate_report(stdout.read_bytes())
        r.update(status='PASS_PINNED_APPIMAGE_INTERPRETER_AND_PYA_IMPORT',accepted=True)
    except BaseException as error:r['error']=repr(error)
    finally:
        terminal=process is None or ('cleanup'in r and not r['cleanup']['remaining_live'])
        r['terminal_group_verified_before_stream_collection']=terminal
        if not terminal:r.update(status='FAIL_RUNTIME_GROUP_NOT_TERMINAL',accepted=False)
        for name,path in [('stdout',stdout),('stderr',stderr)]:
            entry=dict(bytes=path.stat().st_size,path=path.name,complete=terminal)
            if terminal:
                entry['sha256']=digest(path)
                if path.stat().st_size<=262144:entry['base64']=base64.b64encode(path.read_bytes()).decode()
                else:r.update(status='FAIL_RUNTIME_LOG_BOUND',accepted=False)
            r[name]=entry
        admission.write(out/'result.json',r)
    return r
def controls():
    admission.methods();rejected=[];positives=[]
    with tempfile.TemporaryDirectory()as folder:
        root=Path(folder);stub=root/'stub';stub.mkdir()
        (stub/'pya.py').write_text("__version__='HOSTED_FIXTURE_ONLY'\nclass Layout:pass\n")
        env={**os.environ,'PYTHONPATH':str(stub),'PYTHONDONTWRITEBYTECODE':'1'}
        def launcher(name,body):
            p=root/name;p.write_text('#!/bin/sh\n'+body);p.chmod(0o700);return p
        import shlex
        body='test "$1" = python || exit 97\nshift\nexec '+shlex.quote(sys.executable)+' "$@"\n'
        app=launcher('positive',body)
        good=probe(app,digest(app),root/'positive-out',env=env)
        assert good['accepted']and good['returncode']==0
        assert good['interpreter']['pya_version']=='HOSTED_FIXTURE_ONLY'
        assert good['command']==[str(app),'python','-c',CODE]
        positives.append('actual_interpreter_and_explicit_stub_import')
        def reject(name,p,expected=None,timeout=60,expected_code=None):
            got=probe(p,expected or digest(p),root/(name+'-out'),timeout,env)
            assert not got['accepted']and got['status'].startswith('FAIL'),name
            if expected_code is not None:assert got['returncode']==expected_code,name
            rejected.append(name);return got
        text='/home/runner/work/_temp/librelane.AppImage: cannot write uid_map: Operation not permitted\n'
        failed=launcher('uid-map-exit127',"printf '%s\\n' "+shlex.quote(text.rstrip('\n'))+" >&2\nexit 127\n")
        got=reject('actual_exit127_uid_map',failed,expected_code=127)
        assert base64.b64decode(got['stderr']['base64'])==text.encode()
        reject('wrong_launcher_hash',app,'0'*64)
        missing=launcher('missing-record','exit 0\n')
        reject('zero_exit_without_interpreter_record',missing,expected_code=0)
        malformed=launcher('malformed-record',"printf '%s\\n' 'CDR_V59_MIM_INTERPRETER {invalid}'\n")
        reject('malformed_interpreter_record',malformed,expected_code=0)
        changed=launcher('self-changed','printf "\\n#changed\\n" >> "$0"\n'+body)
        reject('changed_launcher_after_zero_exit',changed,expected_code=0)
        sleeper=launcher('sleeping','sleep 5\n')
        timeout=reject('actual_launcher_timeout',sleeper,timeout=0.05)
        assert timeout['timed_out']and timeout['returncode']<0
        (stub/'pya.py').write_text("raise RuntimeError('EXACT_HOSTED_PYA_IMPORT_FAILURE')\n")
        imported=reject('actual_pya_import_exception',app,expected_code=1)
        assert b'EXACT_HOSTED_PYA_IMPORT_FAILURE'in base64.b64decode(imported['stderr']['base64'])
        (stub/'pya.py').write_text("__version__='HOSTED_FIXTURE_ONLY'\nclass Layout:pass\n")
        invalid=dict(good['interpreter'],platform='invalid')
        wrong=launcher('wrong-platform',"printf '%s\\n' "+shlex.quote(MARKER+json.dumps(invalid))+"\n")
        reject('zero_exit_invalid_runtime_identity',wrong,expected_code=0)
        orphan_code="import os,sys,time\nassert sys.argv[1]=='-c'\nexec(sys.argv[2],{})\nchild=os.fork()\nif child:os._exit(0)\nwhile True:\n os.write(1,b'OWNED_DESCENDANT\\n');time.sleep(.01)\n"
        orphan=launcher('orphan-after-leader','test "$1" = python || exit 97\nshift\nexec '+shlex.quote(sys.executable)+' -c '+shlex.quote(orphan_code)+' "$@"\n')
        ended=reject('actual_leader_exit_with_live_descendant',orphan,expected_code=0)
        assert ended['live_after_leader_exit']and not ended['cleanup']['remaining_live']
        assert ended['terminal_group_verified_before_stream_collection']
        assert validate_report(base64.b64decode(ended['stdout']['base64']))['pya_imported']
        binary=launcher('binary-stderr',"printf '\\377\\000' >&2\n"+body)
        exact=probe(binary,digest(binary),root/'binary-out',env=env)
        assert exact['accepted']and base64.b64decode(exact['stderr']['base64'])==bytes([255,0])
        positives.append('exact_nonUTF8_stderr_preserved')
    assert len(rejected)==9 and len(positives)==2
    return dict(status='PASS_HOSTED_LAUNCHER_TRANSPORT_9_FAULTS_2_POSITIVES',
      rejected=rejected,positive=positives,actual_subprocesses=True,
      pya_module_in_controls='EXPLICIT_SYNTHETIC_STUB_NOT_NATIVE_PYA',
      actual_appimage_executed=False,native_geometry_executed=False)
def main():
    p=argparse.ArgumentParser();p.add_argument('--controls',action='store_true');args=p.parse_args()
    if args.controls:print(json.dumps(controls(),indent=2));return
    admission.authorize()
    r=probe(Path(os.environ['CLOUD_APPIMAGE']),APP_SHA,OUT)
    emit(OUT/'result.json','CDR_V59_MIM_RUNTIME_PREFLIGHT')
    assert r['accepted'],r
if __name__=='__main__':main()
