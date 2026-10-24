"""Exact saved-byte recount after host-only canonical-schema assertion bug."""
from pathlib import Path
import hashlib,json,re,xml.etree.ElementTree as ET
R=Path.cwd();B=Path(__file__).resolve().parent;D=Path('/dev/shm/nssoc-integrity-v23-public-controls02')
def pin(p):
 p=Path(p)
 with p.open('rb')as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
assert pin(B/'source-freeze02.json')=={'bytes': 4137, 'sha256': 'dd3132d1b9ba5d585bb66fcdabbd07450d86f7e217736cccb88cebc6f6a9c934'}
f=json.loads((B/'source-freeze02.json').read_text())
for n,v in f['sources'].items():assert pin(B/'sources02'/n)==v
records=[]
for i in range(2):
 out=D/f'test_selected_adjacent_case_af{i}'/'capture';p=out/'result.json'
 expected_pins=[{'bytes': 5383, 'sha256': '2106f78c077b7e1ea2fb66419f515311acf7d994e5ee53ab578934f8e0bb0a5c'}, {'bytes': 5641, 'sha256': '546f0dca1e6a4b628afc252c99d7d34a3221f4995136f2e1beed81fe539649b8'}]
 assert pin(p)==expected_pins[i]
 j=json.loads(p.read_text())
 assert j['status']=='PASS_PORT_ONLY_PCIE_GEN3_WIDE_CRC_QUARANTINE_RX' and j['tests']==dict(passed=1,failed=0,skipped=17)
 assert j['mode']=='rtl' and j['max_encoded_bytes']==150 and j['address_space_limit_bytes']==2147483648
 assert j['exact_test_selection']=='adjacent_header_all_positions_and_bank_boundaries' and j['expected_tests']==1
 assert len(j['commands'])==1 and j['commands'][0]['returncode']==0
 for n,v in j['inputs'].items():
  q=Path(n)
  if q.is_relative_to(R) and str(q.relative_to(R))in f['sources']:q=B/'sources02'/q.relative_to(R)
  assert pin(q)==v,str(q)
 for n,v in j['outputs'].items():assert pin(out/n)==v,n
 cs=list(ET.parse(out/'results.xml').getroot().iter('testcase'));assert len(cs)==18
 selected=[c for c in cs if c.find('skipped')is None]
 assert len(selected)==1 and selected[0].get('name')==j['exact_test_selection']
 assert not any(c.find(n)is not None for c in cs for n in ('failure','error'))
 s=(out/'simulation.log').read_text();assert 'TESTS=1 PASS=1 FAIL=0 SKIP=0'in s
 witness=None
 if i:
  x=re.search(r'V23_ADJACENT_WITNESSES positions=(\[[^\]]+\]) cross_block=(\d+) minimum_same_beat=(\d+) missing_old_predecessor=(\d+)',s);assert x
  positions=json.loads(x[1]);cross,ends,missing=map(int,x.groups()[1:]);assert len(positions)==16 and min(positions)>0 and cross>0 and ends>0 and missing>=16
  witness=dict(positions=positions,cross_block=cross,minimum_same_beat=ends,missing_old_predecessor=missing)
 records.append(dict(result=dict(path=str(p),**pin(p)),xml=dict(path=str(out/'results.xml'),**pin(out/'results.xml')),log=dict(path=str(out/'simulation.log'),**pin(out/'simulation.log')),tests=j['tests'],witness=witness))
r=dict(status='PASS_SAVED_NATIVE_V23_SELECTED_POSITIVES_CANONICAL_SCHEMA',source_freeze=pin(B/'source-freeze02.json'),records=records,source_and_output_pins_rechecked=True,reran_HDL=False,scope='Two actual completed native positive captures only. Historical host assertion failures remain; surviving promote mutant still requires separate block-port witness. No native timing acceptance.')
out=B/'saved-targeted-positive02.json';assert not out.exists();out.write_text(json.dumps(r,indent=2)+'\n');print(r['status'],pin(out))
