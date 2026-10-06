# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""IndependentTMAX bridge and actual byte/grid/receipt rejection controls.

Synthetic records exercise guards only; these tests never launch SPICE or
count as native electrical evidence. Native sources/oldcaptures stay frozen.
"""
from copy import deepcopy
import hashlib
import inspect
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts'))
import characterize_pcie_pll_acquisition_v4 as m
import review_pcie_pll_acquisition_v2 as review
import compare_pcie_pll_acquisition_pair_v2 as pair


def test_whole_producer_method_inverses_and_private_bindings():
    originals = dict(Meter=inspect.getsource(m.previous.namespace['Meter']),
                     startup_proof=inspect.getsource(m.base.startup_proof),
                     run=m.previous.run_source, main=m.previous.main_source)
    generated = dict(Meter=m.meter_source,startup_proof=m.startup_source,
                     run=m.run_source,main=m.main_source)
    for name, source in generated.items():
        for old,new in reversed(m.BRIDGES[name]['exact_replacements']):
            assert source.count(new)==1
            source=source.replace(new,old)
        assert source==originals[name]
        assert hashlib.sha256(source.encode()).hexdigest()==m.BRIDGES[name]['original_sha256']
    assert m.capture.__globals__ is m.namespace
    assert m.namespace['Meter'] is m.Meter
    assert m.run.__globals__ is m.namespace
    assert m.previous.namespace['Meter'] is not m.Meter
    assert m.previous.run.__globals__ is not m.namespace
    assert hashlib.sha256(m.capture_source.encode()).hexdigest()==m.base.BRIDGES['capture']['modified_sha256']


def test_frozen_physics_resource_and_independent_arithmetic_aliases():
    for n in ['measurements','acquisition','runtime','OwnedPublisherV3']:
        assert getattr(m,n) is getattr(m.previous,n)
    for n in ['native_wait','guard','FLOOR','CAP','PART_BYTES','life']:
        assert m.namespace[n] is m.previous.namespace[n]
    assert m.namespace['CAP']==50*1024**2 and m.namespace['FLOOR']==512*1024**2
    assert m.base.FREQUENCY_RELATIVE_LIMIT==100e-6 and m.base.PHASE_RANGE_LIMIT_S==50e-12
    for n in ['independent_edges','monotone_ordinals','independent_analysis','compare_independent','decode_part']:
        assert getattr(review,n) is getattr(review.previous,n)
    assert pair.compare is pair.previous.compare
    assert pair.WINDOWS==((800e-9,900e-9),(900e-9,1e-6))
    assert pair.FREQUENCY_LIMIT_PPM==100 and pair.PHASE_LIMIT_S==50e-12


def test_deck_changes_only_TMAX_and_keeps_TSTEP_and_startup_bytes():
    p=ROOT/'sw/tests/fixtures/pcie_pll_acquisition_v3/connected-loop-bench.cir'
    assert m.sha(p)=='6f31cfc4c419005b857608eb2d873d13b44c8e53e0328517cb9eefeb373b55c4'
    raw=p.read_text()
    old=m.previous.stream_deck(raw,2.5e-12,1e-6)
    new=m.stream_deck(raw,2.5e-12,1e-6)
    assert old.count('.tran 2.5e-12 1e-06 0 2.5e-12\n')==1
    assert new==old.replace('.tran 2.5e-12 1e-06 0 2.5e-12\n','.tran 2.5e-12 1e-06 0 1.25e-12\n')
    assert 'uic' not in new.lower()


@pytest.mark.parametrize('step,stop',[(5e-12,1e-6),(1.25e-12,1e-6),(2.5e-12,400e-9),(2.5e-12,0)])
def test_wrong_step_or_duration_rejected_before_deck_generation(step,stop):
    with pytest.raises(ValueError,match='Fixed2.5ps'):
        m.stream_deck('not a deck',step,stop)


@pytest.mark.parametrize('delta,passed',[(1.25e-12,True),(1.875e-12,False),(2.5e-12,False)])
def test_actual_raw_row_meter_uses_new_ceiling_not_TSTEP(monkeypatch,delta,passed):
    # A real ndarray traverses the wholeMeter.push implementation. The synthetic
    # graph has zero devices; only grid boundary/error handling is under test.
    monkeypatch.setitem(m.namespace,'n',SimpleNamespace(safety=lambda*d:dict(model_geometry_range_issues=[],all_device_bounds=[])))
    config=dict(step_s=2.5e-12,max_step_s=1.25e-12,stop_s=2.5e-12,window_s=[0,2.5e-12])
    meter=m.Meter(['time','v(x)'],[],config,observations=['time','v(x)'])
    block=np.asarray([[0.,0.],[delta,1.]])
    if passed:
        meter.push(block)
        assert meter.count==2 and meter.max_dt==delta
    else:
        with pytest.raises(ValueError,match='Native maximum time step'):
            meter.push(block)


@pytest.mark.parametrize('tran',[
 '.tran 2.5e-12 1e-06 0 2.5e-12',
 '.tran 1.25e-12 1e-06 0 1.25e-12',
 '.tran 2.5e-12 4e-07 0 1.25e-12',
 '.tran 2.5e-12 1e-06 0 1.25e-12\n.tran 2.5e-12 1e-06 0 1.25e-12'])
def test_startup_rejects_wrong_or_duplicate_actual_analysis_before_native_proof(tmp_path,tran):
    (tmp_path/'capture').mkdir();(tmp_path/'capture/capture.json').write_text('{"columns":[]}')
    (tmp_path/'bench.cir').write_text(tran+'\n');(tmp_path/'run.log').write_text('never trusted\n')
    with pytest.raises(ValueError,match='Exact stream native analysis'):
        m.startup_proof(tmp_path,{})


def test_startup_keeps_TSTEP_for_warning_estimate_and_strict_OP_parser(tmp_path,monkeypatch):
    (tmp_path/'capture').mkdir();(tmp_path/'capture/capture.json').write_text('{"columns":[1,2]}')
    (tmp_path/'bench.cir').write_text('.tran 2.5e-12 1e-06 0 1.25e-12\n')
    (tmp_path/'run.log').write_text('literal retained log\n');(tmp_path/'execution.json').write_text('{"returncode":0}')
    seen=[]
    def classify(log,columns,step,stop,ng,code):
        seen.append((log,columns,step,stop,ng,code));return 'clean',[]
    def strict(folder,prior,cleaned):
        assert folder==tmp_path and prior=={'bound':'prior'} and cleaned=='clean'
        return dict(zero_source_op=True)
    ns=m.startup_namespace
    monkeypatch.setitem(ns,'classify_advisory',classify)
    monkeypatch.setitem(ns,'namespace',dict(_strict_startup=strict))
    monkeypatch.setitem(ns,'n',SimpleNamespace(common=SimpleNamespace(sha=lambda p:'frozen'),NG='native'))
    monkeypatch.setitem(ns,'retained_op_proof',lambda log,capture:{'retained_plot':'op1_only'})
    q=m.startup_proof(tmp_path,{'bound':'prior'})
    assert seen==[('literal retained log\n',2,2.5e-12,1e-6,'frozen',0)]
    assert q['zero_source_op'] and q['strict_numerical_diagnostics_pass'] and not q['original_log_modified']


def test_review_whole_method_bridges_and_exact_private_producer():
    for name,ledger in review.BRIDGES.items():
        old=inspect.getsource(getattr(review.previous,name));new=old
        for a,b in ledger['exact_replacements']:
            assert new.count(a)==1;new=new.replace(a,b)
        assert hashlib.sha256(new.encode()).hexdigest()==ledger['modified_sha256']
        for a,b in reversed(ledger['exact_replacements']):
            assert new.count(b)==1;new=new.replace(b,a)
        assert new==old
    assert review.review.__globals__['producer'] is m
    assert review.review.__globals__['bind_completed_capture'] is review.bind_completed_capture
    assert review.previous.review.__globals__['producer'] is not m


def edges(offset=250e-12,frequency=1e8):
    ref=[14e-9+i/1e8 for i in range(99)]
    return dict(reference_edges_s=ref,feedback_edges_s=[14e-9+i/frequency+offset for i in range(99)],reference_ordinals=list(range(99)))


@pytest.mark.parametrize('offset,passed',[(260e-12,True),(301e-12,False),(945e-12,False)])
def test_raw_phase_difference_stays_required_even_for_zero_span(offset,passed):
    a,b=edges(),edges(offset);before=deepcopy((a,b));r=pair.compare(a,b)
    assert r['passed'] is passed and (a,b)==before
    assert all(x['checks']['both_individual_windows_pass'] for x in r['windows'])


def test_individual_frequency_pass_cannot_hide_bad_pair():
    r=pair.compare(edges(frequency=1e8*(1+80e-6)),edges(frequency=1e8*(1-80e-6)))
    assert not r['passed']
    assert all(x['checks']['both_individual_windows_pass'] for x in r['windows'])
    assert all(not x['checks']['frequency_difference_100ppm'] for x in r['windows'])


@pytest.mark.parametrize('fault',[None,'wrong_review_method','native_fail','raw_hash','source_bytes','output_bytes','numerical_warning','one_device_failed'])
def test_tight_capture_receipt_rejects_actual_file_or_predicate_corruption(tmp_path,fault):
    folder=tmp_path/'capture';folder.mkdir()
    model=tmp_path/'model';model.write_text('synthetic binding control\n')
    output=folder/'output';output.write_text('synthetic raw receipt output\n')
    reviewer=ROOT/'scripts/review_pcie_pll_acquisition_v2.py'
    if fault=='wrong_review_method':reviewer=ROOT/'scripts/review_pcie_pll_acquisition_v1.py'
    r=dict(status='PASS_NATIVE_STREAM_FINITE_SCREEN',measurement=dict(passed=True),
           safety=dict(passed=True,all_device_bounds=[dict(passed=True)for _ in range(539)]),devices=[{}for _ in range(539)],
           strict_numerical_diagnostics_pass=True,rows=2,values=4,columns=['time','fixture'],
           inputs={str(model):pair.pin(model)},outputs={output.name:pair.pin(output)},raw_sha256='raw',canonical_payload_sha256='payload')
    q=dict(status='PASS_LOSSLESS_AUTHOR_REPLAY_AND_INDEPENDENT_ACQUISITION_ARITHMETIC',
           native_authoritative_status=r['status'],all539_author_safety_records_exact=True,
           rows=2,values=4,full_raw_sha256='raw',canonical_payload_sha256='payload',independent=dict(passed=True),agreement=dict(all_predicates_exact=True),
           inputs={str(model):pair.pin(model),str(reviewer):pair.pin(reviewer)})
    if fault=='native_fail':r['status']='FAIL_NATIVE_STREAM_FINITE_SCREEN'
    if fault=='raw_hash':q['full_raw_sha256']='corrupt'
    if fault=='numerical_warning':r['strict_numerical_diagnostics_pass']=False
    if fault=='one_device_failed':r['safety']['all_device_bounds'][237]['passed']=False
    native=folder/'result.json';native.write_text(json.dumps(r));q['native_result']=pair.pin(native)
    receipt=tmp_path/'review.json';receipt.write_text(json.dumps(q))
    if fault=='source_bytes':model.write_text('changed actual source\n')
    if fault=='output_bytes':output.write_text('changed actual output\n')
    if fault is None:
        rr,qq=pair.load_tight_verified(folder,receipt);assert rr==r and qq==q
    else:
        with pytest.raises(ValueError):pair.load_tight_verified(folder,receipt)


@pytest.mark.parametrize('fault',[None,'frequency_limit','phase_limit','phase_alignment','TSTEP','missing_entry','baseline_bytes','review_bytes','declaration_bytes','baseline_wrong_step'])
def test_actual_prerequisite_files_and_predeclared_limits_fail_closed(tmp_path,monkeypatch,fault):
    files={name:tmp_path/(name+'.json')for name in ['parent','baseline','baseline_review','declaration']}
    for name,p in files.items():p.write_text(json.dumps({'synthetic':name}))
    bs,rs=m.sha(files['baseline']),m.sha(files['baseline_review'])
    monkeypatch.setattr(m,'BASELINE_SHA',bs);monkeypatch.setattr(m,'BASELINE_REVIEW_SHA',rs)
    d=dict(schema='PLL_RETAINED_TSTEP_MAXSTEP_REFINEMENT_V1',first_result_sha256=bs,first_full_review_sha256=rs,
           TSTEP_s=2.5e-12,first_TMAX_s=2.5e-12,second_TMAX_s=1.25e-12,stop_s=1e-6,
           windows_s=[[800e-9,900e-9],[900e-9,1e-6]],frequency_difference_limit_ppm=100.,matched_phase_limit_s=50e-12,
           phase_alignment_or_offset_removal=False,previous_5ps_2p5ps_pair_status='FAIL_FINITE_NOMINAL_TIMESTEP_SCREEN')
    changes={'frequency_limit':('frequency_difference_limit_ppm',1000.),'phase_limit':('matched_phase_limit_s',1e-9),
             'phase_alignment':('phase_alignment_or_offset_removal',True),'TSTEP':('TSTEP_s',1.25e-12)}
    if fault in changes:k,v=changes[fault];d[k]=v
    files['declaration'].write_text(json.dumps(d))
    spec={n:dict(path=str(p),sha256=m.sha(p))for n,p in files.items()}
    if fault=='missing_entry':del spec['baseline_review']
    gate=tmp_path/'gate.json';gate.write_text(json.dumps(spec))
    for mode,name in [('baseline_bytes','baseline'),('review_bytes','baseline_review'),('declaration_bytes','declaration')]:
        if fault==mode:files[name].write_text('changed actual file afterpin\n')
    calls=[]
    def saved(folder,reviewer):
        calls.append((folder,reviewer))
        assert folder==tmp_path and reviewer==str(files['baseline_review'])
        return dict(config=dict(step_s=5e-12 if fault=='baseline_wrong_step'else2.5e-12,stop_s=1e-6),devices=['synthetic539scope'],outputs={}),dict(inputs={})
    monkeypatch.setattr(m.pair,'load_verified',saved)
    monkeypatch.setattr(m.previous,'prerequisites',lambda *args:dict(paths=[str(files['parent'])]))
    if fault is None:
        q=m.prerequisites(gate,m.sha(gate),2.5e-12,{'devices':['synthetic539scope']})
        assert q['manifest']==spec and str(files['declaration'])in q['paths'] and len(calls)==1
    else:
        with pytest.raises(ValueError):m.prerequisites(gate,m.sha(gate),2.5e-12,{'devices':['synthetic539scope']})


@pytest.mark.parametrize('status,code',[('PASS_NATIVE_STREAM_FINITE_SCREEN',0),('FAIL_NATIVE_STREAM_FINITE_SCREEN',1),('ERROR_NATIVE_OR_STREAM_CAPTURE',1)])
def test_cli_fixed_TSTEP_and_actual_status_routing(tmp_path,monkeypatch,status,code):
    calls=[]
    monkeypatch.setitem(m.namespace,'runtime',SimpleNamespace(check_runtime=lambda*a:None))
    def run(*args):calls.append(args);return dict(status=status)
    monkeypatch.setitem(m.namespace,'run',run)
    monkeypatch.setattr(sys,'argv',['producer','--out',str(tmp_path/'out'),'--prefix','fixture','--step-ps','2.5','--reference','ref','--reference-sha','x','--prerequisites','gate','--prerequisites-sha','y'])
    assert m.main()==code
    assert calls[0][2:4]==(2.5e-12,1e-6)


@pytest.mark.parametrize('step',['5','1.25'])
def test_cli_cannot_change_startup_TSTEP(step,tmp_path,monkeypatch):
    monkeypatch.setitem(m.namespace,'runtime',SimpleNamespace(check_runtime=lambda*a:None))
    monkeypatch.setitem(m.namespace,'run',lambda*a:pytest.fail('InvalidTSTEP reached native run'))
    monkeypatch.setattr(sys,'argv',['producer','--out',str(tmp_path/'out'),'--prefix','fixture','--step-ps',step,'--reference','ref','--reference-sha','x','--prerequisites','gate','--prerequisites-sha','y'])
    with pytest.raises(SystemExit)as ex:m.main()
    assert ex.value.code==2
