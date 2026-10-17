"""Recount actual V24 positives/mutants; preserve one historical host failure."""
from pathlib import Path
import hashlib,io,json,re,tarfile,xml.etree.ElementTree as ET
R=Path.cwd();B=Path(__file__).resolve().parent
D1=Path('/dev/shm/nssoc-integrity-v24-full-controls01');D3=Path('/dev/shm/nssoc-integrity-v24-diagnostic-controls03')
def pin(p):
 p=Path(p)
 with p.open('rb') as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
def load(p):return json.loads(Path(p).read_text())
def counts(p):
 cs=list(ET.parse(p).getroot().iter('testcase'))
 return cs,dict(passed=sum(not any(c.find(x)is not None for x in('failure','error','skipped'))for c in cs),failed=sum(any(c.find(x)is not None for x in('failure','error'))for c in cs),skipped=sum(c.find('skipped')is not None for c in cs))
f2=load(B/'source-freeze02.json');f3=load(B/'source-freeze03.json')
changed={n for n,h in f2['product_sources'].items() if h!=f3['product_sources'][n]}
miter='sw/tests/test_pcie_gen3_integrity_v24_miter.py';assert changed=={miter}
for n,h in f2['product_sources'].items():assert pin(B/'source-before-diagnostic03'/n)==h,n
for n,h in f3['sources'].items():assert pin(R/n)==h,n
peer=load(B/'source-only-peer-vco03.json');assert peer['status']=='PASS_SOURCE_ONLY_V24_PREFIX_CONTEXT_IMPLEMENTATION' and peer['freeze']==pin(B/'source-freeze03.json') and not peer['findings']
history=load(B/'controls01-final-validation.json');assert history['status']=='RETAINED_V24_41_PASS_1_HOST_DIAGNOSTIC_FAILURE'
assert pin(history['archive']['path'])=={k:history['archive'][k]for k in('bytes','sha256')}
campaigns=[]
for rev,want in [('01',dict(passed=41,failed=1,skipped=0)),('03',dict(passed=2,failed=0,skipped=0))]:
 cs,c=counts(B/f'controls{rev}.xml');assert c==want
 s=load(B/f'status{rev}.json');assert s['returncode']==(1 if rev=='01' else 0) and not s['stop_reason']
 for birth in(s['controller'],s['pytest']):
  p=Path('/proc')/str(birth['pid'])/'stat';assert not p.exists() or p.read_text().rsplit(') ',1)[1].split()[19]!=birth['start_ticks']
 campaigns.append(dict(path=str(B/f'controls{rev}.xml'),**pin(B/f'controls{rev}.xml'),**c,cases=[x.attrib for x in cs]))
helpers=[]
for directory,revision in [(D1,2),(D3,3)]:
 for p in sorted(directory.glob('*/*/result.json')):
  if p.parent.parent.is_symlink():continue
  r=load(p);assert r.get('status')!='RUNNING'
  for n,h in r['inputs'].items():
   q=Path(n)
   if revision==2 and q==R/miter:q=B/'source-before-diagnostic03'/miter
   assert pin(q)==h,n
  for n,h in r['outputs'].items():assert pin(p.parent/n)==h,n
  x=p.parent/'results.xml';helpers.append(dict(path=str(p),**pin(p),revision=revision,status=r.get('status'),counts=counts(x)[1] if x.exists() else None))
for n in ['test_actual_wide_rx_full_posit0','test_v23_v24_cycle_exact_all_p0']:
 d=D1/n/'capture';assert counts(d/'results.xml')[1]==dict(passed=18,failed=0,skipped=0)
 assert load(d/'result.json')['tests']==dict(passed=18,failed=0,skipped=0)
positive=(D1/'test_v23_v24_cycle_exact_all_p0/capture/simulation.log').read_text()
context_pattern=r'V24_CONTEXT_WITNESSES current=(\d+) next=(\d+) shifts=(\d+) promotions=(\d+) changed=(\d+) concurrent=(\d+) modes=(\d+) carry=(\d+)/(\d+)/(\d+)/(\d+) eds=(\d+)'
cm=list(map(int,re.search(context_pattern,positive).groups()));assert cm[0]>0 and cm[2]>0 and min(cm[6:])>0
cache=re.search(r'V24_CACHE_QUARANTINE epochs=(\d+) actual_fault_steps=(\d+) invalid_cache_changes=(\d+)',positive)
assert cache and list(map(int,cache.groups()))==[8,8,8]
mutants=[]
for i in range(12):
 d=D1/f'test_actual_miter_fault_is_obs{i}'/('burst' if i==9 else 'capture')
 t=(d/'simulation.log').read_text();r=load(d/'result.json')
 assert 'FATAL:' in t
 if i==11:assert 'V24_CONTEXT_CONSUMED_MODE word=1' in t and 'Time: 50000' in t
 elif i==9:assert 'V24_FRAMER_PROMOTION_RELATION' in t and r['returncode']!=0
 else:assert r['status']=='FAIL' and re.search(r'(PCIE_(?:CYCLE_MITER_OUTPUT|RING_CONTROL|OCCUPIED_SLOT)_MISMATCH|V24_(?:OCCUPIED_SLOT_VERDICT|DESCRIPTOR_OWNERSHIP|OWNED_DESCRIPTOR_PAYLOAD)_MISMATCH|V24_(?:FAULT_QUARANTINE_NOT_ATOMIC|HEADER_BANK_RELATION|FIRST_HEADER_RELATION|CARRIED_HEADER_RELATION))',t)
 mutants.append(dict(path=str(d/'simulation.log'),**pin(d/'simulation.log'),index=i))
target=D3/'test_actual_miter_fault_is_obs0/capture';t=(target/'simulation.log').read_text()
assert load(target/'result.json')['status']=='FAIL' and 'V24_CONTEXT_CONSUMED_MODE word=1' in t and 'Time: 50000' in t
assert (target/'sim/sim.vvp').is_file()
# Identical generated mutant and unchanged stimuli: only the host acceptance
# predicate changed between original and repeated meaningful native failure.
for name in ('soc_pcie_gen3_framer_rx_integrity_v24.v','soc_pcie_gen3_continuous_rx_integrity_v24.v'):
 assert (D1/'test_actual_miter_fault_is_obs11/fault-rtl'/name).read_bytes()==(D3/'test_actual_miter_fault_is_obs0/fault-rtl'/name).read_bytes()
burst=D1/'test_actual_block_burst_scoreb0/burst';bt=(burst/'simulation.log').read_text()
assert load(burst/'result.json')['returncode']==0
bw=list(map(int,re.search(r'PASS_V24_FRAMER_BURST blocks=(\d+) bytes=(\d+) packets=(\d+) promotions=(\d+) changed=(\d+) concurrent=(\d+) inputstall=(\d+) outputstall=(\d+)',bt).groups()))
assert bw[:3]==[15,786,25] and min(bw[3:])>0
bc=list(map(int,re.search(context_pattern,bt).groups()));assert min(bc)>0
bank=[]
for i in range(4):
 p=D1/f'test_actual_context_bank_fault{i}/burst';r=load(p/'result.json');assert r['returncode']!=0 and 'V24_CONTEXT_BANK' in(p/'simulation.log').read_text()
 bank.append(dict(path=str(p/'result.json'),**pin(p/'result.json'),fault=r['fault']))
for i in range(5):
 t=(D1/f'test_actual_finite_matrix_alph{i}/run.log').read_text()
 assert 'V24_ALPHABET vectors=16384 token_matrices=13 carry_columns=4 initial_modes=9 complete_matrices=52' in t
 assert ('V24_PREFIX_RELATION_PASS matrices=140608 comparisons=3796416' if i==0 else 'V24_PREFIX_RELATION word=') in t
for i in range(3):
 t=(D1/f'test_actual_block_context_pack{i}/run.log').read_text()
 assert ('PASS_V24_BLOCK_CONTEXT_PACK vectors=672 positions=16 binary=512 XZ=160 filler=exact' if i==0 else 'V24_BLOCK_CONTEXT_PACK case=') in t
entries={}
for directory,label in [(D1,'initial'),(D3,'diagnostic03')]:
 for p in directory.rglob('*'):
  if p.is_file() and not p.is_symlink() and not any(q.is_symlink() for q in p.parents if q!=directory.parent):entries['raw/'+label+'/'+str(p.relative_to(directory))]=p
for n in f3['product_sources']:entries['sources/'+n]=R/n
for p in B.rglob('*'):
 if p.is_file() and p.suffix in('.json','.py','.xml','.log','.vh') and p.name not in('active-checkpoint.json','seal-controls03.log'):
  entries['evidence/'+str(p.relative_to(B))]=p
manifest={n:dict(original=str(p),**pin(p)) for n,p in sorted(entries.items())}
archive=B/'pcie-integrity-v24-composite-controls-20261006.tar.xz';assert not archive.exists()
raw=json.dumps(manifest,indent=2).encode()+b'\n'
with tarfile.open(archive,'w:xz',preset=1) as tar:
 for n,p in sorted(entries.items()):tar.add(p,arcname=n,recursive=False)
 i=tarfile.TarInfo('members.json');i.size=len(raw);tar.addfile(i,io.BytesIO(raw))
seen=set()
with tarfile.open(archive,'r:xz') as tar:
 for i in tar:
  assert i.isfile() and i.name not in seen;seen.add(i.name);data=tar.extractfile(i).read()
  if i.name=='members.json':assert data==raw
  else:assert dict(bytes=len(data),sha256=hashlib.sha256(data).hexdigest())=={k:manifest[i.name][k] for k in('bytes','sha256')}
assert seen==set(manifest)|{'members.json'}
for n,p in entries.items():assert pin(p)=={k:manifest[n][k] for k in('bytes','sha256')}
r=dict(status='PASS_V24_PREFIX_CONTEXT_COMPOSITE_CONTROLS',source_freeze=pin(B/'source-freeze03.json'),source_peer=pin(B/'source-only-peer-vco03.json'),campaigns=campaigns,pytest_executions=44,passed_executions=43,historical_failed_executions=1,current_42_predicates_covered=True,public_profiles=dict(direct=18,cycle_miter=18,unchanged_latency=True),cache_fault_write_epochs=8,context_public_witness=cm,burst_witness=bw,context_burst_witness=bc,meaningful_miter_mutants=mutants,context_bank_mutants=bank,component=dict(literal_classifications=16384,token_matrices=13,carry_columns=4,initial_modes=9,complete_matrices=52,ordered_triples=140608,comparisons=3796416,actual_faults=4),packing=dict(vectors=672,binary=512,literal_XZ=160,positions=16,actual_faults=2),targeted_same_mutant_rejection=dict(path=str(target/'simulation.log'),**pin(target/'simulation.log'),time_ns=50),helper_receipts=helpers,archive=dict(path=str(archive),**pin(archive)),members=len(seen),full_member_readback=True,all_original_pins_rechecked=True,MAX4118_excluded=True,physical_acceptance=False,scope='Current42 predicates covered across41PASS1historicalhostFAIL and2targetedPASS, with exact unchanged RTL/stimuli and repeated named native fault. No mapped equivalence, timing, fullPHY or manufacturing acceptance.')
validation=B/'pcie-integrity-v24-composite-controls-validation-20261006.json';validation.write_text(json.dumps(r,indent=2)+'\n')
print(r['status'],r['archive'],len(seen),pin(validation),flush=True)
