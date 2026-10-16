# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
import importlib.util,struct
from pathlib import Path
import pytest
P=Path(__file__).resolve().parents[2]/'scripts/cloud_native_progress.py'
spec=importlib.util.spec_from_file_location('native_progress',P);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
HEADER=b'Title: progress fixture\nPlotname: Transient Analysis\nFlags: real\nNo. Variables: 2\nNo. Points: 0\nVariables:\n0 time time\n1 v(out) voltage\nBinary:\n'

def write(path,times):
    path.write_bytes(HEADER+b''.join(struct.pack('<dd',t,.2) for t in times))

def test_pending_and_partial_header_are_not_complete(tmp_path):
    p=tmp_path/'wave.raw';assert m.progress(p,2)['state']=='raw_not_created'
    p.write_bytes(b'Title: pending');r=m.progress(p,2)
    assert r['state']=='header_incomplete_or_oversized' and not r['complete'] and not r['accepted']

def test_partial_row_is_not_counted_as_native_time(tmp_path):
    p=tmp_path/'wave.raw';write(p,[0.,1e-12]);p.write_bytes(p.read_bytes()+struct.pack('<d',99.))
    r=m.progress(p,2)
    assert r['last_written_time_s']==1e-12 and r['complete_binary_rows_observed']==2
    assert r['trailing_partial_row_bytes']==8 and not r['complete'] and not r['accepted']

@pytest.mark.parametrize('times',[[0.,float('nan')],[0.,float('inf')],[0.,0.],[1e-12,2e-12],[0.,2e-12,1e-12]])
def test_bad_observed_timestamps_are_rejected(tmp_path,times):
    p=tmp_path/'wave.raw';write(p,times)
    with pytest.raises(AssertionError):m.progress(p,2)

def test_column_mismatch_is_rejected(tmp_path):
    p=tmp_path/'wave.raw';write(p,[0.,1e-12])
    with pytest.raises(AssertionError):m.progress(p,3)

def test_complete_looking_prefix_never_proves_full_capture(tmp_path):
    p=tmp_path/'wave.raw';write(p,[0.,1e-12,2e-12])
    r=m.progress(p,2)
    assert r['last_written_time_s']==2e-12 and r['not_all_rows_examined']
    assert r['status']=='DIAGNOSTIC_INCOMPLETE_CAPTURE_ONLY' and not r['complete'] and not r['accepted']
