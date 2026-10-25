# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
import gzip
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import signal
import sys
import time

import pytest

S=Path(__file__).resolve().parents[2]/'scripts';sys.path.insert(0,str(S))
spec=importlib.util.spec_from_file_location('power_overlay',S/'diagnose_pcie_bank_power_overlay_v2.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)


def wire(text='R0 P000 T0000 1\nC0 T0000 sub 1f'):
    return '.subckt bank_wires P000 T0000\n'+text+'\n.ends\n'


def test_positive_exact_wire_parser():
    ports,rows=m.wire_records(wire(),{'R':1,'C':1})
    assert ports==['P000','T0000'] and rows[0]==['R0','P000','T0000','1']


@pytest.mark.parametrize('body',['R0 P000 T0000 -1\nC0 T0000 sub 1f','R0 P000 P000 1\nC0 T0000 sub 1f',
                                 'R0 P000 T0000 1\nR0 P000 T0000 1\nC0 T0000 sub 1f',
                                 'R0 P000 T0000 1','R0 P000 T0000 1\nC0 T0000 sub NaN'])
def test_invalid_missing_duplicate_or_negative_physical_records_reject(body):
    with pytest.raises(ValueError):m.wire_records(wire(body),{'R':1,'C':1})


def geometry():
    rows=[]
    for i in range(804):
        label=f'P{i:03d}' if i<56 else f'T{i:04d}'
        rows.append(dict(label=label,wire_component=i%128+1,
                         kind='PUBLIC_PORT_REFERENCE' if i<56 else 'INTRINSIC_DEVICE_TERMINAL_REFERENCE',detail={'name':f'PORT{i}'}))
    records=[]
    for i in range(128,804):records.append([f'R{i}',rows[i]['label'],rows[i-128]['label'],'1'])
    records.append(['C0',rows[0]['label'],'sub','1f'])
    return {'anchors':rows},[r['label'] for r in rows],records


def test_complete804_actual_anchor_graph_without_alias_union():
    a,p,r=geometry();assert len(m.physical_wire_contract(a,p,r))==56


@pytest.mark.parametrize('fault',['open','short','missing_port','unanchored_R','unknown_C'])
def test_actual_physical_anchor_graph_mutations_reject(fault):
    a,p,r=geometry()
    if fault=='open':r.pop(0)
    elif fault=='short':r.append(['Rshort',p[0],p[1],'1'])
    elif fault=='missing_port':p.pop()
    elif fault=='unanchored_R':r.append(['Rfloat','bad1','bad2','1'])
    else:r.append(['Cbad',p[0],'unknown','1f'])
    with pytest.raises(ValueError):m.physical_wire_contract(a,p,r)


def test_original_metadata_identity_cannot_be_relabelled():
    a={'anchors':[], 'unmodeled_body_well_terminals':[{'body':'finite'}], 'actual_metal_terminals':748,'body_well_terminals':313}
    b=json.loads(json.dumps(a));b['unmodeled_body_well_terminals'][0]['body']='shorted'
    with pytest.raises(ValueError,match='terminal/body'):m.compose({},b,a,'','')


def test_frozen_external_deck_metrology_and_old_sources():
    assert m.prior.deck.__module__=='diagnose_pcie_bank_powered_v1'
    assert m.prior.wave_measure.__module__=='diagnose_pcie_bank_powered_v1'
    assert hashlib.sha256(Path(m.prior.__file__).read_bytes()).hexdigest()==m.PRIOR_SHA
    assert hashlib.sha256(Path(m.h.__file__).read_bytes()).hexdigest()==m.prior.METHOD_SHA
    assert (m.prior.BEGIN,m.prior.STOP,m.prior.STEP)==(2e-9,4e-9,2e-12)


@pytest.mark.parametrize('behavior',['wave','early_exit','save_error'])
def test_actual_owned_native_lifecycle_fifo_abort_and_exception_cleanup(tmp_path,monkeypatch,behavior):
    root=tmp_path/'case';root.mkdir();exe=tmp_path/'fake_native'
    body='''import os,signal,time
signal.signal(signal.SIGTERM,signal.SIG_IGN)
'''
    if behavior=='wave':body+='with open("wave.fifo","wb") as f:f.write(b"time v\\n0 1\\n")\n'
    elif behavior=='early_exit':body+='raise SystemExit(7)\n'
    else:body+='open("ready","w").write("native")\nwhile True:time.sleep(.01)\n'
    exe.write_text('#!'+sys.executable+'\n'+body);exe.chmod(0o700)
    monkeypatch.setattr(m,'owned_size',lambda p:0);monkeypatch.setattr(m.prior,'shared_free',lambda:1024**3)
    row={'stream':{},'resources':[]}
    def save():
        if behavior=='save_error':
            until=time.monotonic()+2
            while not (root/'ready').exists() and time.monotonic()<until:time.sleep(.01)
            assert (root/'ready').exists()
            raise RuntimeError('actual persistence failure')
    start=time.monotonic()
    if behavior=='save_error':
        with pytest.raises(RuntimeError,match='persistence'):m.run_native(root,exe,tmp_path,save,row)
    else:m.run_native(root,exe,tmp_path,save,row)
    assert time.monotonic()-start<12 and not (root/'wave.fifo').exists()
    assert row['returncode'] is not None
    with pytest.raises(ProcessLookupError):os.kill(row['pid'],signal.SIGCONT)
    if behavior=='wave':assert gzip.decompress((root/'wave.dat.gz').read_bytes())==b'time v\n0 1\n'
    elif behavior=='early_exit':assert row['returncode']==7 and row['stream']['raw_bytes']==0

    if behavior=='save_error':assert row['returncode']==-signal.SIGKILL
