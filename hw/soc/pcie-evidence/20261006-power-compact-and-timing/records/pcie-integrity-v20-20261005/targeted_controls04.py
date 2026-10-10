"""Only the appended direct public case; other targeted tests use original IDs."""
from pathlib import Path
import runpy

def test_appended_stalled_empty_retire_case_direct(tmp_path):
    ns=runpy.run_path(str(Path.cwd()/'sw/tests/test_pcie_gen3_continuous_rx_integrity_v20.py'))
    result,record,cases,out=ns['run'](tmp_path,maximum=150,case='stalled_output_retires_committed_zero_keep_words')
    assert result.returncode==0 and record['tests']==dict(passed=1,failed=0,skipped=14)
    assert len(cases)==1 and cases[0].find('failure')is None
    assert 'V20_STALLED_EMPTY_RETIRE held_cycles='in(out/'simulation.log').read_text()


def test_appended_stalled_empty_retire_case_miter(tmp_path):
    ns=runpy.run_path(str(Path.cwd()/'sw/tests/test_pcie_gen3_continuous_rx_integrity_v20.py'))
    mit=runpy.run_path(str(Path.cwd()/'sw/tests/test_pcie_gen3_integrity_v20_miter.py'))
    rtl=mit['miter'](tmp_path/'miter-rtl')
    result,record,cases,out=ns['run'](tmp_path,maximum=150,rtl=rtl,case='stalled_output_retires_committed_zero_keep_words')
    assert result.returncode==0 and record['tests']==dict(passed=1,failed=0,skipped=14)
    assert len(cases)==1 and cases[0].find('failure')is None
    assert 'V20_STALLED_EMPTY_RETIRE held_cycles='in(out/'simulation.log').read_text()
