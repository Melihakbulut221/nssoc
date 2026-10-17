"""Seal all actual frozen V23 control bytes; failures remain failures."""
from pathlib import Path
import hashlib,io,json,re,tarfile,xml.etree.ElementTree as ET
R=Path.cwd();B=Path(__file__).resolve().parent;D=Path('/dev/shm/nssoc-integrity-v23-public-controls01')
def pin(p):
 p=Path(p)
 with p.open('rb')as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
def counts(p):
 cs=list(ET.parse(p).getroot().iter('testcase'))
 return cs,dict(passed=sum(not any(c.find(k)is not None for k in ('failure','error','skipped'))for c in cs),failed=sum(any(c.find(k)is not None for k in ('failure','error'))for c in cs),skipped=sum(c.find('skipped')is not None for c in cs))
f=json.loads((B/'source-freeze01.json').read_text())
for n,v in f['sources'].items():assert pin(R/n)==v and pin(B/'sources01'/n)==v,n
peer=json.loads((B/'source-only-peer-rx01.json').read_text());assert peer['freeze']==pin(B/'source-freeze01.json')and not peer['findings']
state=json.loads((B/'controls-status01.json').read_text());assert state['status']in ('COMPLETE_PENDING_INDEPENDENT_CONTROL_RECOUNT','FAILED_CONTROLS_RETAINED')and state['returncode']in(0,1)
cs,c=counts(B/'controls01.xml');assert len(cs)==35 and c['skipped']==0
assert (state['returncode']==0)==(c==dict(passed=35,failed=0,skipped=0))
helpers=[]
for p in sorted(D.glob('*/*/result.json')):
 if p.parent.parent.is_symlink():continue
 r=json.loads(p.read_text())
 if 'inputs'not in r or 'outputs'not in r:continue
 assert r['status']!='RUNNING'
 for n,v in r['inputs'].items():assert pin(n)==v,n
 for n,v in r['outputs'].items():assert pin(p.parent/n)==v,str(p.parent/n)
 x=p.parent/'results.xml'
 helpers.append(dict(path=str(p),**pin(p),status=r['status'],counts=counts(x)[1]if x.is_file()else None))
observations={}
if c['failed']==0:
 direct=D/'test_actual_wide_rx_full_posit0/capture';miter=D/'test_v22_v23_cycle_exact_all_p0/capture'
 for p in [direct,miter]:assert counts(p/'results.xml')[1]==dict(passed=18,failed=0,skipped=0)
 s=(miter/'simulation.log').read_text()
 x=re.search(r'V23_CACHE_QUARANTINE epochs=(\d+) actual_fault_steps=(\d+) invalid_cache_changes=(\d+)',s);assert x and list(map(int,x.groups()))==[8,8,8]
 x=re.search(r'V23_ADJACENT_WITNESSES positions=(\[[^\]]+\]) cross_block=(\d+) minimum_same_beat=(\d+) missing_old_predecessor=(\d+)',s);assert x
 positions=json.loads(x[1]);cross,ends,missing=map(int,x.groups()[1:]);assert len(positions)==16 and min(positions)>0 and cross>0 and ends>0 and missing>=16
 observations.update(public_cases=18,cycle_exact_cases=18,cache_fault_write_epochs=8,cache_actual_changed_epochs=8,adjacent_positions=positions,cross_block_headers=cross,minimum_first_header_end_same_beat=ends,missing_old_predecessor_accepts=missing)
 literal=[]
 for p in sorted(D.glob('test_actual_adjacent_relation_*/run.log')):
  if p.parent.is_symlink():continue
  s=p.read_text();positive='PASS_V23_ADJACENT_RELATION binary=557056 literalXZ=1440'in s
  assert positive or 'V23_ADJACENT_LITERAL case='in s
  literal.append(dict(path=str(p),**pin(p),positive=positive))
 assert len(literal)==6 and sum(x['positive']for x in literal)==1
 observations['literal_controls']=literal
 mutants=[]
 for p in sorted(D.glob('test_actual_miter_fault_is_obs*/capture/simulation.log')):
  if p.parent.parent.is_symlink():continue
  s=p.read_text();assert (p.parent/'sim/sim.vvp').is_file()
  messages=re.findall(r'(?:PCIE_CYCLE_MITER_OUTPUT_MISMATCH|PCIE_RING_CONTROL_MISMATCH|PCIE_OCCUPIED_SLOT_MISMATCH|V23_OCCUPIED_SLOT_VERDICT_MISMATCH|V23_DESCRIPTOR_OWNERSHIP_MISMATCH|V23_OWNED_DESCRIPTOR_PAYLOAD_MISMATCH|V23_FAULT_QUARANTINE_NOT_ATOMIC|V23_HEADER_BANK_RELATION|V23_FIRST_HEADER_RELATION|V23_CARRIED_HEADER_RELATION)',s)
  assert messages;mutants.append(dict(path=str(p),**pin(p),diagnostics=sorted(set(messages))))
 assert len(mutants)==12;observations['miter_actual_mutants']=mutants
 op=D/'test_actual_old_predecessor_ob0/observer-capture/simulation.log';assert 'V23_OBSERVER_OLD_PREDECESSOR'in op.read_text();observations['observer_negative']=dict(path=str(op),**pin(op))
entries={}
for p in D.rglob('*'):
 if p.is_file()and not p.is_symlink()and not any(q.is_symlink()for q in p.parents if q!=D.parent):entries['raw/'+str(p.relative_to(D))]=p
for n in f['sources']:entries['sources/'+n]=R/n
for p in B.rglob('*'):
 if p.is_file()and not p.is_symlink()and p.suffix not in('.xz','.gz')and p.name not in ['active-checkpoint.json','seal-controls01.log']:
  entries['evidence/'+str(p.relative_to(B))]=p
manifest={n:dict(original=str(p),**pin(p))for n,p in sorted(entries.items())}
archive=B/'pcie-integrity-v23-controls01-20261006.tar.xz';assert not archive.exists()
with tarfile.open(archive,'w:xz',preset=1)as t:
 for n,p in sorted(entries.items()):t.add(p,arcname=n,recursive=False)
 raw=(json.dumps(manifest,indent=2)+'\n').encode();info=tarfile.TarInfo('members.json');info.size=len(raw);t.addfile(info,io.BytesIO(raw))
seen=set()
with tarfile.open(archive,'r:xz')as t:
 for i in t:
  assert i.isfile()and i.name not in seen;seen.add(i.name);raw=t.extractfile(i).read()
  if i.name=='members.json':assert json.loads(raw)==manifest
  else:assert len(raw)==manifest[i.name]['bytes']and hashlib.sha256(raw).hexdigest()==manifest[i.name]['sha256']
assert len(seen)==len(manifest)+1
for n,p in entries.items():assert pin(p)=={k:manifest[n][k]for k in ('bytes','sha256')}
r=dict(status='PASS_V23_ADJACENT_HEADER_CONTROLS'if c['failed']==0 else 'FAILED_V23_CONTROLS_RETAINED',source_freeze=pin(B/'source-freeze01.json'),source_peer=pin(B/'source-only-peer-rx01.json'),pytest=dict(path=str(B/'controls01.xml'),**pin(B/'controls01.xml'),**c),cases=[dict(name=x.get('name'),failed=any(x.find(k)is not None for k in ('failure','error')))for x in cs],observations=observations,helper_receipts=helpers,archive=dict(path=str(archive),**pin(archive)),members=len(seen),full_member_readback=True,all_original_pins_rechecked=True,MAX4118_profile_excluded=True,physical_acceptance=False,scope='Actual full frozen35-control execution and complete native captures. Failure count retained without waiver; mapping permitted only all35PASS plus independently reviewed actual witness evidence. Existing4ns/150byte/2GiB profile unchanged, no fullPHY or signoff claim.')
p=B/'pcie-integrity-v23-controls01-validation-20261006.json';assert not p.exists();p.write_text(json.dumps(r,indent=2)+'\n');print(r['status'],pin(archive),len(seen),pin(p))
