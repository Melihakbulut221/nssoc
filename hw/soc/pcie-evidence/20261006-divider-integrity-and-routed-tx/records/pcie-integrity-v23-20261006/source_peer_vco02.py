"""Independent saved-source derivative review; no producer imports or HDL execution."""
from pathlib import Path
import ast,hashlib,json,xml.etree.ElementTree as ET
R=Path.cwd();B=Path(__file__).resolve().parent

def pin(p):
 p=Path(p)
 with p.open('rb')as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
f0=json.loads((B/'source-freeze01.json').read_text());f=json.loads((B/'source-freeze02.json').read_text());prior=json.loads((B/'source-only-peer-rx01.json').read_text())
assert prior['status']=='PASS_SOURCE_ONLY_V23_ADJACENT_HEADER_RELATION'and not prior['findings'] and prior['freeze']==pin(B/'source-freeze01.json')
assert f['prior_freeze']==pin(B/'source-freeze01.json')
inputs={str(B/n):pin(B/n)for n in ['source-freeze01.json','source-freeze02.json','source-only-peer-rx01.json','targeted_controls02.py','launch_controls02.py','launch_controls_targeted02.py','detach_controls02.py','detach_controls_targeted02.py','controls-status01.json','controls01.xml','controls01.log','failed-controls01-release.json']}
changed=[]
for n,value in f['sources'].items():
 assert pin(R/n)==value and pin(B/'sources02'/n)==value
 assert pin(B/'sources01'/n)==f0['sources'][n]
 inputs[n]=value;inputs[str(B/'sources01'/n)]=f0['sources'][n]
 if value!=f0['sources'][n]:changed.append(n)
bench='hw/soc/tb/cocotb/test_soc_pcie_gen3_continuous_rx_integrity_v23.py';assert changed==[bench]
old=(B/'sources01'/bench).read_text();new=(R/bench).read_text();addition='    # Selected execution starts at t=0; reset/settle before observer snapshots.\n    await p.begin()\n'
needle='async def adjacent_header_all_positions_and_bank_boundaries(d):\n    p = Ports(d)\n'
assert old.count(needle)==new.count(needle)==1 and old.replace(needle,needle+addition)==new and new.replace(needle+addition,needle)==old
assert f['baseline']==f0['baseline'] and f['contracts']==f0['contracts'] and f['predicates']==f0['predicates'] and f['resources']==f0['resources']
for n,p in f['contracts'].items():assert pin(B/n)==p;inputs[str(B/n)]=p
assert pin(R/f['baseline']['path'])=={k:v for k,v in f['baseline'].items()if k!='path'}
# Whole-controller exact inverse: fresh receipt names, explicit targeted node list and helper pin only.
a=(B/'launch_controls02.py').read_text();b=(B/'launch_controls_targeted02.py').read_text();s=a
for x,y in [('source-freeze01.json','source-freeze02.json'),(pin(B/'source-freeze01.json')['sha256'],pin(B/'source-freeze02.json')['sha256']),('source-only-peer-rx01.json','source-only-peer-rx02.json'),('public-controls01','public-controls02'),('controls-status01','controls-status02'),('controls-owner01','controls-owner02'),('controls01.log','controls02.log'),('controls01.xml','controls02.xml')]:s=s.replace(x,y)
faults=['header_wrong_predecessor','header_current_input_tail','header_shift_wrong','header_promote_stale','header_carried_invert','header_carried_always_bad'];nodes=[str(B/'targeted_controls02.py')]+['sw/tests/test_pcie_gen3_integrity_v23_miter.py::test_actual_miter_fault_is_observed['+n+']'for n in faults]+['sw/tests/test_pcie_gen3_integrity_v23_miter.py::test_actual_old_predecessor_observer_negative']
start=s.index("command=[sys.executable,'-m','pytest'");end=s.index('\nowner=',start)
s=s[:start]+"command=[sys.executable,'-m','pytest','-q','-p','no:cacheprovider',*"+repr(nodes)+",'--basetemp='+str(D),'--junitxml='+str(B/'controls02.xml')]"+s[end:]
s=s.replace("assert j['freeze']==pin(freeze)","assert j['freeze']==pin(freeze) and j['targeted_helper']==pin(B/'targeted_controls02.py')")
assert s==b
s=(B/'detach_controls02.py').read_text()
for x,y in [('source-freeze01.json','source-freeze02.json'),(repr(pin(B/'source-freeze01.json')),repr(pin(B/'source-freeze02.json'))),('source-only-peer-rx01.json','source-only-peer-rx02.json'),('public-controls01','public-controls02'),('controls-status01','controls-status02'),('controls-detached-once01','controls-detached-once02'),('controls-detached-receipt01','controls-detached-receipt02'),('controls-launch01','controls-launch02'),('launch_controls02.py','launch_controls_targeted02.py'),(repr(pin(B/'launch_controls02.py')),repr(pin(B/'launch_controls_targeted02.py')))]:s=s.replace(x,y)
assert s==(B/'detach_controls_targeted02.py').read_text()
# Prior actual errors, preserved as failures rather than product rejections.
cases=list(ET.parse(B/'controls01.xml').getroot().iter('testcase'));failed=[c for c in cases if c.find('failure')is not None or c.find('error')is not None];assert len(cases)==35 and len(failed)==7 and all(c.find('skipped')is None for c in cases)
expected={'test_actual_miter_fault_is_observed['+x+']'for x in faults}|{'test_actual_old_predecessor_observer_negative'};assert {c.attrib['name']for c in failed}==expected
rawroot=Path('/dev/shm/nssoc-integrity-v23-public-controls01');bad=[]
for directory in rawroot.iterdir():
 if not directory.is_dir()or directory.is_symlink():continue
 for p in directory.rglob('simulation.log'):
  text=p.read_text()
  if "Can't convert LogicArray to int: it contains non-0/1 values"in text:
   assert 'positions0 = [int(d.v23_stp_positions[i].value)'in text and '0.00ns WARNING'in text.replace(' ns','ns').replace('  ',' ') or 'positions0 = [int(d.v23_stp_positions[i].value)'in text
   bad.append(str(p));inputs[str(p)]=pin(p)
assert len(bad)==7
helper=(B/'targeted_controls02.py').read_text();compile(helper,'targeted_controls02.py','exec')
assert "@pytest.mark.parametrize('miter',[False,True])"in helper and "record['tests']==dict(passed=1,failed=0,skipped=0)"in helper and "'V23_ADJACENT_WITNESSES'"in helper
r=dict(status='PASS_SOURCE_ONLY_V23_ADJACENT_HEADER_RELATION',reviewer='vco_loaded_feedback',freeze=pin(B/'source-freeze02.json'),sources=f['sources'],targeted_helper=pin(B/'targeted_controls02.py'),support_methods={n:pin(B/n)for n in ['launch_controls_targeted02.py','detach_controls_targeted02.py']},prior_source_peer=pin(B/'source-only-peer-rx01.json'),findings=[],method=pin(Path(__file__)),checked_pins=inputs,review=dict(delta='Exactly one100-byte initialization comment/await p.begin before first observer counter snapshot in new18th case; other8source files, all RTL/miter/literal predicates unchanged.',temporal='Ports.begin performs awaited reset cycle then stream-start cycle, allowing Verilog initial array values and sequential reset to settle before conversion. It does not zero or mask observation values in Python, relax any assertion, or change accepted-word identities; cumulative observer counters remain incremented by actual RTL events.',prior_failures='Exactly28PASS/7FAIL in saved XML. Allseven selected new negatives failed on initial positions0 non-binary conversion; these were not accepted as real mutation failures. All seven raw saved logs rehashed.',targeted='Two actual selected direct/miter positives plus six exact header product mutants and one declared observer mutant. Successful selected positives require exact1PASS/0FAIL/0SKIP XML; miter requires all original public/ownership checks and actual witness log. Negative semantic diagnostics and compiled-native requirement unchanged.',lifecycle='Whole controller/detacher source normalization reproduced; CPU6/2GiB, fixed clock, lexical .venv, sanitized3Python overrides, ProcessOwner wait and postcontext checks, no healthy timeout unchanged.',scope_qualification='Inherited freeze scope saying no controls yet is historical wording; actual prior28PASS/7FAIL exists. No revision02 controls have run and no new functional PASS claimed.'),scope='Bounded additive source/saved failure review only, relying on prior complete RX V23 source peer. No reviewed producer import, HDL compiler, controls or native execution.')
p=B/'source-only-peer-rx02.json';assert not p.exists();p.write_text(json.dumps(r,indent=2)+'\n');print(pin(p))
