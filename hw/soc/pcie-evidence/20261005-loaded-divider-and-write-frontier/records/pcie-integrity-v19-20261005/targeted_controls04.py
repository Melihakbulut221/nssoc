"""Only the changed direct epoch case; failed full miter runs via its original test."""
from pathlib import Path
import runpy

def test_changed_epoch_case_direct(tmp_path):
    helper=runpy.run_path(str(Path.cwd()/'sw/tests/test_pcie_gen3_continuous_rx_integrity_v19.py'))
    result,record,cases,out=helper['run'](tmp_path,maximum=150,case='fault_quarantine_restart_wrap_and_backpressure')
    assert result.returncode==0 and record['tests']==dict(passed=1,failed=0,skipped=13)
    assert len(cases)==1 and cases[0].find('failure') is None
    assert 'V19_EPOCH_QUARANTINE epochs=16' in (out/'simulation.log').read_text()
