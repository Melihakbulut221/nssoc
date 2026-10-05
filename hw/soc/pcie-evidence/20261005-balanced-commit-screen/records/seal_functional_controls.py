"""Combine completed corrected focused and public controls, never pending PASS."""
from pathlib import Path
import hashlib,json,tarfile,runpy
R=Path.cwd();B=Path(__file__).resolve().parent

def pin(p):
 with Path(p).open('rb') as f:return dict(bytes=Path(p).stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
# Root supplies this binding only after its actual corrected focused validation.
gate=json.loads((B/'functional-ready-inputs.json').read_text());approved=Path(gate['root_focused_validation']['path'])
assert pin(approved)=={k:gate['root_focused_validation'][k] for k in ['bytes','sha256']}
assert json.loads(approved.read_text())['status']==gate['root_focused_validation']['status']
assert gate['root_focused_validation']['status'].startswith('PASS_')
assert '8 passed' in (B/'commit-controls02.log').read_text()
assert '13 passed, 2 deselected' in (B/'public-controls01.log').read_text()
f=json.loads((B/'source-freeze.json').read_text())
for n,v in f['files'].items():assert pin(R/n)==v
peer=json.loads((B/'source-only-peer-pll02.json').read_text());assert peer['status']=='PASS_V18_FINAL_SOURCE_AND_CORRECTED_FOCUSED_HARNESS_PEER' and peer['source_freeze']==pin(B/'source-freeze.json')
public=json.loads((B/'public-controls-validation01.json').read_text());assert public['status']=='PASS_V18_PUBLIC_CYCLE_MITER_ORACLE_AND_ACTUAL_FAULT_CONTROLS' and public['pytest_executions']==13
H=runpy.run_path(str(R/'sw/tests/test_pcie_gen3_integrity_v18_commit.py'));body=(R/'hw/soc/rtl/pcie/soc_pcie_gen3_framer_rx_integrity_v18.v').read_text();bench=H['parser_miter']();D=Path('/dev/shm/nssoc-integrity-v18-commit-controls02');rows=[]
for index,fault in enumerate([None,*H['FAULTS']]):
 folder=D/('test_actual_complete_parser_ar'+str(index));expected=body
 if fault:
  before,after=H['FAULTS'][fault];assert expected.count(before)==1;expected=expected.replace(before,after)
 assert (folder/'candidate.v').read_text()==expected and (folder/'tb.v').read_text()==bench
 assert (folder/'sim.vvp').is_file()
 log=(folder/'run.log').read_text()
 if fault:assert 'PARSER_ARBITRARY_STATE_MISMATCH' in log and 'PASS 32768 ACTUAL_FULL_PARSER_CASES' not in log
 else:assert 'PASS 32768 ACTUAL_FULL_PARSER_CASES' in log and 'PARSER_ARBITRARY_STATE_MISMATCH' not in log
 rows.append(dict(fault=fault,path=str(folder),run_log=pin(folder/'run.log'),candidate=pin(folder/'candidate.v'),bench=pin(folder/'tb.v')))
files={}
for n in f['files']:files['source/'+n]=R/n
for n in ['source-freeze.json','source-public-freeze01.json','source-only-peer-pll01.json','source-only-peer-pll02.json','source_only_peer_pll03.py','source_only_peer_pll04.py','source-peer-attempt03.log','source-peer-attempt04.log','commit-controls01-harness-preservation.json','commit-controls01-source.py','commit-controls01-superseded.json','commit-controls01.log','commit-controls02.log','public-controls01.log','public-controls-validation01.json','functional-ready-inputs.json','seal_functional_controls.py']:files['method/'+n]=B/n
files['method/root-focused-validation.json']=approved
files['public/'+Path(public['archive']['path']).name]=Path(public['archive']['path'])
for root in [D,Path('/dev/shm/nssoc-integrity-v18-commit-controls01')]:
 for p in root.rglob('*'):
  if p.is_file() and not p.is_symlink() and not any(q.is_symlink() for q in p.parents if q!=root):files['focused/'+root.name+'/'+str(p.relative_to(root))]=p
m={n:dict(original_path=str(p),**pin(p)) for n,p in sorted(files.items())};mp=B/'functional-controls-members.json';assert not mp.exists();mp.write_text(json.dumps(m,indent=2)+'\n');a=B/'pcie-integrity-v18-combined-functional-controls-20261005.tar.xz';assert not a.exists()
with tarfile.open(a,'w:xz',preset=3) as t:
 for n,p in sorted(files.items()):t.add(p,arcname=n,recursive=False)
 t.add(mp,arcname='members.json',recursive=False)
with tarfile.open(a,'r:xz') as t:
 assert set(t.getnames())==set(m)|{'members.json'}
 for member in t.getmembers():
  expected=pin(mp) if member.name=='members.json' else m[member.name];assert member.isfile() and member.size==expected['bytes']
  with t.extractfile(member) as stream:assert hashlib.file_digest(stream,'sha256').hexdigest()==expected['sha256']
x=dict(status='PASS_BALANCED_COMMIT_AND_ACTUAL_PUBLIC_FAULT_CONTROLS',source_freeze=pin(B/'source-freeze.json'),source_peer=pin(B/'source-only-peer-pll02.json'),pytest_executions=21,distinct_predicates=20,duplicate_predicate='Exact inverse helper independently and through public miter module.',positive_public_cases=26,actual_RTL_mutants=16,corrected_full_parser_cases=32768,parser_outputs=28,excluded_MAX4118_ids=2,skipped=0,focused_rows=rows,public_receipt=pin(B/'public-controls-validation01.json'),root_focused_validation=gate['root_focused_validation'],archive=dict(path=str(a),**pin(a),members=len(m)+1),full_readback=True,scope='Completed corrected8 focused plus13public predicates, two explicit MAX4118 exclusions. Corrected first16384 cover all4states×8^4token combinations; secondhalf adds unknown controls. Six commit faults and ten public/miter/CRC/parser faults detected. Original correlated-stimulus campaign and equivalent upper-value Z mutant remain superseded, not counted as completed coverage. No native mapping or physical timing acceptance.')
p=B/'pcie-integrity-v18-core-controls-validation-20261005.json';assert not p.exists();p.write_text(json.dumps(x,indent=2)+'\n');print(json.dumps({'archive':x['archive'],'validation':pin(p)}))
