# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Immutable evidence publication refuses replacement and broken readbacks."""
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

import pytest

ROOT=Path(__file__).resolve().parents[2]


def load():
    spec=importlib.util.spec_from_file_location('publisher',ROOT/'scripts/publish_pcie_native_capture_v2.py')
    m=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


@pytest.mark.parametrize('fault', ['none','size','digest','state','duplicate','authenticated','anonymous','local_change'])
def test_existing_assets_are_immutable_and_both_downloads_checked(tmp_path,monkeypatch,fault):
    m=load();p=tmp_path/'capture.bin';p.write_bytes(b'actual finite capture\x00\xff')
    out=tmp_path/'receipt.json';h=hashlib.sha256(p.read_bytes()).hexdigest()
    expected={'bytes':p.stat().st_size,'sha256':h}
    asset={'id':123,'name':p.name,'size':expected['bytes'],'digest':'sha256:'+h,'state':'uploaded','browser_download_url':'https://example.invalid/capture'}
    if fault=='size':asset['size']+=1
    if fault=='digest':asset['digest']='sha256:'+'0'*64
    if fault=='state':asset['state']='new'
    calls=[]
    def api(path):
        calls.append(path)
        return {'assets':[asset,asset] if fault=='duplicate' else [asset]}
    def auth(_):
        if fault=='local_change':p.write_bytes(b'changed')
        return {**expected,'sha256':'0'*64} if fault=='authenticated' else expected
    def anon(_):
        return {**expected,'bytes':0} if fault=='anonymous' else expected
    def no_mutation(*args,**kwargs):
        pytest.fail('Existing asset must never be uploaded or replaced')
    monkeypatch.setattr(m,'api',api);monkeypatch.setattr(m,'authenticated',auth);monkeypatch.setattr(m,'anonymous',anon)
    monkeypatch.setattr(m.subprocess,'run',no_mutation)
    monkeypatch.setattr(sys,'argv',['publish','--tag','explicit-finite-release','--out',str(out),str(p)])
    result=m.main();r=json.loads(out.read_text())
    assert calls==['releases/tags/explicit-finite-release']
    assert r['tag']=='explicit-finite-release' and r['physical_acceptance'] is False
    assert result==(fault!='none')
    assert r['status']==('PASS_IMMUTABLE_RELEASE_ROUNDTRIPS' if fault=='none' else 'FAIL')
    assert len(r['assets'])==(1 if fault=='none' else 0)
