"""Recount all immutable V23 campaigns, including every real prior failure."""
from pathlib import Path
import ast,hashlib,io,json,re,tarfile,xml.etree.ElementTree as ET
R=Path.cwd();B=Path(__file__).resolve().parent
D1=Path('/dev/shm/nssoc-integrity-v23-public-controls01');D2=Path('/dev/shm/nssoc-integrity-v23-public-controls02');D3=Path('/dev/shm/nssoc-integrity-v23-public-controls03')
def pin(p):
 p=Path(p)
 with p.open('rb')as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
def recount(p):
 cs=list(ET.parse(p).getroot().iter('testcase'))
 return cs,dict(passed=sum(not any(c.find(x)is not None for x in ['failure','error','skipped'])for c in cs),failed=sum(any(c.find(x)is not None for x in ['failure','error'])for c in cs),skipped=sum(c.find('skipped')is not None for c in cs))
def load(p):return json.loads(Path(p).read_text())
freezes={i:load(B/f'source-freeze0{i}.json')for i in [1,2,3]}
for i,f in freezes.items():
 for n,v in f['sources'].items():assert pin(B/f'sources0{i}'/n)==v,n
for n,v in freezes[3]['sources'].items():assert pin(R/n)==v,n
bench='hw/soc/tb/cocotb/test_soc_pcie_gen3_continuous_rx_integrity_v23.py';miter='sw/tests/test_pcie_gen3_integrity_v23_miter.py'
assert {n for n in freezes[1]['sources']if freezes[1]['sources'][n]!=freezes[2]['sources'][n]}=={bench}
assert {n for n in freezes[2]['sources']if freezes[2]['sources'][n]!=freezes[3]['sources'][n]}=={miter}
a=(B/'sources01'/bench).read_text();b=(B/'sources02'/bench).read_text()
delta='    # Selected execution starts at t=0; reset/settle before observer snapshots.\n    await p.begin()\n'
assert b.count(delta)==1 and b.replace(delta,'')==a
delta='''    if fault == "header_promote_stale":
        # Wrapper line cadence does not fill next-bank; exercise the real
        # framer ready/valid block input using the exact same RTL mutation.
        burst = runpy.run_path(str(ROOT / "sw/tests/test_pcie_gen3_integrity_v23_block_burst.py"))
        burst["run_burst"](tmp_path / "burst", fault)
        return
'''
a=(B/'sources02'/miter).read_text();b=(R/miter).read_text();assert b.count(delta)==1 and b.replace(delta,'')==a
peer=load(B/'source-only-peer-vco03.json');assert peer['freeze']==pin(B/'source-freeze03.json') and not peer['findings']
assert peer['targeted_helper']==pin(B/'targeted_controls03.py') and peer['saved_positive_reader']==pin(B/'read_targeted_positive02.py')
campaigns=[]
for label,wanted in [('01',dict(passed=28,failed=7,skipped=0)),('02',dict(passed=6,failed=3,skipped=0)),('03',dict(passed=3,failed=0,skipped=0))]:
 cs,c=recount(B/f'controls{label}.xml');assert c==wanted
 status=load(B/f'controls-status{label}.json');assert status['returncode']==(0 if label=='03'else 1)
 assert status['status']==('COMPLETE_PENDING_INDEPENDENT_CONTROL_RECOUNT'if label=='03'else'FAILED_CONTROLS_RETAINED')
 campaigns.append(dict(path=str(B/f'controls{label}.xml'),**pin(B/f'controls{label}.xml'),**c,cases=[dict(name=x.get('name'),failed=any(x.find(k)is not None for k in ['failure','error']))for x in cs]))
helpers=[]
for root,revision in [(D1,1),(D2,2)]:
 for p in sorted(root.glob('*/*/result.json')):
  if p.parent.parent.is_symlink():continue
  r=load(p)
  if 'inputs'not in r or 'outputs'not in r:continue
  assert r['status']!='RUNNING'
  for n,v in r['inputs'].items():
   q=Path(n)
   if q.is_relative_to(R)and str(q.relative_to(R))in freezes[revision]['sources']:q=B/f'sources0{revision}'/q.relative_to(R)
   assert pin(q)==v,str(q)
  for n,v in r['outputs'].items():assert pin(p.parent/n)==v,n
  x=p.parent/'results.xml';helpers.append(dict(path=str(p),**pin(p),revision=revision,status=r['status'],counts=recount(x)[1]if x.is_file()else None))
for p in [D1/'test_actual_wide_rx_full_posit0/capture',D1/'test_v22_v23_cycle_exact_all_p0/capture']:assert recount(p/'results.xml')[1]==dict(passed=18,failed=0,skipped=0)
saved=load(B/'saved-targeted-positive02.json');assert saved['status']=='PASS_SAVED_NATIVE_V23_SELECTED_POSITIVES_CANONICAL_SCHEMA'and saved['source_freeze']==pin(B/'source-freeze02.json')and saved['reran_HDL']is False
for x in saved['records']:
 for k in ['result','xml','log']:assert pin(x[k]['path'])=={v:x[k][v]for v in ['bytes','sha256']}
 assert x['tests']==dict(passed=1,failed=0,skipped=17)
s=(D1/'test_v22_v23_cycle_exact_all_p0/capture/simulation.log').read_text()
x=re.search(r'V23_CACHE_QUARANTINE epochs=(\d+) actual_fault_steps=(\d+) invalid_cache_changes=(\d+)',s);assert x and list(map(int,x.groups()))==[8,8,8]
literal=[]
for p in sorted(D1.glob('test_actual_adjacent_relation_*/run.log')):
 if p.parent.is_symlink():continue
 s=p.read_text();positive='PASS_V23_ADJACENT_RELATION binary=557056 literalXZ=1440'in s
 assert positive or 'V23_ADJACENT_LITERAL case='in s
 literal.append(dict(path=str(p),**pin(p),positive=positive))
assert len(literal)==6 and sum(x['positive']for x in literal)==1
mutants=[]
diagnostics=r'(?:PCIE_CYCLE_MITER_OUTPUT_MISMATCH|PCIE_RING_CONTROL_MISMATCH|PCIE_OCCUPIED_SLOT_MISMATCH|V23_OCCUPIED_SLOT_VERDICT_MISMATCH|V23_DESCRIPTOR_OWNERSHIP_MISMATCH|V23_OWNED_DESCRIPTOR_PAYLOAD_MISMATCH|V23_FAULT_QUARANTINE_NOT_ATOMIC|V23_HEADER_BANK_RELATION|V23_FIRST_HEADER_RELATION|V23_CARRIED_HEADER_RELATION)'
for root,indices in [(D1,range(6)),(D2,[0,1,2,4,5])]:
 for i in indices:
  p=root/f'test_actual_miter_fault_is_obs{i}/capture/simulation.log';s=p.read_text();messages=re.findall(diagnostics,s);assert messages and load(p.parent/'result.json')['status']=='FAIL'
  assert(p.parent/'sim/sim.vvp').is_file();mutants.append(dict(path=str(p),**pin(p),diagnostics=sorted(set(messages))))
op=D2/'test_actual_old_predecessor_ob0/observer-capture/simulation.log';assert 'V23_OBSERVER_OLD_PREDECESSOR'in op.read_text()
burst=[]
for directory,fault in [(D3/'test_actual_block_burst_scoreb0/burst',None),(D3/'test_actual_miter_fault_is_obs0/burst','header_promote_stale')]:
 p=directory/'result.json';r=load(p);assert r['fault']==fault
 for n,v in r['inputs'].items():assert pin(n)==v,n
 for n,v in r['outputs'].items():assert pin(directory/n)==v,n
 s=(directory/'simulation.log').read_text()
 if fault:assert r['returncode']!=0 and 'V23_FRAMER_PROMOTION_RELATION'in s
 else:
  assert r['returncode']==0
  x=re.search(r'PASS_V23_FRAMER_BURST blocks=(\d+) bytes=(\d+) packets=(\d+) promotions=(\d+) changed=(\d+) concurrent=(\d+) inputstall=(\d+) outputstall=(\d+)',s);assert x
  values=list(map(int,x.groups()));assert values[:3]==[r['blocks'],r['bytes'],r['packets']]and min(values[3:])>0
 burst.append(dict(path=str(p),**pin(p),fault=fault,log=dict(path=str(directory/'simulation.log'),**pin(directory/'simulation.log'))))
assert len(mutants)==11 and len(burst)==2
entries={}
for root,label in [(D1,'initial'),(D2,'targeted02'),(D3,'targeted03')]:
 for p in root.rglob('*'):
  if p.is_file()and not p.is_symlink()and not any(q.is_symlink()for q in p.parents if q!=root.parent):entries['raw/'+label+'/'+str(p.relative_to(root))]=p
for n in freezes[3]['sources']:entries['sources/'+n]=R/n
for p in B.rglob('*'):
 if p.is_file()and not p.is_symlink()and p.suffix not in('.xz','.gz')and p.name not in ['active-checkpoint.json','seal-controls03.log']:
  entries['evidence/'+str(p.relative_to(B))]=p
manifest={n:dict(original=str(p),**pin(p))for n,p in sorted(entries.items())}
archive=B/'pcie-integrity-v23-composite-controls-20261006.tar.xz';assert not archive.exists()
with tarfile.open(archive,'w:xz',preset=1)as t:
 for n,p in sorted(entries.items()):t.add(p,arcname=n,recursive=False)
 raw=(json.dumps(manifest,indent=2)+'\n').encode();i=tarfile.TarInfo('members.json');i.size=len(raw);t.addfile(i,io.BytesIO(raw))
seen=set()
with tarfile.open(archive,'r:xz')as t:
 for i in t:
  assert i.isfile()and i.name not in seen;seen.add(i.name);raw=t.extractfile(i).read()
  if i.name=='members.json':assert json.loads(raw)==manifest
  else:assert len(raw)==manifest[i.name]['bytes']and hashlib.sha256(raw).hexdigest()==manifest[i.name]['sha256']
assert len(seen)==len(manifest)+1
for n,p in entries.items():assert pin(p)=={k:manifest[n][k]for k in ['bytes','sha256']}
r=dict(status='PASS_V23_ADJACENT_HEADER_COMPOSITE_CONTROLS',source_freeze=pin(B/'source-freeze03.json'),source_peer=pin(B/'source-only-peer-vco03.json'),campaigns=campaigns,pytest_executions=47,passed_executions=37,historical_failed_executions=10,public_positive_composite=dict(original_unchanged_cases=17,targeted_corrected_case=1,complete_direct_profile_rerun=False,complete_cycle_miter_profile_rerun=False,prior_full_cases=18),saved_selected_positives=pin(B/'saved-targeted-positive02.json'),adjacent_witness=saved['records'][1]['witness'],cache_fault_write_epochs=8,literal_controls=literal,meaningful_miter_mutants=mutants,promotion_burst=burst,observer_negative=dict(path=str(op),**pin(op)),helper_receipts=helpers,archive=dict(path=str(archive),**pin(archive)),members=len(seen),full_member_readback=True,all_original_pins_rechecked=True,MAX4118_profile_excluded=True,physical_acceptance=False,scope='Unchanged RTL across three frozen harness revisions. Retains28PASS7FAIL and6PASS3FAIL including surviving wrapper-cadence promotion mutant; saved positive schema recounted without rerun, real framer burst catches exact same promotion mutation. Full original18-case wrapper positives plus targeted revised18th positives,17 unchanged cases,557056binary/1440four-state tuples and five literal faults,12 product mutations,11 wrapper miter mutations plus1 real block-port promotion mutation. No timing/fullPHY/manufacturing acceptance.')
p=B/'pcie-integrity-v23-composite-controls-validation-20261006.json';assert not p.exists();p.write_text(json.dumps(r,indent=2)+'\n');print(r['status'],pin(archive),len(seen),pin(p))
