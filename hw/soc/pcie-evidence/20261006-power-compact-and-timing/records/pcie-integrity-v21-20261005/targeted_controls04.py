"""Only the corrected parser-fault positive; other selected tests use pinned originals."""
from pathlib import Path
import runpy
R=Path.cwd()
def test_changed_fault_epoch_positive(tmp_path):
 helper=runpy.run_path(str(R/'sw/tests/test_pcie_gen3_continuous_rx_integrity_v21.py'))
 case='descriptor_parser_fault_cancels_queue_after_sampling_edge'
 result,record,cases,out=helper['run'](tmp_path,case=case)
 assert result.returncode==0 and record['tests']==dict(passed=1,failed=0,skipped=15),record
 assert len(cases)==1 and cases[0].find('failure') is None
 log=(out/'simulation.log').read_text()
 assert 'V21_PARSER_FAULT_EPOCHS' in log
