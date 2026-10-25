#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Read the one authenticated small rejected-fixture artifact in hosted RAM only."""
import argparse,base64,hashlib,io,json,os,stat,subprocess,zipfile
from pathlib import Path,PurePosixPath
ROOT=Path(__file__).resolve().parents[1]
RUN=40172782148
JOB=121106975996
SOURCE='023fe9ce2b2226e3858c5436ebe48f929aed734d'
ARTIFACT=12590911691
SIZE=13840
DIGEST='68e6bf54ac3bb925b92883538a96ec2d584da15f0bbb59c106adc3a09396890f'
RESULT_SHA='e274559d3fddc80ed02b492395e1d396c7c513f77e521f0c1ec425beccd377b6'
STDERR_SHA='7aeab8d8f8e0207f393a35e5d8565a5f33b312277a346bc5c3c23259aee3746b'
def sha(b):return hashlib.sha256(b).hexdigest()
def api_command(path,raw=False):
    return ['gh','api','repos/Melihakbulut221/nssoc/'+path]+(['--allow-escape-sequences']if raw else [])
def validate_api_command(command,path,raw):
    assert command==api_command(path,raw),'Raw API transport arguments changed'
def api(path,raw=False):
    command=api_command(path,raw);validate_api_command(command,path,raw)
    b=subprocess.check_output(command)
    return b if raw else json.loads(b)
def scan(raw,size,digest):
    assert len(raw)==size and sha(raw)==digest,'Artifact transport bytes changed'
    files={}
    with zipfile.ZipFile(io.BytesIO(raw))as z:
        total=0
        for item in z.infolist():
            p=PurePosixPath(item.filename)
            assert str(p)==item.filename and not p.is_absolute() and '..'not in p.parts
            assert chr(92)not in item.filename and '\x00'not in item.filename and ':'not in item.filename
            assert not item.is_dir() and item.filename not in files
            mode=(item.external_attr>>16)&0xffff
            assert stat.S_IFMT(mode)in(0,stat.S_IFREG)
            assert 0<=item.file_size<=1024**2 and not item.flag_bits&1
            total+=item.file_size;assert total<=16*1024**2
            b=z.read(item);assert len(b)==item.file_size
            files[item.filename]=b
    assert files
    return files
def control_zip(entries):
    b=io.BytesIO()
    with zipfile.ZipFile(b,'w')as z:
        for name,body,mode in entries:
            i=zipfile.ZipInfo(name);i.external_attr=mode<<16;z.writestr(i,body)
    return b.getvalue()
def controls():
    good=control_zip([('result.json',b'{}\n',stat.S_IFREG|0o600)])
    assert scan(good,len(good),sha(good))=={'result.json':b'{}\n'}
    faults=[]
    def reject(name,fn):
        try:fn()
        except(AssertionError,zipfile.BadZipFile):faults.append(name)
        else:raise AssertionError('Accepted readback corruption '+name)
    reject('transport-size',lambda:scan(good,len(good)+1,sha(good)))
    reject('transport-hash',lambda:scan(good,len(good),'0'*64))
    for name,entries in [
      ('duplicate',[('a',b'a',stat.S_IFREG),('a',b'b',stat.S_IFREG)]),
      ('parent',[('../a',b'a',stat.S_IFREG)]),
      ('absolute',[('/a',b'a',stat.S_IFREG)]),
      ('symlink',[('a',b'a',stat.S_IFLNK)]),
      ('oversize',[('a',b'a'*(1024**2+1),stat.S_IFREG)]),
      ('directory',[('a/',b'',stat.S_IFDIR)]),
      ('single-backslash',[('a'+chr(92)+'b',b'a',stat.S_IFREG)])]:
        raw=control_zip(entries);reject(name,lambda raw=raw:scan(raw,len(raw),sha(raw)))
    path='actions/artifacts/12590911691/zip'
    validate_api_command(api_command(path,True),path,True)
    validate_api_command(api_command('actions/runs/40172782148',False),'actions/runs/40172782148',False)
    reject('raw-transport-flag-removed',lambda:validate_api_command(api_command(path,False),path,True))
    reject('metadata-raw-flag-invented',lambda:validate_api_command(api_command(path,True),path,False))
    assert len(faults)==11
    return dict(status='PASS_11_SMALL_ARCHIVE_AND_TRANSPORT_CONTROLS_ONLY',rejected=faults,new_fixture_run=False)
def main():
    p=argparse.ArgumentParser();p.add_argument('--readback-only',action='store_true');args=p.parse_args()
    assert os.environ.get('GITHUB_ACTIONS')=='true'and args.readback_only
    m=json.loads((ROOT/'scripts/mainchip-userstack-fixture-methods.json').read_text())
    for path,h in m['protected'].items():assert sha((ROOT/path).read_bytes())==h,path
    assert m['artifact_readback_authorized']is True
    check=controls()
    run=api('actions/runs/'+str(RUN));job=api('actions/jobs/'+str(JOB))
    assert run['id']==RUN and run['head_sha']==SOURCE and run['run_attempt']==1
    assert run['status']=='completed'and run['conclusion']=='failure'
    assert run['event']=='workflow_dispatch'and run['path']=='.github/workflows/mainchip-userstack-fixture-cloud.yml'
    assert run['head_branch']=='codex/mainchip-userstack-proposal'
    assert job['id']==JOB and job['run_id']==RUN and job['head_sha']==SOURCE
    assert job['run_attempt']==1 and job['name']=='harmless-fixture'and job['conclusion']=='failure'
    assert job['status']=='completed'
    a=api('actions/artifacts/'+str(ARTIFACT))
    assert a['id']==ARTIFACT and a['name']=='mainchip-userstack-harmless-fixture'and not a['expired']
    assert a['size_in_bytes']==SIZE and a['digest']=='sha256:'+DIGEST
    assert a['workflow_run']['id']==RUN and a['workflow_run']['head_sha']==SOURCE
    raw=api('actions/artifacts/'+str(ARTIFACT)+'/zip',raw=True)
    files=scan(raw,SIZE,DIGEST);assert len(files)==12
    result=files['result.json'];assert len(result)==3689 and sha(result)==RESULT_SHA
    r=json.loads(result);assert r['status']=='REJECTED_USERSTACK_FIXTURE'and r['controls']==[]
    error=files['twenty/sample-00/command/stderr.log'];assert len(error)==155 and sha(error)==STDERR_SHA
    assert files['twenty/sample-00/command/stdout.log']==b''
    command=json.loads(files['twenty/sample-00/command/command.json'])
    assert command['returncode']==1 and command['cleanup']['live_remaining']is False
    selected={n:dict(bytes=len(files[n]),sha256=sha(files[n]),text=files[n].decode('utf-8'))for n in [
        'twenty/sample-00/command/stderr.log','twenty/sample-00/command/stdout.log',
        'twenty/sample-00/reader.gdb','twenty/sample-00/result.json']}
    report=dict(status='PASS_EXACT_REJECTED_FIXTURE_ARTIFACT_READBACK_ONLY',run=RUN,job=JOB,source=SOURCE,
        artifact={k:a[k]for k in ('id','name','size_in_bytes','digest')},controls=check,
        members={n:dict(bytes=len(b),sha256=sha(b))for n,b in files.items()},selected=selected,
        original_rejection_preserved=True,new_fixture_run=False,native_process_restored=False,
        native_attachment_authorized=False,normal_continuation_accepted=False)
    folder=ROOT/'cloud-mainchip-userstack-readback';folder.mkdir(exist_ok=False)
    b=(json.dumps(report,indent=2,allow_nan=False)+'\n').encode();(folder/'result.json').write_bytes(b)
    print('USERSTACK_READBACK_RESULT '+json.dumps(dict(bytes=len(b),sha256=sha(b))),flush=True)
    for n in range(0,len(b),3072):
        print('USERSTACK_READBACK_CHUNK '+str(n//3072)+' '+base64.b64encode(b[n:n+3072]).decode(),flush=True)
    print('EXACT_ORIGINAL_GDB_STDERR_BEGIN\n'+error.decode()+'EXACT_ORIGINAL_GDB_STDERR_END',flush=True)
if __name__=='__main__':main()
