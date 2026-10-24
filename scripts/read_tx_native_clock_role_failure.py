#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Read the exact rejected native role log on GitHub. No CAD or simulator."""
import argparse,base64,copy,hashlib,io,json,os,subprocess,tarfile
from pathlib import Path,PurePosixPath
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'cloud-tx-native-clock-role-failure-readback'
RUN=40102668052
HEAD='d9d3e8453dbb5831354bb84b40e042dd73c61211'
JOB=120904864521
REPO='repos/Melihakbulut221/nssoc/'
PREFIX='cloud-tx-output8088-native-clock-roles'
SUMMARY_SHA='d6ae64be4af600ed7a260727b8bc58cf861f7dc10c9db512e00d9a8d1f796f97'
PARTS_SHA='7663f750f9ef054d00bf69e2faa1dbd343c4130196ed298064430b28d2eeaaf0'
ARCHIVE_SHA='af93d80b3e04fcfa5212ad2272ec34500f172353b206369adf4c0b1c092341aa'
LOG_SHA='edfa6b5fe0396099ee8676783e42cc843fdea8d6b86fcbe563ced27396284bfe'
PIN={
 'native-role-binding.log':LOG_SHA,
 'tx-output8088-branchtailfeed-interfaces-source/parts.json':'278156444c2bd2159f6f029f8f3a9d51ad156d1a84a751ea41e4e75e6b5b6a51',
 'tx-output8088-branchtailfeed-interfaces-source/summary.json':'e872278654de17a300e5004c463a1ad37b5c9e1116ed7d8720e2872f8124c2b9',
 'native/original-interfaces.json':'13bfff54e68a5355547fc64e4ebdd64e347c5b54a43b8c924b9ece724b009aaf',
 'result.json':SUMMARY_SHA}
def sha(b):return hashlib.sha256(b).hexdigest()
def api(path):return json.loads(subprocess.check_output(['gh','api',REPO+path]))
def asset(aid,size,digest):
    m=api('releases/assets/'+str(aid))
    assert m['id']==aid and m['size']==size and m['digest']=='sha256:'+digest
    b=subprocess.check_output(['gh','api','-H','Accept: application/octet-stream',REPO+'releases/assets/'+str(aid)])
    assert len(b)==size and sha(b)==digest
    return b
def methods():
    m=json.loads((ROOT/'scripts/tx-native-clock-role-failure-readback-methods.json').read_text())
    for p,h in m['protected'].items():assert sha((ROOT/p).read_bytes())==h,p
    assert m['native_execution_allowed']is False
    return m
def source(s,p):
    assert s['status']=='FAIL_OR_ERROR'and s['source_head']==HEAD and s['native_returncode']==1
    assert s['error']=="AssertionError('Native clock role, bank topology or physical polarity check rejected')"
    assert 'line 109, in main'in s['traceback']
    assert s['no_new_simulation']is True and not s['full_phy_accepted']and not s['electrical_accepted']
    assert s['outputs']=={k:v for k,v in PIN.items()if k!='result.json'}
    assert s['restore']['run']==40083738813
    assert s['restore']['summary_sha256']==PIN['tx-output8088-branchtailfeed-interfaces-source/summary.json']
    assert s['restore']['manifest_sha256']==PIN['tx-output8088-branchtailfeed-interfaces-source/parts.json']
    assert p['format']=='ordered-tar-gzip-parts-v1'and p['source_directory']==PREFIX
    assert p['stem']=='tx-output8088-native-clock-roles-40102668052-1'
    assert p['bytes']==22610 and p['sha256']==ARCHIVE_SHA
    assert p['parts']==[dict(index=0,name=p['stem']+'.tar.gz.part0000',bytes=22610,sha256=ARCHIVE_SHA)]
    assert p['verification']==dict(parts=1,bytes=22610,sha256=ARCHIVE_SHA,all_parts_and_combined_bytes_verified=True)
def identity(run,job):
    assert run['id']==RUN and run['head_sha']==HEAD and run['head_branch']=='codex/tx-clock-phase-parent'
    assert run['event']=='workflow_dispatch'and run['run_attempt']==1 and run['status']=='completed'and run['conclusion']=='failure'
    assert run['path']=='.github/workflows/tx-output8088-native-clock-roles-cloud.yml'
    assert job['id']==JOB and job['run_id']==RUN and job['head_sha']==HEAD and job['run_attempt']==1
    assert job['name']=='actual-native-clock-roles'and job['status']=='completed'and job['conclusion']=='failure'
def archive(payload,expected):
    found={};dirs=set()
    allowed_dirs={PREFIX}|{PREFIX+'/'+str(p)for name in expected for p in PurePosixPath(name).parents if str(p)!='.'}
    with tarfile.open(fileobj=io.BytesIO(payload),mode='r:gz')as t:
        for member in t:
            name=member.name
            assert name and '\\'not in name and ':'not in name and not any(ord(c)<32 or ord(c)==127 for c in name)
            path=PurePosixPath(name);assert not path.is_absolute()and '..'not in path.parts
            canonical=str(path)
            assert name==canonical or(member.isdir()and name==canonical+'/'),'Noncanonical member'
            assert not member.issym()and not member.islnk()and not member.issparse()
            if member.isdir():
                assert canonical in allowed_dirs and canonical not in dirs
                dirs.add(canonical);continue
            assert member.isfile()and name.startswith(PREFIX+'/')
            key=name[len(PREFIX)+1:]
            assert key in expected and key not in found and 0<=member.size<=1024**2
            f=t.extractfile(member);assert f is not None
            with f:b=f.read(1024**2+1)
            assert len(b)==member.size and sha(b)==expected[key]
            found[key]=b
    assert set(found)==set(expected)and dirs==allowed_dirs
    assert sum(map(len,found.values()))<=2*1024**2
    return found
def controls(s,p,run,job):
    source(s,p);identity(run,job);bad=[]
    def reject(name,fn):
        try:fn()
        except(AssertionError,KeyError,ValueError,tarfile.TarError,EOFError):bad.append(name)
        else:raise AssertionError('Accepted '+name)
    for name,key,value in [('accepted','electrical_accepted',True),('PHY-claim','full_phy_accepted',True),('source','source_head','0'*40),('return','native_returncode',0),('different-error','error','other')]:
        q=copy.deepcopy(s);q[key]=value;reject(name,lambda:source(q,p))
    q=copy.deepcopy(s);q['outputs']['native-role-binding.log']='0'*64
    reject('log-hash',lambda:source(q,p))
    for name,key,value in [('part-size','bytes',1),('part-hash','sha256','0'*64)]:
        q=copy.deepcopy(p);q['parts'][0][key]=value;reject(name,lambda:source(s,q))
    for name,which,key,value in [('run-head',0,'head_sha','0'*40),('run-live',0,'status','in_progress'),('run-success',0,'conclusion','success'),('wrong-job',1,'id',1),('job-head',1,'head_sha','0'*40),('job-success',1,'conclusion','success')]:
        q=copy.deepcopy([run,job]);q[which][key]=value;reject(name,lambda:identity(*q))
    fixture={'result.json':b'{}','native/log.txt':b'actual native diagnostic'}
    expected={k:sha(v)for k,v in fixture.items()}
    def package(mutation=None):
        entries=[(PREFIX,b'',tarfile.DIRTYPE),(PREFIX+'/native',b'',tarfile.DIRTYPE)]+[(PREFIX+'/'+k,b,tarfile.REGTYPE)for k,b in fixture.items()]
        if mutation:entries=mutation(entries)
        data=io.BytesIO()
        with tarfile.open(fileobj=data,mode='w:gz')as t:
            for name,b,kind in entries:
                m=tarfile.TarInfo(name);m.type=kind;m.size=len(b)if kind==tarfile.REGTYPE else 0
                if kind in(tarfile.SYMTYPE,tarfile.LNKTYPE):m.linkname='/forbidden'
                t.addfile(m,io.BytesIO(b)if kind==tarfile.REGTYPE else None)
        return data.getvalue()
    assert archive(package(),expected)==fixture
    assert archive(package(lambda e:[(n+'/'if k==tarfile.DIRTYPE else n,b,k)for n,b,k in e]),expected)==fixture
    for name,mut in [
      ('traversal',lambda e:e+[(PREFIX+'/../escape',b'x',tarfile.REGTYPE)]),
      ('absolute',lambda e:e+[('/escape',b'x',tarfile.REGTYPE)]),
      ('duplicate',lambda e:e+[e[-1]]),('missing',lambda e:e[:-1]),
      ('symlink',lambda e:e[:-1]+[(e[-1][0],b'',tarfile.SYMTYPE)]),
      ('hardlink',lambda e:e[:-1]+[(e[-1][0],b'',tarfile.LNKTYPE)]),
      ('corrupt-member',lambda e:e[:-1]+[(e[-1][0],b'changed',tarfile.REGTYPE)]),
      ('extra-directory',lambda e:e+[(PREFIX+'/extra',b'',tarfile.DIRTYPE)])]:
        reject(name,lambda:archive(package(mut),expected))
    assert len(bad)==22
    return dict(status='PASS_EXACT_REJECTION_AND22_ARCHIVE_SOURCE_FAULTS',rejected=bad,native_execution=False)
def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    a=argparse.ArgumentParser();a.add_argument('--controls',action='store_true');a.add_argument('--readback',action='store_true');args=a.parse_args()
    assert args.controls!=args.readback
    OUT.mkdir(exist_ok=False)
    r=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],run_id=os.environ['GITHUB_RUN_ID'],native_execution=False,
        native_role_accepted=False,electrical_accepted=False,full_phy_accepted=False)
    try:
        r['method']=methods()
        sb=asset(672628572,4098,SUMMARY_SHA);pb=asset(672628641,874,PARTS_SHA)
        run=api('actions/runs/'+str(RUN));job=api('actions/jobs/'+str(JOB))
        s=json.loads(sb);p=json.loads(pb);r['controls']=controls(s,p,run,job)
        if args.controls:r['status']='PASS_CLOCK_ROLE_REJECTION_READER_CONTROLS_ONLY';return
        payload=asset(672628758,22610,ARCHIVE_SHA)
        found=archive(payload,PIN);assert found['result.json']==sb and json.loads(found['result.json'])==s
        log=found['native-role-binding.log'].decode('utf-8')
        r.update(status='PASS_EXACT_NATIVE_ROLE_FAILURE_LOG_READBACK_ORIGINAL_REJECTION_REMAINS',
            original_run=RUN,original_source=HEAD,original_summary_sha256=SUMMARY_SHA,original_parts_sha256=PARTS_SHA,
            original_archive_sha256=ARCHIVE_SHA,all_five_members_verified=True,
            members={k:dict(bytes=len(b),sha256=sha(b))for k,b in found.items()},
            original_report=s,native_role_log_utf8=log,native_role_log_sha256=sha(found['native-role-binding.log']))
        (OUT/'native-role-binding.log').write_bytes(found['native-role-binding.log'])
        methods()
    except BaseException as e:r.update(status='FAIL_CLOCK_ROLE_FAILURE_READBACK',error=repr(e));raise
    finally:
        data=(json.dumps(r,indent=2)+'\n').encode();(OUT/'result.json').write_bytes(data)
        print('RESULT_SHA256 '+sha(data));print('RESULT_BYTES '+str(len(data)))
        b64=base64.b64encode(data).decode();chunks=[b64[i:i+4096]for i in range(0,len(b64),4096)]
        for i,b in enumerate(chunks):print('RESULT_BASE64 '+str(i)+'/'+str(len(chunks))+' '+b)
        print(r['status'],flush=True)
if __name__=='__main__':main()
