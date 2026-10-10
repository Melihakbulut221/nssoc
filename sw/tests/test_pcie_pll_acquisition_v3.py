# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Exact publication bridge and real nested ownership/PartQueue controls; no SPICE."""
import hashlib
import importlib.util
import json
import lzma
import os
from pathlib import Path
import signal
import struct
import subprocess
import sys
import time
from types import SimpleNamespace

import pytest

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts'))
import characterize_pcie_pll_acquisition_v3 as m
spec=importlib.util.spec_from_file_location('publisher_v3_fixture',ROOT/'sw/tests/test_pcie_native_publisher_v3.py')
f=importlib.util.module_from_spec(spec);spec.loader.exec_module(f)


def test_exact_inverse_and_private_namespaces():
    for name in ['run','publisher']:
        original=getattr(m,name+'_source')
        for before,after in reversed(m.BRIDGES[name]['exact_replacements']):
            assert original.count(after)==1;original=original.replace(after,before)
        assert original==getattr(m.previous,name+'_source')
        assert hashlib.sha256(original.encode()).hexdigest()==m.BRIDGES[name]['original_sha256']
    assert m.main_source==m.previous.main_source
    assert m.namespace is not m.previous.namespace
    assert m.namespace['run'] is m.run and m.namespace['verify_parent'] is m.verify_parent
    assert m.previous.namespace['run'] is m.previous.run
    assert m.previous.publisher_namespace['publication'] is m.previous.publication
    assert m.publisher_namespace['publication'] is m.publication
    assert m.publisher_namespace['PUBLISHER_SHA']==m.PUBLISHER_SHA
    assert m.RELEASE_TAG==m.previous.RELEASE_TAG


def test_no_electrical_numerical_lifecycle_or_resource_change():
    for name in ['stream_deck','measurements','startup_proof','acquisition','prerequisites','runtime']:
        assert getattr(m,name) is getattr(m.previous,name)
    for name in ['capture','native_wait','Meter','guard','FLOOR','CAP','PART_BYTES','life']:
        assert m.namespace[name] is m.previous.namespace[name]
    assert m.STOP==m.previous.STOP==1e-6
    assert m.namespace['FLOOR']==512*1024**2 and m.namespace['CAP']==50*1024**2
    assert m.previous.previous.FREQUENCY_RELATIVE_LIMIT==100e-6
    assert m.previous.previous.PHASE_RANGE_LIMIT_S==50e-12
    assert m.sha(m.previous.__file__)==m.PREVIOUS_SHA
    assert m.sha(m.publication.__file__)==m.PUBLISHER_SHA
    assert m.publication.pin(m.publication.lifecycle.__file__)['sha256']==m.publication.OWNER_SHA


@pytest.mark.parametrize('step',[5e-12,2.5e-12])
def test_actual_deck_generation_bytes_identical(step,tmp_path,monkeypatch):
    # Exact preserved deck text only: no native tool/PDK or volatile fixture read.
    absent=tmp_path/'absent-native-prerequisite'
    assert not absent.exists()
    monkeypatch.setitem(m.namespace,'ORIGINAL',absent)
    monkeypatch.setitem(m.previous.namespace,'ORIGINAL',absent)
    fixture=ROOT/'sw/tests/fixtures/pcie_pll_acquisition_v3/connected-loop-bench.cir'
    assert m.sha(fixture)=='6f31cfc4c419005b857608eb2d873d13b44c8e53e0328517cb9eefeb373b55c4'
    original=fixture.read_text()
    assert m.stream_deck(original,step,1e-6)==m.previous.stream_deck(original,step,1e-6)
    assert m.stream_deck(original,step,1e-6).count(f'.tran {step:.12g} 1e-06 0 {step:.12g}\n')==1


@pytest.mark.parametrize('version,number,has',[(sys.version_info,'0.0',True),((3,14),'2.5.3',True),((3,12),'2.5.3',False)])
def test_runtime_guard_unchanged(version,number,has):
    with pytest.raises(RuntimeError):m.runtime.check_runtime(version,number,has)


def queue_fixture(tmp_path,monkeypatch,modes):
    raw=struct.pack('<4d',0.0,1.25,2.5e-12,1.3)
    packed=lzma.compress(raw,preset=1)
    source=tmp_path/'expected-compressed-fixture.bin';source.write_bytes(packed)
    expected=m.publication.pin(source)
    asset=dict(id=123,name='producer-control-part00000.bin.xz',size=len(packed),digest='sha256:'+expected['sha256'],state='uploaded',browser_download_url='unused')
    return raw,packed,source,asset


@pytest.mark.parametrize('mode',['transient','mismatch'])
def test_actual_nested_publisher_part_queue_retention_and_native_owner(tmp_path,monkeypatch,mode):
    raw,packed,source,asset=queue_fixture(tmp_path,monkeypatch,mode)
    with f.http_fixture(packed,[{}]) as(url,calls):
        asset['browser_download_url']=url
        modes=[dict(cut=8,stderr='TLS handshake timeout',exit=1),{}] if mode=='transient' else [dict(corrupt=True),{}]
        f.gh_fixture(tmp_path,monkeypatch,source,asset,modes)
        owner_path=tmp_path/'outer-owner.json';partdir=tmp_path/'parts'
        try:
            with m.life.ProcessOwner(owner_path) as owner:
                sleeper=owner.launch('native',[sys.executable,'-c','import time;time.sleep(60)'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
                queue=m.life.PartQueue(partdir,'producer-control',['time','v(x)'],m.OwnedPublisherV3(owner),2,True,m.namespace['FLOOR'])
                queue.append(raw[:16]);queue.append(raw[16:])
                ledger=queue.finish()
                assert mode=='transient' and sleeper.poll() is None
                assert ledger['status']=='PASS_PUBLISHED_PARTS' and ledger['rows']==2
                assert ledger['payload_sha256']==hashlib.sha256(raw).hexdigest()
                assert ledger['parts'][0]['local_state']=='REMOVED_EXACT_PUBLIC_DUPLICATE'
                assert not (partdir/asset['name']).exists()
                # Source reference is handed to the exact verified public asset;
                # the queue reclaims only its local duplicate after both paths.
                attempts=json.loads((partdir/'publication-00000.transport/attempts.json').read_text())
                auth=[x for x in attempts if x['kind']=='authenticated']
                assert [x['status'] for x in auth]==['TRANSPORT_FAILURE','PASS']
                observed=auth[0]['observed_download'];prefix=packed[:observed['matched_local_prefix_bytes']]
                assert hashlib.sha256(prefix).hexdigest()==observed['sha256'] and len(prefix)==8
                assert auth[0]['retained_local_source']['sha256']==ledger['parts'][0]['sha256']
                free,used=m.namespace['guard'](partdir)
                assert free>=512*1024**2 and used<50*1024**2
                sleeper.terminate();owner.wait(sleeper)
        except ValueError:
            assert mode=='mismatch'
        ledger=json.loads((partdir/'parts.json').read_text())
        ownership=json.loads(owner_path.read_text())
        assert sleeper.poll() is not None
        if mode=='mismatch':
            assert ledger['status']=='ERROR_PART_RETAINED'
            assert (partdir/asset['name']).read_bytes()==packed and bytes(queue.pending)==raw
            assert ownership['status']=='CANCELLED'
            attempts=json.loads((partdir/'publication-00000.transport/attempts.json').read_text())
            assert len([x for x in attempts if x['kind']=='authenticated'])==1
            assert not calls
        else:assert len(calls)==1
        for entry in ownership['processes']:
            assert not any(x['state']!='Z' for x in m.life.group_members(entry['process_group']))


def test_publisher_pin_failure_spawns_no_child(tmp_path,monkeypatch):
    monkeypatch.setitem(m.publisher_namespace,'PUBLISHER_SHA','0'*64)
    part=tmp_path/'part.bin';part.write_bytes(b'fixed')
    with pytest.raises(ValueError,match='Frozen publisher'):
        with m.life.ProcessOwner(tmp_path/'owner.json') as owner:
            m.OwnedPublisherV3(owner)(part,tmp_path/'receipt.json')
    assert json.loads((tmp_path/'owner.json').read_text())['processes']==[]
    assert part.read_bytes()==b'fixed'


def test_actual_outer_stop_reaps_nested_term_ignoring_transport_and_retains_part(tmp_path,monkeypatch):
    raw,packed,source,asset=queue_fixture(tmp_path,monkeypatch,'cancel')
    asset['browser_download_url']='http://127.0.0.1/unused'
    counter=f.gh_fixture(tmp_path,monkeypatch,source,asset,[dict(cut=8,sleep=60,ignore_term=True,child=True),{}])
    script=tmp_path/'outer-control.py'
    script.write_text('''import sys,json,subprocess
from pathlib import Path
sys.path.insert(0,ROOT)
import characterize_pcie_pll_acquisition_v3 as m
B=Path(BASE);raw=bytes.fromhex(RAW)
queue=None
try:
 with m.life.ProcessOwner(B/'outer-owner.json') as owner:
  owner.launch('native',[sys.executable,'-c','import time;time.sleep(60)'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
  queue=m.life.PartQueue(B/'parts','producer-control',['time','v(x)'],m.OwnedPublisherV3(owner),2,True,m.namespace['FLOOR'])
  queue.append(raw[:16]);queue.append(raw[16:]);queue.finish()
except BaseException as error:
 if queue is not None:(B/'retained-pending.bin').write_bytes(queue.pending)
 (B/'terminal.json').write_text(json.dumps({'error':repr(error)}))
 raise
'''.replace('ROOT',repr(str(ROOT/'scripts'))).replace('BASE',repr(str(tmp_path))).replace('RAW',repr(raw.hex())))
    with (tmp_path/'outer-control.log').open('wb') as log:
        outer=subprocess.Popen([sys.executable,str(script)],stdout=log,stderr=subprocess.STDOUT)
        deadline=time.monotonic()+8
        while time.monotonic()<deadline:
            childpath=Path(str(counter)+'.child')
            if childpath.exists():break
            if outer.poll() is not None:pytest.fail((tmp_path/'outer-control.log').read_text())
            time.sleep(.01)
        else:outer.kill();pytest.fail('Nested transport did not start')
        start=time.monotonic();outer.send_signal(signal.SIGTERM);assert outer.wait(timeout=7)!=0
        assert time.monotonic()-start<5
    partdir=tmp_path/'parts';ledger=json.loads((partdir/'parts.json').read_text())
    assert ledger['status']=='ERROR_PART_RETAINED'
    assert (partdir/asset['name']).read_bytes()==packed
    assert (tmp_path/'retained-pending.bin').read_bytes()==raw
    receipt=json.loads((partdir/'publication-00000.json').read_text())
    assert receipt['status']=='FAIL' and receipt['explicit_stop']
    for path in [tmp_path/'outer-owner.json',*partdir.glob('publication-00000.transport/*/owned-processes.json')]:
        for entry in json.loads(path.read_text())['processes']:
            assert not any(x['state']!='Z' for x in m.life.group_members(entry['process_group']))
    child=int(Path(str(counter)+'.child').read_text());identity=m.life.process_identity(child)
    assert identity is None or identity['state']=='Z'


@pytest.mark.parametrize('status,code',[('PASS_NATIVE_STREAM_FINITE_SCREEN',0),('FAIL_NATIVE_STREAM_FINITE_SCREEN',1),('ERROR_NATIVE_OR_STREAM_CAPTURE',1),('RUNNING',1)])
def test_native_cli_status_routing_is_unchanged_without_launch(tmp_path,monkeypatch,status,code):
    monkeypatch.setitem(m.namespace,'runtime',SimpleNamespace(check_runtime=lambda*a:None))
    monkeypatch.setitem(m.namespace,'run',lambda*a:{'status':status})
    monkeypatch.setattr(sys,'argv',['producer','--out',str(tmp_path/'out'),'--prefix','control','--step-ps','2.5','--reference','reference','--reference-sha','x','--prerequisites','prerequisites','--prerequisites-sha','y'])
    assert m.main()==code
