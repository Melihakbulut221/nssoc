"""Independent whole-source and saved positive metadata review, no producer execution."""
from pathlib import Path
import ast,difflib,hashlib,json,re,tarfile,xml.etree.ElementTree as ET
R=Path.cwd();B=Path(__file__).resolve().parent
inputs={}
def pin(p):
 p=Path(p)
 with p.open('rb')as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
def read(p):inputs[str(p)]=pin(p);return p.read_text()
def load(p):return json.loads(read(p))
f=load(B/'source-freeze03.json');f0=load(B/'source-freeze02.json');assert f['previous_freeze']==pin(B/'source-freeze02.json')
changed=[]
for n,v in f['sources'].items():
 assert pin(R/n)==v;inputs[n]=v
 if n in f0['sources']:
  assert pin(B/'sources02'/n)==f0['sources'][n];inputs[str(B/'sources02'/n)]=f0['sources'][n]
  if v!=f0['sources'][n]:changed.append(n)
 else:assert n=='sw/tests/test_pcie_gen3_integrity_v23_block_burst.py'
assert changed==['sw/tests/test_pcie_gen3_integrity_v23_miter.py']
old=(B/'sources02'/changed[0]).read_text();new=(R/changed[0]).read_text()
addition='''    if fault == "header_promote_stale":
        # Wrapper line cadence does not fill next-bank; exercise the real
        # framer ready/valid block input using the exact same RTL mutation.
        burst = runpy.run_path(str(ROOT / "sw/tests/test_pcie_gen3_integrity_v23_block_burst.py"))
        burst["run_burst"](tmp_path / "burst", fault)
        return
'''
needle='def test_actual_miter_fault_is_observed(tmp_path, fault):\n';assert old.count(needle)==1 and old.replace(needle,needle+addition)==new and new.replace(needle+addition,needle)==old
burst=read(R/'sw/tests/test_pcie_gen3_integrity_v23_block_burst.py');tree=ast.parse(burst)
assert {n.name for n in tree.body if isinstance(n,ast.FunctionDef)}=={'pin','stimulus','bench','run_burst','test_actual_block_burst_scoreboard_and_promotion'}
# Independently inspect and bind immutable metadata remedy, including actual archived source/result bytes.
supp=load(B/'support-source03-supplement02.json');archive=R/supp['archive']['path'];assert pin(archive)['sha256']==supp['archive']['sha256'];inputs[str(archive)]=pin(archive)
found={}
with tarfile.open(archive,'r|xz')as tf:
 for member in tf:
  if member.name in supp['archive_member_pins']:
   data=tf.extractfile(member).read();got=dict(bytes=len(data),sha256=hashlib.sha256(data).hexdigest());assert got==supp['archive_member_pins'][member.name];found[member.name]=data
assert set(found)==set(supp['archive_member_pins'])
reader=read(B/'read_targeted_positive02.py');priorreader=read(B/'support-source03-candidate01/read_targeted_positive02.py')
fpin=pin(B/'source-freeze02.json');insert=f"assert pin(B/'source-freeze02.json')=={fpin!r}\n";assert reader.count(insert)==1
rpins=[supp['archive_member_pins'][f'raw/test_selected_adjacent_case_af{i}/capture/result.json']for i in range(2)]
oldline=" out=D/f'test_selected_adjacent_case_af{i}'/'capture';p=out/'result.json';j=json.loads(p.read_text())"
newlines=" out=D/f'test_selected_adjacent_case_af{i}'/'capture';p=out/'result.json'\n expected_pins="+repr(rpins)+"\n assert pin(p)==expected_pins[i]\n j=json.loads(p.read_text())"
assert reader.replace(insert,'').replace(newlines,oldline)==priorreader
# Independent own rehash/parse of saved positives, not executing proposed reader.
positives=[]
for i in range(2):
 out=Path('/dev/shm/nssoc-integrity-v23-public-controls02')/f'test_selected_adjacent_case_af{i}'/'capture';p=out/'result.json';assert pin(p)==rpins[i];j=load(p)
 assert j['status']=='PASS_PORT_ONLY_PCIE_GEN3_WIDE_CRC_QUARANTINE_RX'and j['tests']==dict(passed=1,failed=0,skipped=17)
 assert (j['mode'],j['max_encoded_bytes'],j['address_space_limit_bytes'],j['exact_test_selection'],j['expected_tests'])==('rtl',150,2*1024**3,'adjacent_header_all_positions_and_bank_boundaries',1)
 assert len(j['commands'])==1 and j['commands'][0]['returncode']==0
 for name,v in j['inputs'].items():
  q=Path(name)
  if q.is_relative_to(R)and str(q.relative_to(R))in f0['sources']:q=B/'sources02'/q.relative_to(R)
  assert pin(q)==v;inputs[str(q)]=v
 for name,v in j['outputs'].items():assert pin(out/name)==v;inputs[str(out/name)]=v
 cases=list(ET.parse(out/'results.xml').getroot().iter('testcase'));assert len(cases)==18
 selected=[c for c in cases if c.find('skipped')is None];assert len(selected)==1 and selected[0].attrib['name']==j['exact_test_selection'] and not any(c.find(n)is not None for c in cases for n in ['failure','error'])
 log=read(out/'simulation.log');assert 'TESTS=1 PASS=1 FAIL=0 SKIP=0'in log
 witness=None
 if i:
  m=re.search(r'V23_ADJACENT_WITNESSES positions=(\[[^\]]+\]) cross_block=(\d+) minimum_same_beat=(\d+) missing_old_predecessor=(\d+)',log);assert m
  vals=json.loads(m[1]);cross,ends,missing=map(int,m.groups()[1:]);assert len(vals)==16 and min(vals)>0 and cross>0 and ends>0 and missing>=16;witness=dict(positions=vals,cross=cross,ends=ends,missing=missing)
 positives.append(dict(result=pin(p),xml=pin(out/'results.xml'),witness=witness))
# Complete controller and detacher byte normalization, not only selected function comparison.
a=read(B/'launch_controls_targeted02.py');b=read(B/'launch_controls_targeted03.py');s=a
for x,y in [('source-freeze02.json','source-freeze03.json'),(fpin['sha256'],pin(B/'source-freeze03.json')['sha256']),('source-only-peer-rx02.json','source-only-peer-vco03.json'),('targeted_controls02.py','targeted_controls03.py'),('public-controls02','public-controls03'),('controls-status02','controls-status03'),('controls-owner02','controls-owner03'),('controls02.log','controls03.log'),('controls02.xml','controls03.xml')]:s=s.replace(x,y)
s=s.replace("and j['targeted_helper']==pin(B/'targeted_controls03.py')","and j['targeted_helper']==pin(B/'targeted_controls03.py') and j['saved_positive_reader']==pin(B/'read_targeted_positive02.py')")
start=s.index("command=[sys.executable,'-m','pytest'");end=s.index('\nowner=',start)
nodes=[str(B/'targeted_controls03.py'),'sw/tests/test_pcie_gen3_integrity_v23_block_burst.py::test_actual_block_burst_scoreboard_and_promotion','sw/tests/test_pcie_gen3_integrity_v23_miter.py::test_actual_miter_fault_is_observed[header_promote_stale]']
s=s[:start]+"command=[sys.executable,'-m','pytest','-q','-p','no:cacheprovider',*"+repr(nodes)+",'--basetemp='+str(D),'--junitxml='+str(B/'controls03.xml')]"+s[end:];assert s==b
s=read(B/'detach_controls_targeted02.py');newdetach=read(B/'detach_controls_targeted03.py')
for x,y in [('source-freeze02.json','source-freeze03.json'),(repr(fpin),repr(pin(B/'source-freeze03.json'))),('source-only-peer-rx02.json','source-only-peer-vco03.json'),('public-controls02','public-controls03'),('controls-status02','controls-status03'),('controls-detached-once02','controls-detached-once03'),('controls-detached-receipt02','controls-detached-receipt03'),('controls-launch02','controls-launch03'),('launch_controls_targeted02.py','launch_controls_targeted03.py'),(repr(pin(B/'launch_controls_targeted02.py')),repr(pin(B/'launch_controls_targeted03.py')))]:s=s.replace(x,y)
assert s==newdetach
read(B/'targeted_controls03.py');read(B/'source-peer-vco02-correction01.json');read(B/'source-peer-vco03-findings01.json')
assert all(pin(p)==v for p,v in inputs.items())
r=dict(status='PASS_SOURCE_ONLY_V23_ADJACENT_HEADER_RELATION',reviewer='vco_loaded_feedback',freeze=pin(B/'source-freeze03.json'),sources=f['sources'],targeted_helper=pin(B/'targeted_controls03.py'),saved_positive_reader=pin(B/'read_targeted_positive02.py'),support_methods={n:pin(B/n)for n in ['launch_controls_targeted03.py','detach_controls_targeted03.py']},findings=[],method=pin(Path(__file__)),checked_pins=inputs,independent_saved_positives=positives,resolved_finding='Exact freeze02 and both actual result.json pins added before parsing, independently matched to bytes in sealed failed-controls02 archive. Every prior input/output/XML/witness check unchanged; candidate reader and finding retained.',review=dict(source='Eight prior product/test sources byte-identical; only existing miter dispatch for exact surviving promotion mutation adds real block-input bench. Complete six-line inverse verified. No new product RTL change.',new_bench='Full source read. Real block ready/valid drives framer payload in actual four-lane packing, advances only on accepted handshake, holds unchanged data during backpressure, uses4ns clock. Scalar CRC/byte/meta oracle is existing independently checked encoder, not candidate logic. V22/V23 public outputs compare each cycle; independent byte/SOP/EOP/dllp/sequence scoreboard plus packet/verdict/drain counts retain actual data correctness.',meaningfulness='Clocked old-next relation sampled before edge must become new-current after NBA on actual reference step/slice3/next_valid. Required changed-value promotion, simultaneous promotion/acceptance, input stall and output stall prevent idle-path pass. Same exact candidate current<=current mutant requires specific PROMOTION_RELATION fatal, no force or hierarchical state assignment. Actual positive and negative still mandatory.',saved_reader='Independent own file read confirms both exact canonical selected positives1PASS/0FAIL/17selected-outSKIPs across18XMLentries; actual witness has all16positions and nonzero cross/minimum/missingoldpred. This is saved evidence, not HDL rerun. Surviving original promotion negative and prior two host-schema failures remain retained.',lifecycle='Whole reviewed launch/detach bodies reproduce exactly after fresh identifiers/hash/three-node selection and added reader pin. CPU6/2GiB, no healthy watchdog, sanitized Python overrides, owned descendant cleanup and terminal/context checks unchanged.'),scope='Source plus saved-positive metadata review only. No proposed reader, stimulus/bench generator, pytest, HDL compiler, native simulation or physical method executed. No functional closure until actual new block-burst positive/mutation and merged complete finite acceptance.')
p=B/'source-only-peer-vco03.json';assert not p.exists();p.write_text(json.dumps(r,indent=2)+'\n');print(pin(p))
