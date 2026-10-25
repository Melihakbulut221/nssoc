from pathlib import Path
import hashlib,json,shutil,ast
R=Path.cwd();B=Path(__file__).resolve().parent
def pin(p):
 with Path(p).open('rb')as f:return dict(bytes=Path(p).stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
f=json.loads((B/'source-freeze01.json').read_text());p=R/'hw/soc/tb/cocotb/test_soc_pcie_gen3_continuous_rx_integrity_v23.py';old=p.read_text()
a='async def adjacent_header_all_positions_and_bank_boundaries(d):\n    p = Ports(d)\n';b=a+'    # Selected execution starts at t=0; reset/settle before observer snapshots.\n    await p.begin()\n';assert old.count(a)==1;p.write_text(old.replace(a,b))
assert p.read_text().replace(b,a)==old
f['status']='FROZEN_V23_ADDITIVE_SELECTED_CASE_INITIALIZATION';f['prior_freeze']=pin(B/'source-freeze01.json');f['changes']=['Only new18th testcase resets/settles before reading observer counters; original17prefix, strictwitnesses, allproduct/miter/literal bytes unchanged. Initial28PASS7FAIL fully retained. No new02 controls yet.'];f['sources']={n:pin(R/n)for n in f['sources']}
q=B/'source-freeze02.json';q.write_text(json.dumps(f,indent=2)+'\n')
D=B/'sources02';D.mkdir()
for n in f['sources']:
 t=D/n;t.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(R/n,t)
# Two fresh selected positives plus exactly seven affected negatives.
helper='''"""Actual corrected18th case through direct and cycle-miter RTL."""
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
'''
(B/'targeted_controls02.py').write_text(helper)
s=(B/'launch_controls02.py').read_text();s=s.replace('source-freeze01.json','source-freeze02.json').replace('446efb90f07eb3b2fe960498c55079afb385c3a89f8e2dad6dc02f028372b630',pin(q)['sha256']).replace('source-only-peer-rx01.json','source-only-peer-rx02.json').replace('public-controls01','public-controls02').replace('controls-status01','controls-status02').replace('controls-owner01','controls-owner02').replace('controls01.log','controls02.log').replace('controls01.xml','controls02.xml')
a="command=[sys.executable,'-m','pytest'";start=s.index(a);end=s.index('\nowner=',start)
nodes=[str(B/'targeted_controls02.py')]+['sw/tests/test_pcie_gen3_integrity_v23_miter.py::test_actual_miter_fault_is_observed['+n+']'for n in ['header_wrong_predecessor','header_current_input_tail','header_shift_wrong','header_promote_stale','header_carried_invert','header_carried_always_bad']]+['sw/tests/test_pcie_gen3_integrity_v23_miter.py::test_actual_old_predecessor_observer_negative']
command="command=[sys.executable,'-m','pytest','-q','-p','no:cacheprovider',*"+repr(nodes)+",'--basetemp='+str(D),'--junitxml='+str(B/'controls02.xml')]"
s=s[:start]+command+s[end:];s=s.replace("assert j['freeze']==pin(freeze)","assert j['freeze']==pin(freeze) and j['targeted_helper']==pin(B/'targeted_controls02.py')")
(B/'launch_controls_targeted02.py').write_text(s)
s=(B/'detach_controls02.py').read_text();s=s.replace('source-freeze01.json','source-freeze02.json').replace(repr(pin(B/'source-freeze01.json')),repr(pin(q))).replace('source-only-peer-rx01.json','source-only-peer-rx02.json').replace('public-controls01','public-controls02').replace('controls-status01','controls-status02').replace('controls-detached-once01','controls-detached-once02').replace('controls-detached-receipt01','controls-detached-receipt02').replace('controls-launch01','controls-launch02').replace("launch_controls02.py","launch_controls_targeted02.py").replace(repr(pin(B/'launch_controls02.py')),repr(pin(B/'launch_controls_targeted02.py')))
(B/'detach_controls_targeted02.py').write_text(s)
print(pin(q),pin(B/'targeted_controls02.py'))
