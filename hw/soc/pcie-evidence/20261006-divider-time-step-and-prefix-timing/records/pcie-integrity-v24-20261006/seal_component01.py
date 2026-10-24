from pathlib import Path
import datetime,hashlib,json,tarfile,io,xml.etree.ElementTree as ET,re
R=Path.cwd();B=Path(__file__).resolve().parent;D=Path('/dev/shm/nssoc-integrity-v24-matrix-controls01')
def pin(p):
 p=Path(p)
 with p.open('rb')as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
f=B/'component-source-freeze02.json';freeze=json.loads(f.read_text())
for name,h in freeze['sources'].items():assert pin(name)==h
status=json.loads((B/'component-status01.json').read_text());assert status['status']=='COMPLETE_PENDING_INDEPENDENT_CONTROL_RECOUNT'and status['returncode']==0 and not status['stop_reason']
for v in [status['controller'],status['pytest']]:
 p=Path('/proc')/str(v['pid'])/'stat'
 assert not p.exists()or p.read_text().rsplit(') ',1)[1].split()[19]!=v['start_ticks']
cases=list(ET.parse(B/'component-controls01.xml').getroot().iter('testcase'));assert len(cases)==5 and all(not len(c)for c in cases)
paths={}
for p in sorted(D.iterdir()):
 if p.is_dir()and not p.is_symlink():
  for q in p.rglob('*'):
   assert not q.is_symlink()
   if q.is_file():paths['native/'+str(q.relative_to(D))]=q
raw=[]
for i in range(5):
 p=D/f'test_actual_finite_matrix_alph{i}'/'run.log';t=p.read_text();assert 'V24_ALPHABET vectors=16384 token_matrices=13 carry_columns=4 initial_modes=9 complete_matrices=52'in t
 if i==0:assert 'V24_PREFIX_RELATION_PASS matrices=140608 comparisons=3796416'in t
 else:assert 'FATAL:'in t and 'V24_PREFIX_RELATION word='in t
 raw.append(dict(path=str(p),**pin(p),positive=i==0,diagnostic=t))
for p in B.iterdir():
 if p.is_file()and(p.name.startswith(('component-','review_component','launch_component','detach_component','architecture-','review_architecture'))or p.name in ('prefix_candidate01.vh','test_matrix_relation01.py','seal_component01.py'))and p.suffix in('.json','.py','.log','.xml','.vh'):
  paths['evidence/'+p.name]=p
for name in freeze['sources']:
 p=Path(name)
 if str(p).startswith(str(R))and not str(p).startswith(str(B)):
  paths['sources/'+str(p.relative_to(R))]=p
members={name:dict(original=str(p),**pin(p))for name,p in sorted(paths.items())}
archive=B/'pcie-integrity-v24-component-controls-20261006.tar.xz';assert not archive.exists()
manifest=json.dumps(members,indent=2).encode()+b'\n'
with tarfile.open(archive,'w:xz')as tar:
 for name,p in sorted(paths.items()):assert pin(p)=={k:members[name][k]for k in('bytes','sha256')};tar.add(p,arcname=name,recursive=False)
 info=tarfile.TarInfo('members.json');info.size=len(manifest);tar.addfile(info,io.BytesIO(manifest))
seen=set()
with tarfile.open(archive,'r:xz')as tar:
 for m in tar:
  assert m.isfile()and m.name not in seen;seen.add(m.name);data=tar.extractfile(m).read()
  if m.name=='members.json':assert data==manifest
  else:assert dict(bytes=len(data),sha256=hashlib.sha256(data).hexdigest())=={k:members[m.name][k]for k in('bytes','sha256')}
assert seen==set(members)|{'members.json'}
(B/'component-members01.json').write_bytes(manifest)
q=dict(status='PASS_SAVED_V24_COMPONENT_5_CONTROLS_AND_FULL_MEMBER_READBACK',utc=datetime.datetime.now(datetime.UTC).isoformat(),source_freeze=pin(f),controller_status=pin(B/'component-status01.json'),pytest_xml=pin(B/'component-controls01.xml'),pytest_cases=[c.attrib for c in cases],raw_cases=raw,archive=dict(path=str(archive),members=len(seen),**pin(archive)),member_manifest=pin(B/'component-members01.json'),method=pin(Path(__file__)),predicate=dict(literal_input_classifications=16384,token_matrices=13,carry_columns=4,initial_modes=9,ordered_matrix_triples=140608,mode_comparisons=3796416,actual_mutants=4),full_product_acceptance=False,scope='Standalone actual HDL finite relation plus4 meaningful negatives only; frozen original01 launcher findings retained. Product V24 bank implementation and physical timing are separate pending gates. Native capture archived losslessly without rerun; runtime external pins retained in freeze.')
(B/'component-validation01.json').write_text(json.dumps(q,indent=2)+'\n');print(q['status'],q['archive'])
