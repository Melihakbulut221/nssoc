"""Only direct public case17 changes; the full miter and all its faults rerun."""
from pathlib import Path
import runpy
R=Path.cwd()
def test_changed_cache_epoch_direct_positive(tmp_path):
    m=runpy.run_path(str(R/'sw/tests/test_pcie_gen3_continuous_rx_integrity_v22.py'))
    case='cache_fault_write_and_new_epoch_reuse'
    result,record,cases,out=m['run'](tmp_path,case=case)
    assert result.returncode==0 and record['tests']==dict(passed=1,failed=0,skipped=16),record
    assert len(cases)==1 and cases[0].find('failure') is None
    assert 'V22_CACHE_QUARANTINE epochs=8' in (out/'simulation.log').read_text()
