# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Actual transport children, retained prefixes, hard integrity failures and stop."""
import contextlib
import gzip
import hashlib
import http.server
import importlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import threading
import time

import pytest

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts'))
m=importlib.import_module('publish_pcie_native_capture_v3')


def payload(tmp_path):
    p=tmp_path/'capture.bin';p.write_bytes(bytes(range(256))*8192)
    expected=m.pin(p)
    asset=dict(id=123,name=p.name,size=expected['bytes'],digest='sha256:'+expected['sha256'],state='uploaded',browser_download_url='http://127.0.0.1/unused')
    return p,expected,asset


def gh_fixture(tmp_path,monkeypatch,p,asset,modes):
    counter=tmp_path/'counter.json'
    counter.write_text('0')
    config=tmp_path/'gh-config.json'
    config.write_text(json.dumps(dict(source=str(p),asset=asset,modes=modes,counter=str(counter))))
    gh=tmp_path/'gh'
    gh.write_text('#!'+sys.executable+'\n'+'''import json,sys,time,os,signal,subprocess
from pathlib import Path
c=json.loads(Path('''+repr(str(config))+''').read_text())
if '/releases/tags/' in ' '.join(sys.argv):
 print(json.dumps({'assets':[c['asset']]}));raise SystemExit(0)
n=int(Path(c['counter']).read_text());Path(c['counter']).write_text(str(n+1))
a=c['modes'][min(n,len(c['modes'])-1)]
b=Path(c['source']).read_bytes();b=b[:a.get('cut',len(b))]
if a.get('corrupt'):b=bytes([b[0]^1])+b[1:]
if a.get('extra'):b+=b'EXTRA'
if a.get('ignore_term'):signal.signal(signal.SIGTERM,signal.SIG_IGN)
if a.get('child'):
 q=subprocess.Popen([sys.executable,'-c','import signal,time;signal.signal(signal.SIGTERM,signal.SIG_IGN);time.sleep(60)'])
 Path(c['counter']+'.child').write_text(str(q.pid))
sys.stdout.buffer.write(b);sys.stdout.buffer.flush()
sys.stderr.write(a.get('stderr',''));sys.stderr.flush()
if a.get('sleep'):time.sleep(a['sleep'])
raise SystemExit(a.get('exit',0))
''')
    gh.chmod(0o755)
    monkeypatch.setenv('PATH',str(tmp_path)+os.pathsep+os.environ['PATH'])
    return counter


def journal(client):return json.loads((client.directory/'attempts.json').read_text())


@pytest.mark.parametrize('message',['net/http: TLS handshake timeout','connection reset by peer','HTTP 429','HTTP 500','HTTP 503'])
def test_native_transient_authentication_retries_and_preserves_exact_prefix(tmp_path,monkeypatch,message):
    p,e,a=payload(tmp_path)
    gh_fixture(tmp_path,monkeypatch,p,a,[dict(cut=12345,stderr=message,exit=1),{}])
    c=m.Client(tmp_path/'evidence',attempts=2,timeout=3,backoff=0)
    assert c.authenticated(a,p,e)==e
    rows=journal(c);assert [x['status'] for x in rows]==['TRANSPORT_FAILURE','PASS']
    failed=rows[0];observed=failed['observed_download']
    assert failed['returncode']==1
    assert gzip.open(failed['stderr']['path'],'rb').read()==message.encode()
    reconstructed=p.read_bytes()[:observed['matched_local_prefix_bytes']]
    assert len(reconstructed)==12345==observed['bytes']
    assert hashlib.sha256(reconstructed).hexdigest()==observed['sha256']
    assert failed['retained_local_source']==dict(path=str(p),**e)
    assert sum(x.stat().st_size for x in c.directory.rglob('*') if x.is_file())<100000
    assert p.stat().st_size==2*1024**2


def test_zero_byte_tls_is_recorded_and_not_a_payload_integrity_failure(tmp_path,monkeypatch):
    p,e,a=payload(tmp_path)
    gh_fixture(tmp_path,monkeypatch,p,a,[dict(cut=0,stderr='TLS handshake timeout',exit=1),{}])
    c=m.Client(tmp_path/'evidence',attempts=2,timeout=3,backoff=0)
    c.authenticated(a,p,e)
    r=journal(c)[0];assert r['observed_download']['bytes']==0 and r['observed_download']['matched_local_prefix_bytes']==0
    assert r['observed_download']['sha256']==hashlib.sha256(b'').hexdigest()


@pytest.mark.parametrize('mode',[dict(cut=12345),dict(corrupt=True),dict(extra=True)])
def test_actual_completed_truncation_corruption_extra_bytes_never_retry(tmp_path,monkeypatch,mode):
    p,e,a=payload(tmp_path);counter=gh_fixture(tmp_path,monkeypatch,p,a,[mode,{}])
    c=m.Client(tmp_path/'evidence',attempts=4,timeout=3,backoff=0)
    with pytest.raises(m.IntegrityError):c.authenticated(a,p,e)
    r=journal(c);assert len(r)==1 and r[0]['status']=='FATAL_NO_RETRY' and counter.read_text()=='1'
    v=r[0]['observed_download'];body=p.read_bytes()[:v['matched_local_prefix_bytes']]
    if v['mismatching_chunk']:body+=Path(v['mismatching_chunk']['path']).read_bytes()
    assert len(body)==v['bytes'] and hashlib.sha256(body).hexdigest()==v['sha256']


@pytest.mark.parametrize('code',[401,404])
def test_actual_permanent_auth_failures_never_retry(tmp_path,monkeypatch,code):
    p,e,a=payload(tmp_path);gh_fixture(tmp_path,monkeypatch,p,a,[dict(cut=0,stderr=f'HTTP {code}',exit=1),{}])
    c=m.Client(tmp_path/'evidence',attempts=4,timeout=3,backoff=0)
    with pytest.raises(RuntimeError):c.authenticated(a,p,e)
    assert len(journal(c))==1 and journal(c)[0]['status']=='FATAL_NO_RETRY'


def test_retry_budget_is_finite(tmp_path,monkeypatch):
    p,e,a=payload(tmp_path);gh_fixture(tmp_path,monkeypatch,p,a,[dict(cut=0,stderr='TLS handshake timeout',exit=1)])
    c=m.Client(tmp_path/'evidence',attempts=3,timeout=3,backoff=0)
    with pytest.raises(m.TransportError):c.authenticated(a,p,e)
    assert len(journal(c))==3


def test_native_timeout_after_prefix_cleans_term_ignoring_descendant_then_retries(tmp_path,monkeypatch):
    p,e,a=payload(tmp_path)
    counter=gh_fixture(tmp_path,monkeypatch,p,a,[dict(cut=34567,sleep=60,ignore_term=True,child=True),{}])
    c=m.Client(tmp_path/'evidence',attempts=2,timeout=.2,backoff=0)
    c.authenticated(a,p,e)
    r=journal(c);assert r[0]['deadline_triggered'] and r[0]['observed_download']['bytes']==34567
    owner=json.loads(Path(r[0]['owned_processes']).read_text())
    assert owner['cleanup']['groups'][0]['term_sent'] and owner['cleanup']['groups'][0]['kill_sent']
    assert not owner['cleanup']['groups'][0]['identity_reused']
    assert r[0]['elapsed_seconds']<2
    child=int(Path(str(counter)+'.child').read_text());identity=m.lifecycle.process_identity(child)
    assert identity is None or identity['state']=='Z'


@contextlib.contextmanager
def http_fixture(data,modes):
    calls=[]
    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            mode=modes[min(len(calls),len(modes)-1)];calls.append(mode)
            self.send_response(mode.get('status',200));self.end_headers()
            self.wfile.write(mode.get('body',data))
        def log_message(self,*args):pass
    server=http.server.ThreadingHTTPServer(('127.0.0.1',0),Handler)
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    try:yield f'http://127.0.0.1:{server.server_port}/asset',calls
    finally:server.shutdown();server.server_close();thread.join()


@pytest.mark.parametrize('status',[429,503,401,404])
def test_actual_anonymous_http_status_retry_classification(tmp_path,status):
    p,e,a=payload(tmp_path);c=m.Client(tmp_path/'evidence',attempts=2,timeout=3,backoff=0)
    with http_fixture(p.read_bytes(),[dict(status=status,body=b'error'),{}]) as(url,calls):
        a['browser_download_url']=url
        if status in (429,503):assert c.anonymous(a,p,e)==e and len(calls)==2
        else:
            with pytest.raises(Exception):c.anonymous(a,p,e)
            assert len(calls)==1
    response=json.loads(Path(journal(c)[0]['response']['path']).read_text())
    assert response['http_status']==status
    assert Path(response['error_body']['path']).read_bytes()==b'error'
    assert gzip.open(journal(c)[0]['stderr']['path'],'rb').read()


def test_actual_anonymous_corruption_never_retries(tmp_path):
    p,e,a=payload(tmp_path);c=m.Client(tmp_path/'evidence',attempts=2,timeout=3,backoff=0)
    with http_fixture(p.read_bytes(),[dict(body=b'bad'),{}]) as(url,calls):
        a['browser_download_url']=url
        with pytest.raises(m.IntegrityError):c.anonymous(a,p,e)
        assert len(calls)==1
    assert Path(journal(c)[0]['observed_download']['mismatching_chunk']['path']).read_bytes()==b'bad'


@pytest.mark.parametrize('field,value',[('size',0),('digest','sha256:'+'0'*64),('state','new')])
def test_metadata_integrity_faults_are_fatal(tmp_path,field,value):
    p,e,a=payload(tmp_path);a[field]=value
    with pytest.raises(m.IntegrityError):m.validate_asset(a,e)


@pytest.mark.parametrize('phase',['download','backoff'])
def test_actual_wrapper_stop_reaps_child_group_and_prevents_retry(tmp_path,monkeypatch,phase):
    p,e,a=payload(tmp_path)
    mode=dict(cut=23456,sleep=60,ignore_term=True,child=True) if phase=='download' else dict(cut=0,stderr='TLS handshake timeout',exit=1)
    gh_fixture(tmp_path,monkeypatch,p,a,[mode,{}])
    receipt=tmp_path/'receipt.json';log=tmp_path/'wrapper.log'
    with log.open('wb') as stream:
        proc=subprocess.Popen([sys.executable,str(ROOT/'scripts/publish_pcie_native_capture_v3.py'),'--out',str(receipt),str(p)],stdout=stream,stderr=subprocess.STDOUT)
        start=time.monotonic()
        while time.monotonic()-start<8:
            transport=receipt.with_suffix('.transport')
            if phase=='download':
                files=list(transport.glob('*authenticated*/owned-processes.json'))
                if files and json.loads(files[0].read_text())['processes']:break
            else:
                path=transport/'attempts.json'
                if path.exists() and any(x['status']=='TRANSPORT_FAILURE' for x in json.loads(path.read_text())):break
            time.sleep(.01)
        else:proc.kill();pytest.fail(log.read_text())
        before=time.monotonic();proc.send_signal(signal.SIGTERM);assert proc.wait(timeout=3)!=0
        assert time.monotonic()-before<2
    r=json.loads(receipt.read_text());assert r['status']=='FAIL' and r['explicit_stop']
    rows=json.loads((transport/'attempts.json').read_text())
    auth=[x for x in rows if x['kind']=='authenticated'];assert len(auth)==1
    for f in transport.glob('*/owned-processes.json'):
        owner=json.loads(f.read_text())
        for entry in owner['processes']:
            identity=entry['identity'];current=m.lifecycle.process_identity(identity['pid'])
            assert current is None or current['start_ticks']!=identity['start_ticks'] or current['state']=='Z'
            assert not any(x['state']!='Z' for x in m.lifecycle.group_members(entry['process_group']))
