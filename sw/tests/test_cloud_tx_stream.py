# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Reject incomplete or misbound native transport without relaxing PHY gates."""
import importlib.util
from pathlib import Path
import numpy as np
import pytest
SPEC=importlib.util.spec_from_file_location('tx_stream',Path(__file__).resolve().parents[2]/'scripts/cloud_tx_stream.py')
m=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(m)
VECTORS=['v(out)','@q.x.qnpn13g2[ic]']


def raw(values=None):
    data=np.array([[0.,0.,0.],[1e-12,.25,.001],[2e-12,.5,.002]]) if values is None else values
    header=('Title: transport control\nPlotname: Transient Analysis\nFlags: real\n'
        'No. Variables: 3\nNo. Points: 3\nVariables:\n0 time time\n'
        '1 v(out) voltage\n2 i(@q.x.qnpn13g2[ic]) current\nBinary:\n')
    return header.encode()+data.astype('<f8').tobytes()


def test_all_native_values_and_current_alias(tmp_path):
    path=tmp_path/'wave.raw';path.write_bytes(raw())
    t,v,p=m.read_streamed_wave(path,VECTORS,2e-12,1e-12)
    assert list(v)==VECTORS and p['header_rows']==3 and p['complete_unmodified_rows']
    expected=np.array([[0.,0.,0.],[1e-12,.25,.001],[2e-12,.5,.002]])
    assert m.compare_complete(expected,t,v,VECTORS)['rows']==3


@pytest.mark.parametrize('fault',['truncated','extra','header_count','duplicate','renamed_device','wrong_kind','nonfinite','reversed_time','incomplete_stop','missing_vector'])
def test_reject_damaged_native_capture(tmp_path,fault):
    data=raw()
    if fault=='truncated':data=data[:-1]
    elif fault=='extra':data+=b'x'
    elif fault=='header_count':data=data.replace(b'No. Points: 3',b'No. Points: 4')
    elif fault=='duplicate':data=data.replace(b'i(@q.x.qnpn13g2[ic]) current',b'v(out) voltage')
    elif fault=='renamed_device':data=data.replace(b'@q.x.',b'@q.y.')
    elif fault=='wrong_kind':data=data.replace(b'v(out) voltage',b'v(out) current')
    elif fault=='nonfinite':data=raw(np.array([[0,0,0],[1e-12,np.nan,0],[2e-12,0,0]]))
    elif fault=='reversed_time':data=raw(np.array([[0,0,0],[2e-12,0,0],[1e-12,0,0]]))
    elif fault=='incomplete_stop':data=raw(np.array([[0,0,0],[.5e-12,0,0],[1e-12,0,0]]))
    elif fault=='missing_vector':data=data.replace(b'No. Variables: 3',b'No. Variables: 2')
    path=tmp_path/'bad.raw';path.write_bytes(data)
    with pytest.raises(AssertionError):m.read_streamed_wave(path,VECTORS,2e-12,1e-12)


@pytest.mark.parametrize('fault',['one_value','phase','row_removed','vector_removed'])
def test_reject_transport_changes(fault):
    data=np.array([[0.,0.,0.],[1e-12,.25,.001],[2e-12,.5,.002]])
    t=data[:,0].copy();v={n:data[:,i+1].copy() for i,n in enumerate(VECTORS)}
    if fault=='one_value':v[VECTORS[1]][1]+=.0001
    elif fault=='phase':t[1]+=.1e-12
    elif fault=='row_removed':data=data[:-1]
    elif fault=='vector_removed':v.pop(VECTORS[1])
    with pytest.raises(AssertionError):m.compare_complete(data,t,v,VECTORS)


def test_analysis_parameters_and_native_sources_preserved():
    vectors=['v(out)']
    deck='Example\nR1 in out 25\n.options reltol=1e-4\n.control\nsave v(out)\nalter @q.x[off] = 1\nop\nwrdata op.dat v(out)\ntran 5e-13 34e-9 0 5e-13\nwrdata wave.dat v(out)\nquit\n.endc\n.end\n'
    transformed=m.streaming_deck(deck,{'vectors':vectors})
    assert transformed=='Example\nR1 in out 25\n.options reltol=1e-4\n.tran 5e-13 34e-9 0 5e-13\n.control\nsave v(out)\nalter @q.x[off] = 1\nop\nwrdata op.dat v(out)\nset filetype=binary\nrun wave.raw\nquit\n.endc\n.end\n'
    for bad in [deck.replace('tran 5e-13','tran 5e-13\ntran 5e-13'),deck.replace('wrdata wave.dat v(out)','wrdata wave.dat v(other)')]:
        with pytest.raises(AssertionError):m.streaming_deck(bad,{'vectors':vectors})


def test_pwl_reduction_keeps_exact_source_text():
    sources=['V1 in 0 PWL(0 0 1n 1)\n','Vs s ref PWL(\n+ 0 0\n+ 2e-9 .08)\n']
    deck='Title\n'+''.join(sources)+'.tran 1p 34n\n.control\nquit\n.endc\n.end\n'
    assert m.pwl_voltage_sources(deck)==sources
    with pytest.raises(AssertionError):m.pwl_voltage_sources('No source\nR1 a 0 1\n')
    with pytest.raises(AssertionError):m.pwl_voltage_sources('Title\n'+sources[0]*2)


def test_failed_tail_never_relabels_partial_capture_as_complete(tmp_path):
    path=tmp_path/'wave.raw';path.write_bytes(raw())
    result=m.failed_capture_tail(path,m.digest(path))
    assert result['accepted']is False and result['end_s']==2e-12
    assert result['tail'][-1]['time_hex']==float(2e-12).hex()
    with pytest.raises(AssertionError):m.read_streamed_wave(path,VECTORS,34e-9,1e-12)
    with pytest.raises(AssertionError):m.failed_capture_tail(path,'0'*64)
    path.write_bytes(raw()[:-1])
    with pytest.raises(AssertionError):m.failed_capture_tail(path,m.digest(path))
