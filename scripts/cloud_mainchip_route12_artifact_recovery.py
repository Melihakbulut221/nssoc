#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Recover exact failed main-chip evidence. Never import/start/restore the router."""
import argparse, ast, copy, hashlib, io, json, os, re, shutil, stat, subprocess, tempfile, traceback, zipfile
from pathlib import Path,PurePosixPath
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'cloud-mainchip-route12-artifact-recovery'
REPO='repos/Melihakbulut221/nssoc/'
RUN=40095811631
HEAD='4d85722e05fbda8440c6577d7d7baa18a642485b'
JOB=120877858005
ARTIFACT=12564886005
ZIP_BYTES=1560640815
ZIP_SHA='6231b9523ba15bcabac5e65b166648523a742c146321c7806ff97d01e6272e56'
LOG_SHA='95782e475057e65b6d3ef165d7d26c36f269fe04981cb984e0279b1c3607ed19'
CONTROLLER='scripts/cloud_mainchip_route12_drt_continuation.py'
CONTROLLER_SHA='08b91df1a93d28c4acda1dbeae3b45e53af8393664ceaf71038808bdb0707eee'
FAILURE='No observable native DRT progress after cross-runner restore'
GROUP='mainchip-route12-artifact-recovery'
def digest(b):return hashlib.sha256(b).hexdigest()
def file_sha(p):
    h=hashlib.sha256()
    with p.open('rb')as f:
        for b in iter(lambda:f.read(1048576),b''):h.update(b)
    return h.hexdigest()
def write_json(p,d):p.write_text(json.dumps(d,indent=2)+'\n')
def api(path):return json.loads(subprocess.check_output(['gh','api',REPO+path]))
def methods():
    m=json.loads((ROOT/'scripts/mainchip-route12-artifact-recovery-methods.json').read_text())
    for p,h in m['protected'].items():assert file_sha(ROOT/p)==h,p
    assert m['native_execution_allowed']is False
    return m
def identity(run,job,a):
    assert run['id']==RUN and run['head_sha']==HEAD and run['head_branch']=='codex/complete-open-work'
    assert run['run_attempt']==1 and run['status']=='completed'and run['conclusion']=='failure'
    assert run['event']=='workflow_dispatch'
    assert run['path']=='.github/workflows/mainchip-route12-drt-continuation-cloud.yml'
    assert job['id']==JOB and job['run_id']==RUN and job['run_attempt']==1
    assert job['name']=='continuation'and job['head_sha']==HEAD
    assert job['status']=='completed'and job['conclusion']=='failure'
    assert a['id']==ARTIFACT and a['name']=='mainchip-route12-drt-cross'and a['expired']is False
    assert a['size_in_bytes']==ZIP_BYTES and a['digest']=='sha256:'+ZIP_SHA
    assert a['workflow_run']['id']==RUN and a['workflow_run']['head_sha']==HEAD
    assert a['workflow_run']['head_branch']=='codex/complete-open-work'
def source_evidence():
    r=api('actions/runs/'+str(RUN));j=api('actions/jobs/'+str(JOB));a=api('actions/artifacts/'+str(ARTIFACT))
    identity(r,j,a)
    log=subprocess.check_output(['gh','api',REPO+'actions/jobs/'+str(JOB)+'/logs'])
    assert len(log)==130528 and digest(log)==LOG_SHA
    assert b'line 352, in main'in log and ('AssertionError: '+FAILURE).encode()in log
    assert b'HTTP 403: Resource not accessible by integration'in log
    assert b'With the provided path, there will be 65 files uploaded'in log
    return r,j,a,log
def consume(inp,target,size,sha):
    h=hashlib.sha256();n=0
    with target.open('xb')as out:
        for b in iter(lambda:inp.read(1048576),b''):
            n+=len(b);assert n<=size,'Archive overrun'
            h.update(b);out.write(b)
    assert n==size and h.hexdigest()==sha,'Truncated or corrupt archive'
    assert target.stat().st_size==size and file_sha(target)==sha
    return dict(bytes=n,sha256=h.hexdigest(),complete_stream_verified=True)
def download(target):
    p=subprocess.Popen(['gh','api',REPO+'actions/artifacts/'+str(ARTIFACT)+'/zip'],stdout=subprocess.PIPE)
    try:proof=consume(p.stdout,target,ZIP_BYTES,ZIP_SHA)
    except BaseException:
        p.stdout.close()
        if p.poll()is None:p.terminate()
        p.wait();raise
    else:
        p.stdout.close();assert p.wait()==0,'Artifact download command failed'
    return proof
def index(z,count):
    files={};dirs=set()
    for i in z.infolist():
        n=i.filename
        assert n and '\\'not in n and ':'not in n and all(ord(c)>=32 and ord(c)!=127 for c in n)
        p=PurePosixPath(n);assert not p.is_absolute()and '..'not in p.parts
        canonical=str(p)
        assert canonical not in ('','.','/')and n==canonical+('/'if i.is_dir()else'')
        assert not(i.flag_bits&1),'Encrypted archive member'
        kind=stat.S_IFMT(i.external_attr>>16)
        if i.is_dir():
            assert kind in(0,stat.S_IFDIR)and canonical not in dirs
            dirs.add(canonical);continue
        assert kind in(0,stat.S_IFREG),'Archive links or special files are forbidden'
        assert n not in files and i.compress_type in(zipfile.ZIP_STORED,zipfile.ZIP_DEFLATED)
        assert 0<=i.file_size<=128*1024**3
        files[n]=i
    assert len(files)==count and not(set(files)&dirs)
    assert sum(i.file_size for i in files.values())<=128*1024**3
    for name in set(files)|dirs:
        assert not any(str(p)in files for p in PurePosixPath(name).parents if str(p)!='.')
    return files
def scan(z,files,out=None):
    inventory={};small={}
    if out is not None:out.mkdir()
    for number,(name,i)in enumerate(sorted(files.items())):
        target=None
        if out is not None and i.file_size<=8*1024**2 and PurePosixPath(name).suffix in('.json','.log','.tcl','.txt'):
            alias='original-evidence-'+str(number).zfill(3)+'-'+PurePosixPath(name).name
            target=out/alias
        h=hashlib.sha256();size=0;dest=target.open('xb')if target else None
        try:
            # Reading through EOF also enforces each ZIP CRC; no native file executes.
            with z.open(i,'r')as inp:
                for b in iter(lambda:inp.read(1048576),b''):
                    size+=len(b);assert size<=i.file_size
                    h.update(b)
                    if dest:dest.write(b)
        finally:
            if dest:dest.close()
        assert size==i.file_size
        row=dict(bytes=size,sha256=h.hexdigest(),crc32=i.CRC,compressed_bytes=i.compress_size)
        if target:
            assert target.stat().st_size==size and file_sha(target)==h.hexdigest()
            row['small_evidence_asset']=target.name;small[name]=target
        inventory[name]=row
    return inventory,small
def inventory_valid(report,inventory):
    expected=report['outputs']
    assert isinstance(expected,dict)and len(inventory)==65
    # The workflow copies criu-build.log only after the controller closes result.outputs.
    assert set(inventory)==set(expected)|{'result.json','criu-build.log'}
    assert 'result.json'not in expected and 'criu-build.log'not in expected
    for name,sha in expected.items():
        assert re.fullmatch('[0-9a-f]{64}',sha)
        assert inventory[name]['sha256']==sha,('Changed original recorded file',name)
def failure_valid(r):
    assert r['status']=='FAIL_OR_ERROR'and r['source_head']==HEAD and r['run_id']==RUN
    assert r['stage']=='cross'and r['job']=='continuation'
    assert r['error']=="AssertionError('"+FAILURE+"')"
    assert 'line 352, in main'in r['traceback']and FAILURE in r['traceback']
    assert r['route_complete']is False and r['final_timing_complete']is False and r['full_phy_accepted']is False
    assert r['controller_sha256']==CONTROLLER_SHA
    assert r['restored_native_process']is True and r['native_process_saved']is True
    assert r.get('active_drt_cross_runner_progress_proven',False)is False
    assert r.get('sources_unchanged',False)is False
    assert r['checkpointed_elf_sha256']=='25a5e9ba1cbb76b820af97cfc8d87b7a2d1bc1203091d83ee4eee859c2e9a04b'
def diagnosis(r,inventory,small):
    failure_valid(r);inventory_valid(r,inventory)
    source=(ROOT/CONTROLLER).read_text();assert digest(source.encode())==CONTROLLER_SHA
    node=next(n for n in ast.parse(source).body if isinstance(n,ast.FunctionDef)and n.name=='log_proof')
    fn=ast.get_source_segment(source,node)
    namespace=dict(re=re,digest=digest)
    exec(compile(fn,'<frozen-native-log-proof-only>','exec'),namespace)
    raw=small['work/native.log'].read_bytes();boots=small['work/boots.log'].read_bytes()
    proof=namespace['log_proof'](raw,boots)
    assert proof==r['native_log']
    old_hash=r['restored_work_prefixes_verified']['work/native.log']
    assert digest(raw)==old_hash,'Expected unchanged restored native log'
    assert proof['optimization_iterations'][-1]=='42'
    assert proof['progress'][-1]==dict(percent=50,violations=3313)
    assert proof['single_entrypoint']and len(r['controls'])==4 and all(x['rejected']for x in r['controls'])
    images=r['checkpoint_images'];assert images
    actual={n[len('checkpoints/state/'):]:v['sha256']for n,v in inventory.items()if n.startswith('checkpoints/state/')}
    assert actual==images
    for command in r['commands']:
        assert inventory[command['label']+'.log']['sha256']==command['log_sha256']
    return dict(status='OBSERVED_EXACT_SAVED_PROCESS_AND_UNCHANGED_NATIVE_LOG_NOT_A_VALID_CONTINUATION',
        original_error=r['error'],original_status=r['status'],
        original_result_sha256=inventory['result.json']['sha256'],
        all_65_members_crc_and_sha256_verified=True,all_original_recorded_member_hashes_verified=True,
        original_recorded_files=len(r['outputs']),workflow_added_build_log_sha256=inventory['criu-build.log']['sha256'],
        original_log_proof=proof,frozen_log_proof_source_sha256=digest(fn.encode()),
        restored_prefix_sha256=old_hash,unchanged_full_native_log=True,
        segment_elapsed_s=r['segment_elapsed_s'],recorded_checkpoint_images=images,
        recorded_native_process_saved=True,checkpoint_image_hashes_reproduced=True,
        saved_process_validated=False,continuation_accepted=False,native_process_restored=False,
        route_complete=False,final_timing_complete=False,full_phy_accepted=False,
        scope='Exact original failure and all65 files recovered only. Process-image existence/hashes do not establish liveness or a valid next checkpoint.')
def controls(actual):
    run,job,artifact,_=actual;identity(run,job,artifact);bad=[]
    def reject(name,fn):
        try:fn()
        except(AssertionError,KeyError,ValueError,zipfile.BadZipFile,EOFError):bad.append(name)
        else:raise AssertionError('Accepted recovery fault '+name)
    for label,which,key,value in [
        ('source-head','run','head_sha','0'*40),('source-run','run','id',1),
        ('live-source','run','status','in_progress'),('accepted-source','run','conclusion','success'),
        ('job-identity','job','id',1),('job-head','job','head_sha','0'*40),
        ('artifact-id','artifact','id',1),('artifact-size','artifact','size_in_bytes',1),
        ('artifact-digest','artifact','digest','sha256:'+'0'*64),('expired-artifact','artifact','expired',True),
        ('artifact-name','artifact','name','other')]:
        r,j,a=copy.deepcopy((run,job,artifact));{'run':r,'job':j,'artifact':a}[which][key]=value
        reject(label,lambda:identity(r,j,a))
    with tempfile.TemporaryDirectory(prefix='artifact-recovery-controls-')as td:
        d=Path(td);payload=b'actual\x00opaque\xffbytes'
        consume(io.BytesIO(payload),d/'good',len(payload),digest(payload))
        for label,b in [('truncated-stream',payload[:-1]),('overlong-stream',payload+b'x'),('corrupt-stream',b'x'+payload[1:])]:
            reject(label,lambda:consume(io.BytesIO(b),d/label,len(payload),digest(payload)))
        def zip_bytes(entries):
            data=io.BytesIO()
            with zipfile.ZipFile(data,'w',compression=zipfile.ZIP_STORED)as z:
                for name,body,kind in entries:
                    i=zipfile.ZipInfo(name);i.create_system=3;i.external_attr=(kind|0o600)<<16
                    z.writestr(i,body)
            return data.getvalue()
        entries=[('result.json',b'{}',stat.S_IFREG),('work/native.log',b'original native log',stat.S_IFREG),
                 ('checkpoints/state/pages-1.img',b'opaque image',stat.S_IFREG)]
        good=zip_bytes(entries)
        with zipfile.ZipFile(io.BytesIO(good))as z:
            inv,_=scan(z,index(z,3));assert len(inv)==3 and inv['work/native.log']['sha256']==digest(entries[1][1])
        for label,mutate in [
            ('absolute-member',lambda e:[('/absolute',e[0][1],stat.S_IFREG)]+e[1:]),
            ('parent-traversal',lambda e:[('../escape',e[0][1],stat.S_IFREG)]+e[1:]),
            ('dot-alias',lambda e:[('./result.json',e[0][1],stat.S_IFREG)]+e[1:]),
            ('windows-separator',lambda e:[('work\\escape',e[0][1],stat.S_IFREG)]+e[1:]),
            ('drive-path',lambda e:[('C:/escape',e[0][1],stat.S_IFREG)]+e[1:]),
            ('duplicate-member',lambda e:[e[0],e[0],e[2]]),
            ('symbolic-link',lambda e:[('result.json',b'/escape',stat.S_IFLNK)]+e[1:]),
            ('special-file',lambda e:[('result.json',b'',stat.S_IFIFO)]+e[1:]),
            ('file-is-parent',lambda e:[('work',b'x',stat.S_IFREG)]+e[1:]),
            ('missing-member',lambda e:e[:-1])]:
            changed=zip_bytes(mutate(entries))
            def check():
                with zipfile.ZipFile(io.BytesIO(changed))as z:scan(z,index(z,3))
            reject(label,check)
        corrupt=good.replace(b'original native log',b'Xriginal native log',1)
        assert corrupt!=good
        def crc_check():
            with zipfile.ZipFile(io.BytesIO(corrupt))as z:scan(z,index(z,3))
        reject('member-crc-corruption',crc_check)
        fixture={'result.json':dict(sha256='0'*64),'criu-build.log':dict(sha256='1'*64)}
        fixture.update({f'file-{i}':dict(sha256=digest(str(i).encode()))for i in range(63)})
        report=dict(outputs={n:r['sha256']for n,r in fixture.items()if n not in('result.json','criu-build.log')})
        inventory_valid(report,fixture)
        q=copy.deepcopy(fixture);q['file-3']['sha256']='0'*64
        reject('recorded-member-hash',lambda:inventory_valid(report,q))
        q=copy.deepcopy(fixture);q['invented']=q.pop('file-2')
        reject('recorded-member-inventory',lambda:inventory_valid(report,q))
    assert len(bad)==27,len(bad)
    return dict(status='PASS_ACTUAL_SOURCE_IDENTITY_TRANSPORT_SAFE_ZIP_AND27_FAULTS',rejected=bad,
        all65_fixture_recorded_hashes_positive=True,opaque_archive_bytes_only=True,native_execution=False)
def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true'and os.environ['GITHUB_RUN_ATTEMPT']=='1'
    p=argparse.ArgumentParser();p.add_argument('--controls',action='store_true');p.add_argument('--recover',action='store_true');a=p.parse_args()
    assert a.controls!=a.recover
    OUT.mkdir(exist_ok=False)
    r=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],run_id=os.environ['GITHUB_RUN_ID'],
        original_run=RUN,original_head=HEAD,original_artifact=ARTIFACT,
        native_execution=False,native_process_restored=False,route_complete=False,
        final_timing_complete=False,full_phy_accepted=False,continuation_accepted=False,saved_process_validated=False)
    try:
        r['method']=methods();actual=source_evidence();r['controls']=controls(actual)
        if a.controls:
            r['status']='PASS_MAINCHIP_ARTIFACT_RECOVERY_SOURCE_CONTROLS_ONLY';return
        assert shutil.disk_usage(OUT).free>=12*1024**3
        with tempfile.TemporaryDirectory(prefix='original-mainchip-artifact-')as td:
            path=Path(td)/'source.zip';r['archive_transport']=download(path)
            archive=OUT/('original-artifact-'+str(ARTIFACT)+'.zip');path.replace(archive)
            with zipfile.ZipFile(archive)as z:
                files=index(z,65)
                assert 'result.json'in files and files['result.json'].file_size<=8*1024**2
                inventory,small=scan(z,files,OUT/'small')
                report=json.loads(small['result.json'].read_text())
                result=diagnosis(report,inventory,small)
            write_json(OUT/'member-inventory.json',inventory)
            write_json(OUT/'diagnosis.json',result)
            write_json(OUT/'source-artifact.json',actual[2])
            (OUT/'original-job.log').write_bytes(actual[3])
            r['original_failure']=dict(status=report['status'],error=report['error'],traceback=report['traceback'],
                original_result_sha256=inventory['result.json']['sha256'],native_log_sha256=inventory['work/native.log']['sha256'])
            r['diagnosis']=result;r['all_65_original_members_retained']=True
            r['native_capsule_not_accepted']=True
        methods();r['status']='PASS_LOSSLESS_MAINCHIP_EVIDENCE_RECOVERY_ORIGINAL_ROUTING_REMAINS_REJECTED'
    except BaseException as e:
        r.update(status='FAIL_MAINCHIP_ARTIFACT_RECOVERY',error=repr(e),traceback=traceback.format_exc());raise
    finally:
        r['outputs']={str(p.relative_to(OUT)):dict(bytes=p.stat().st_size,sha256=file_sha(p))
            for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'}
        write_json(OUT/'result.json',r)
        data=(OUT/'result.json').read_bytes()
        print('RECOVERY_RESULT_SHA256 '+digest(data));print('RECOVERY_RESULT_BYTES '+str(len(data)))
        text=__import__('base64').b64encode(data).decode();chunks=[text[i:i+4096]for i in range(0,len(text),4096)]
        for i,b in enumerate(chunks):print('RECOVERY_RESULT_BASE64 '+str(i)+'/'+str(len(chunks))+' '+b)
        print(r['status'],flush=True)
if __name__=='__main__':main()
