"""Actual corrected18th case through direct and cycle-miter RTL."""
from pathlib import Path
import json,os,runpy,shutil,subprocess,sys,xml.etree.ElementTree as ET
import pytest
R=Path.cwd()
@pytest.mark.parametrize('miter',[False,True])
def test_selected_adjacent_case_after_initialization(tmp_path,miter):
    tool=Path(shutil.which('iverilog')or'/usr/bin/iverilog');out=tmp_path/'capture'
    command=[sys.executable,str(R/'scripts/check_pcie_gen3_continuous_rx_integrity_v23.py'),'--out',str(out),'--iverilog-dir',str(tool.parent),'--test','adjacent_header_all_positions_and_bank_boundaries']
    if miter:
        m=runpy.run_path(str(R/'sw/tests/test_pcie_gen3_integrity_v23_miter.py'));rtl=m['miter'](tmp_path/'miter-rtl');command+=['--rtl-dir',str(rtl)]
    with(tmp_path/'launch.log').open('w')as log:
        result=subprocess.run(command,cwd=R,stdout=log,stderr=subprocess.STDOUT,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'})
    record=json.loads((out/'result.json').read_text());cases=list(ET.parse(out/'results.xml').getroot().iter('testcase'))
    assert result.returncode==0 and record['status']=='PASS' and record['tests']==dict(passed=1,failed=0,skipped=0)
    assert len(cases)==1 and cases[0].get('name')=='adjacent_header_all_positions_and_bank_boundaries'and not any(cases[0].find(n)is not None for n in ['failure','error','skipped'])
    if miter:assert 'V23_ADJACENT_WITNESSES' in(out/'simulation.log').read_text()
