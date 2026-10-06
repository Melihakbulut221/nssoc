# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Native graph composition, real fault paths and owned terminal lifecycle."""
import copy
import gzip
import json
import os
from pathlib import Path
import signal
import sys
import types

import pytest

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts'))
import characterize_pcie_vco_v6_divider_cap24_v1_wire_v1 as m


@pytest.fixture(autouse=True)
def exact_vco_fixture(monkeypatch):
    monkeypatch.setattr(m.core, 'HYBRID', Path(__file__).parent/'fixtures/pcie_vco_v6_feedback_v1')


def fixture_inputs():
    f=m.DIVIDER/'inputs'
    out={}
    for key,name in [('anchors','anchors.json'),('devices','device-location-geometry.json'),('geometry','wire-component-geometry.json'),('native','extracted.cir'),('wires','wires.spice')]:
        data=gzip.decompress((f/(name+'.gz')).read_bytes())
        assert m.core.hashlib.sha256(data).hexdigest()==m.builder.PINS[key]
        out[key]=json.loads(data) if name.endswith('.json') else data.decode()
    out['tech']={'ptap1_raspec':'0.980n','ptap1_rpspec':'0.980m'}
    return out


def compose(x):
    return m.builder.compose(x['anchors'],x['devices'],x['geometry'],x['native'],x['wires'],x['tech'])


def test_actual_public91_device205_anchor_model_is_exactly_reproducible():
    text,comp=compose(fixture_inputs())
    assert text==(m.DIVIDER/'hybrid-open.spice').read_text()
    actual=json.loads((m.DIVIDER/'composition.json').read_text())
    assert all(actual[k]==v for k,v in comp.items())
    assert len(comp['records'])==91 and comp['body_well_terminals']==85
    assert comp['finite_contacts']==18 and comp['wire_components']==37
    assert comp['full_pex_qualified'] is False
    assert sum(t['node']=='BODY_SUBSTRATE' for r in comp['records'] for t in r['terminals'])==85
    assert all(t['anchor'] is None for r in comp['records'] for t in r['terminals'] if t['node']=='BODY_SUBSTRATE')


@pytest.mark.parametrize('fault,diagnostic',[
    ('missing_contact','Native device ID census'),
    ('wrong_hbt_terminal','Native terminal identity/order'),
    ('wrong_hbt_geometry','Native geometry/value'),
    ('lost_wire','Wire element census'),
    ('body_on_metal','Body equivalence changed'),
    ('wrong_anchor','Physical reference point changed'),
])
def test_actual_native_input_damage_is_rejected(fault,diagnostic):
    x=fixture_inputs()
    if fault=='missing_contact':
        assert sum(line.startswith('R$91 ') for line in x['native'].splitlines())==1
        x['native']='\n'.join(line for line in x['native'].splitlines() if not line.startswith('R$91 '))+'\n'
    elif fault=='wrong_hbt_terminal':
        lines=x['native'].splitlines();i=next(i for i,line in enumerate(lines) if line.startswith('Q$1 '));w=lines[i].split();w[1],w[2]=w[2],w[1];lines[i]=' '.join(w);x['native']='\n'.join(lines)+'\n'
    elif fault=='wrong_hbt_geometry':
        lines=x['native'].splitlines();i=next(i for i,line in enumerate(lines) if line.startswith('Q$1 '));assert 'Nx=4' in lines[i];lines[i]=lines[i].replace('Nx=4','Nx=5');x['native']='\n'.join(lines)+'\n'
    elif fault=='lost_wire':
        lines=x['wires'].splitlines();i=next(i for i,line in enumerate(lines) if line.startswith('R'));del lines[i];x['wires']='\n'.join(lines)+'\n'
    elif fault=='body_on_metal':
        x['anchors']['unmodeled_body_well_terminals'][0]['native_cluster']=8
    else:
        a=next(a for a in x['anchors']['anchors'] if a['kind']=='INTRINSIC_DEVICE_TERMINAL_REFERENCE');a['point_dbu'][0]+=1
    with pytest.raises(ValueError,match=diagnostic):compose(x)


@pytest.mark.parametrize('fault',['missing_contact','wire_value','body_short','terminal'])
def test_actual_output_damage_is_rejected(fault):
    expected=(m.DIVIDER/'hybrid-open.spice').read_text();lines=expected.splitlines()
    if fault=='missing_contact':
        i=next(i for i,line in enumerate(lines) if ' ptap1 ' in line);del lines[i]
    elif fault=='wire_value':
        i=next(i for i,line in enumerate(lines) if line.startswith('R'));w=lines[i].split();w[-1]='1';lines[i]=' '.join(w)
    elif fault=='body_short':
        i=next(i for i,line in enumerate(lines) if line.startswith('XD'));lines[i]=lines[i].replace('BODY_SUBSTRATE','AVSS')
    else:
        i=next(i for i,line in enumerate(lines) if line.startswith('XD'));w=lines[i].split();w[1],w[2]=w[2],w[1];lines[i]=' '.join(w)
    with pytest.raises(ValueError,match='contract changed'):m.builder.verify_output('\n'.join(lines),expected)


@pytest.mark.parametrize('vctrl,fault',[(.6,''),(.85,''),(.6,'disconnect_divider_clock'),(.6,'wrong_feedback_modulus')])
def test_all455_devices_and_native_boundaries_are_observed(vctrl,fault):
    c,rows,texts=m.config(vctrl,fault)
    old_c,old_rows,old_texts=m.previous.config(vctrl,fault)
    assert len(rows)==455
    assert [r for r in rows if not r['path'].startswith('xchain.xdiv.')]==[r for r in old_rows if not r['path'].startswith('xchain.xdiv.')]
    assert texts['hybrid-open.spice']==old_texts['hybrid-open.spice']
    assert sum(r['model']=='npn13g2' for r in rows)==64
    assert sum(r['model'] in ('ptap1','ntap1') for r in rows)==31
    assert c['wire_resistors']==1271 and c['wire_capacitors']==1414
    for key in ['window_s','stop_s','step_s','minimum_states']:assert c[key]==old_c[key]
    assert c['fixture'][:-2]==old_c['fixture']
    assert c['fixture'][-2:]==['VDIVBODY div_body_substrate 0 0','VDIVWREF div_wire_cref 0 0']
    assert sum(net=='div_body_substrate' for r in rows if r['path'].startswith('xchain.xdiv.') for net in r['nets'])==85
    vectors=m.n.vectors(rows,c['extra_vectors'])
    assert set(m.OBS[1:])<=set(vectors)
    meter=m.Meter(['time',*vectors],rows,c)
    assert len(meter.contacts)==31 and len(meter.rows)==424
    assert set(r['path'] for r in meter.contacts+meter.rows)==set(r['path'] for r in rows)
    deck=m.deck(c,rows,texts)
    assert deck.count('echo NSSOC_NATIVE_FLAG_BEGIN ')==64
    assert '.tran 5e-12 3.4e-08 0 5e-12' in deck
    assert 'uic' not in deck.lower() and 'gmin' not in deck.lower()
    assert 'op\nwrite op.raw all\nrun stream.fifo' in deck


def test_real_faults_are_single_connections_with_both_models_retained():
    _,gold,good=m.config()
    for fault in ('disconnect_divider_clock','wrong_feedback_modulus'):
        c,rows,texts=m.config(fault=fault)
        changed=[name for name in texts if texts[name]!=good[name]]
        assert len(changed)==1
        if fault=='disconnect_divider_clock':
            # Real wire-port fault changes top connection, not internal anchors.
            assert rows==gold
            assert texts[changed[0]]==good[changed[0]].replace('XDIV avss clkn clkp','XDIV avss clkp clkp')
            assert 'v(clkn)' in c['extra_vectors']
        else:
            assert rows!=gold
            assert texts[changed[0]]==good[changed[0]].replace('XD2N q2b q1 q0 d2b','XD2N q2b q1 q1 d2b')
        assert texts['divider-hybrid-open.spice']==good['divider-hybrid-open.spice']


@pytest.mark.parametrize('before,after',[
    ('sub div_body_substrate div_wire_cref','sub avss avss'),
    ('XDIV avss clkn clkp','XDIV avss qp qn'),
    ('XFB qp qn','BIDEAL qp avss V=1\nXFB qp qn'),
])
def test_missing_or_hidden_ideal_boundaries_reject(before,after):
    text=m.CHAIN.read_text();assert text.count(before)==1
    with pytest.raises(ValueError,match='topology'):m.topology(text.replace(before,after))


def test_source_correspondence_rejects_wrong_original_device_parameter():
    _,original,texts=m.previous.config()
    rows,_=m.reference_rows(original,texts)
    row=next(r for r in rows if r['path']=='xchain.xdiv.xfirst.xup')
    row['params']['l']='6.4u'
    with pytest.raises(ValueError,match='geometry/value'):
        m.source_correspondence(json.loads((m.DIVIDER/'composition.json').read_text()),json.loads((m.DIVIDER/'source-native-bijection.json').read_text()),rows)


def test_unchanged_collector_measurement_and_native_limits_keep_private_globals():
    for name in ['capture','measurement','native_limit','main']:
        assert m._scope[name].__code__ is m.previous._scope[name].__code__
        assert m._scope[name].__defaults__==m.previous._scope[name].__defaults__
        assert m._scope[name].__closure__==m.previous._scope[name].__closure__
        assert m._scope[name].__globals__ is m._scope
    assert m._scope['Meter'] is m.Meter and m._scope['config'] is m.config
    assert m._scope['FLOOR']==512*1024**2 and m._scope['OWN_LIMIT']==80*1024**2
    assert m.previous._scope['Meter'] is not m.Meter


@pytest.fixture
def fake_native(tmp_path,monkeypatch):
    """Actual short FIFO producer; data semantics isolated from lifecycle controls."""
    executable=tmp_path/'producer'
    executable.write_text('#!/usr/bin/env python3\nfrom pathlib import Path\nwith open("stream.fifo","wb",buffering=0) as f:f.write(b"real child payload")\n')
    executable.chmod(0o700)
    scope=m._scope
    monkeypatch.setitem(scope,'n',types.SimpleNamespace(NG=executable,common=m.n.common))
    monkeypatch.setitem(scope,'capture',lambda source,*args: {'payload':source.read().decode()})
    monkeypatch.setitem(scope,'RECEIPT_RESERVE',0)
    monkeypatch.setitem(scope,'guard',m._scope['guard'])
    # Guard ownership is the actual current fixture; no prior native paths included.
    monkeypatch.setattr(m.physical,'owned_size',lambda p:sum(x.stat().st_size for x in p.rglob('*') if x.is_file()))
    return executable


def test_actual_healthy_short_fifo_producer_is_closed(tmp_path,fake_native):
    r=m._scope['run_native'](tmp_path,[],{})
    assert r['payload']=='real child payload'
    owner=json.loads((tmp_path/'owned-processes.json').read_text())
    assert owner['processes'][0]['status']=='REAPED_NO_LIVE_MEMBERS'
    assert owner['elapsed_watchdog_seconds'] is None


@pytest.mark.parametrize('boundary',['complete','teardown'])
def test_actual_sigterm_at_completion_boundaries_is_not_lost(tmp_path,fake_native,monkeypatch,boundary):
    Base=m.life.ProcessOwner
    class BoundaryOwner(Base):
        terminal_saves=0
        def save(self):
            super().save()
            if any(e['record']['status']=='REAPED_NO_LIVE_MEMBERS' for e in self.entries):
                self.terminal_saves+=1
                if boundary=='teardown' and self.terminal_saves==2:os.kill(os.getpid(),signal.SIGTERM)
        def complete(self,process):
            result=super().complete(process)
            if boundary=='complete':os.kill(os.getpid(),signal.SIGTERM)
            return result
    monkeypatch.setitem(m._scope,'life',types.SimpleNamespace(ProcessOwner=BoundaryOwner))
    with pytest.raises(RuntimeError,match='SIGTERM'):m._scope['run_native'](tmp_path,[],{})
    owner=json.loads((tmp_path/'owned-processes.json').read_text())
    assert owner['processes'][0]['status']=='REAPED_NO_LIVE_MEMBERS'


def test_actual_terminal_fast_producer_resource_overflow_rejects(tmp_path,fake_native,monkeypatch):
    fake_native.write_text(fake_native.read_text()+'Path("actual-two-MiB.bin").write_bytes(b"X"*(2*1024**2))\n')
    monkeypatch.setitem(m._scope,'OWN_LIMIT',1024**2)
    with pytest.raises(ValueError,match='Own80MiB'):m._scope['run_native'](tmp_path,[],{})
    assert (tmp_path/'actual-two-MiB.bin').stat().st_size==2*1024**2
    owner=json.loads((tmp_path/'owned-processes.json').read_text())
    assert owner['status']=='CANCELLED'


def test_authoritative_v8_reference_changes_only_two_coupling_mims():
    _, original, texts=m.previous.config()
    rows, reference=m.reference_rows(original,texts)
    old={r['path']:r for r in original if r['path'].startswith('xchain.xdiv.')}
    assert len(rows)==73 and reference==m.REFERENCE.read_text()
    changed={r['path'] for r in rows if r!=old[r['path']]}
    assert changed=={'xchain.xdiv.xcp','xchain.xdiv.xcn'}
    for row in rows:
        expected=old[row['path']]
        if row['path'] in changed:expected=dict(expected,params={'w':'24u','l':'24u'})
        assert row==expected


@pytest.mark.parametrize('name',['xchain.xdiv.xcp','xchain.xdiv.xcn'])
def test_cap24_reference_rollback_rejects_actual_native24_geometry(name):
    _, original, texts=m.previous.config()
    rows,_=m.reference_rows(original,texts)
    row=next(r for r in rows if r['path']==name)
    assert row['params']=={'w':'24u','l':'24u'}
    row['params']['w']='20u'
    with pytest.raises(ValueError,match='geometry/value'):
        m.source_correspondence(json.loads((m.DIVIDER/'composition.json').read_text()),json.loads((m.DIVIDER/'source-native-bijection.json').read_text()),rows)
