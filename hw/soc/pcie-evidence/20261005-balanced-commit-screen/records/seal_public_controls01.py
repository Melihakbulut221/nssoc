"""Seal completed public controls independently of evolving focused stimuli."""
from pathlib import Path
import ast,hashlib,json,tarfile,xml.etree.ElementTree as ET
R=Path.cwd();B=Path(__file__).resolve().parent;D=Path('/dev/shm/nssoc-integrity-v18-public-controls01')
def pin(p):
 with p.open('rb') as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
assert '13 passed, 2 deselected' in (B/'public-controls01.log').read_text()
f=json.loads((B/'source-public-freeze01.json').read_text())
for n,v in f['files'].items():assert pin(R/n)==v
focused=R/'sw/tests/test_pcie_gen3_integrity_v18_commit.py';text=focused.read_text();module=ast.parse(text)
helper=next(n for n in module.body if isinstance(n,ast.FunctionDef) and n.name=='test_exact_generated_inverse_and_wrapper_bridge');h=ast.get_source_segment(text,helper)
assert dict(bytes=len(h.encode()),sha256=hashlib.sha256(h.encode()).hexdigest(),AST_sha256=hashlib.sha256(ast.dump(helper,include_attributes=False).encode()).hexdigest())==f['frozen_inverse_helper']
snapshot=Path(f['live_focused_harness_snapshot']['path']);assert pin(snapshot)=={k:f['live_focused_harness_snapshot'][k] for k in ['bytes','sha256']}
prior=ast.parse(snapshot.read_text())
def globals_used(m):return {node.targets[0].id:ast.dump(node,include_attributes=False) for node in m.body if isinstance(node,ast.Assign) and isinstance(node.targets[0],ast.Name) and node.targets[0].id in ['ROOT','RTL','GEN']}
assert globals_used(module)==globals_used(prior) and len(globals_used(module))==3
rows=[]
for name in ['test_v11_v18_cycle_exact_all_p0','test_actual_wide_rx_full_posit0']:
 p=D/name/'capture/results.xml';cases=ET.parse(p).findall('.//testcase');assert len(cases)==13 and all(c.find('failure') is None and c.find('error') is None and c.find('skipped') is None for c in cases)
 result=json.loads((p.parent/'result.json').read_text());assert result['status']=='PASS_PORT_ONLY_PCIE_GEN3_WIDE_CRC_QUARANTINE_RX' and result['tests']==dict(passed=13,failed=0,skipped=0)
 rows.append(dict(path=str(p),**pin(p),passed=13))
files={}
for n in f['files']:files['source/'+n]=R/n
for n in ['source-public-freeze01.json','source-only-peer-pll01.json','source_only_peer_pll01.py','source_only_peer_pll02.py','source-peer-attempt01.log','source-peer-attempt02.log','focused-harness-snapshot-public01.py','public-controls01.log','seal_public_controls01.py']:files['method/'+n]=B/n
for p in D.rglob('*'):
 if p.is_file() and not p.is_symlink() and not any(q.is_symlink() for q in p.parents if q!=D):files['controls/'+str(p.relative_to(D))]=p
m={n:dict(original_path=str(p),**pin(p)) for n,p in sorted(files.items())};mp=B/'public-controls-members01.json';assert not mp.exists();mp.write_text(json.dumps(m,indent=2)+'\n');a=B/'pcie-integrity-v18-public-controls-20261005.tar.xz';assert not a.exists()
with tarfile.open(a,'w:xz',preset=3) as t:
 for n,p in sorted(files.items()):t.add(p,arcname=n,recursive=False)
 t.add(mp,arcname='members.json',recursive=False)
with tarfile.open(a,'r:xz') as t:
 assert set(t.getnames())==set(m)|{'members.json'}
 for member in t.getmembers():
  expected=pin(mp) if member.name=='members.json' else m[member.name];assert member.isfile() and member.size==expected['bytes']
  with t.extractfile(member) as stream:assert hashlib.file_digest(stream,'sha256').hexdigest()==expected['sha256']
r=dict(status='PASS_V18_PUBLIC_CYCLE_MITER_ORACLE_AND_ACTUAL_FAULT_CONTROLS',pytest_executions=13,positive_public_cases=26,actual_RTL_mutants=10,excluded_MAX4118_ids=2,skipped=0,source_freeze=pin(B/'source-public-freeze01.json'),source_peer=pin(B/'source-only-peer-pll01.json'),inverse_helper_and_required_globals_unchanged=True,focused_harness_at_seal=pin(focused),xml_recount=rows,archive=dict(path=str(a),**pin(a),members=len(m)+1),full_readback=True,scope='Independent full public/miter/oracle profile at MAX150. All8main/publicsources and exactinversehelper/globaldependencies stable. Focused arbitrary-state harness is separately owned and evolving; nofocused/mapped/physical acceptance implied. No completed tests rerun.')
p=B/'public-controls-validation01.json';p.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({'archive':r['archive'],'validation':pin(p)}))
