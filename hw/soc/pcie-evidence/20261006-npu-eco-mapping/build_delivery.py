# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Publish finite native mapping records, preserving all acceptance boundaries."""
from pathlib import Path
import json,hashlib,tarfile
R=Path.cwd();B=R/'hw/soc/out/npu-eco-mapping-20261006';D=Path(__file__).absolute().parent;C=R/'hw/soc/pcie-evidence/20261006-npu-eco-mapping';assert not C.exists()
def pin(p):
 p=Path(p)
 with p.open('rb') as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
p=json.loads((B/'package01.json').read_text());public=json.loads((B/'release01.json').read_text());native=json.loads((B/'native01/result.json').read_text());assert public['status']=='PASS_IMMUTABLE_RELEASE_ROUNDTRIPS'
assert native['status']=='PASS_MATCHED32SRAM_MAPPING_AND_EXACT_ECO_BRIDGE_BOOT_PHYSICAL_PENDING'
seen={}
with tarfile.open(p['archive']['path'],'r:xz') as tar:
 for m in tar:
  assert m.isfile() and m.name not in seen
  with tar.extractfile(m) as f:h=hashlib.file_digest(f,'sha256').hexdigest()
  assert dict(bytes=m.size,sha256=h)=={k:p['members'][m.name][k] for k in ('bytes','sha256')};seen[m.name]=True
assert set(seen)==set(p['members']) and len(seen)==187
for asset in public['assets']:assert asset['authenticated_roundtrip'] and asset['anonymous_roundtrip']
assert pin(Path(p['archive']['path']))=={k:public['assets'][0][k] for k in ('bytes','sha256')}
files={}
for path in B.iterdir():
 if path.is_file() and path.suffix in ('.py','.json','.log') and not path.name.startswith('seal-launch'):files[path.name]=path
for variant in ('original','candidate','factored'):
 for name in ('map.ys','native.log'):files['native/'+variant+'/'+name]=B/'native01'/variant/name
files['native/result.json']=B/'native01/result.json';files['build_delivery.py']=Path(__file__).absolute()
C.mkdir(parents=True);copied={}
for name,path in sorted(files.items()):
 q=C/name;q.parent.mkdir(parents=True,exist_ok=True);q.write_bytes(path.read_bytes());assert pin(q)==pin(path);copied[name]=dict(source=str(path.relative_to(R)),**pin(q))
 license='Apache-2.0' if q.suffix=='.py' else 'CERN-OHL-W-2.0' if q.suffix=='.ys' else 'CC-BY-4.0'
 Path(str(q)+'.license').write_text('SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut\nSPDX-License-Identifier: '+license+'\n')
sources={s:pin(R/s) for s in ['scripts/check_npu_physical_eco_mapping.py','sw/tests/test_npu_physical_eco_mapping.py']}
dictout=dict(status='PASS_THREE_NATIVE_SRAM_MAPS_AND_FULL_EXACT_ECO_BRIDGE',sources=sources,compact_files=copied,archive=p['archive'],members=187,assets=public['assets'],native_stages={name:{k:r[k] for k in ('status','returncode','netlist','elapsed_seconds')} for name,r in native['stages'].items()},bridge=native['exact_combinational_bridge'],fixture_graph_controls_passed=17,actual_saved_graph_faults_rejected=3,capture_boundary=json.loads((B/'nssoc-npu-eco-sram-mapping-validation-20261006.json').read_text())['capture_boundary'],candidate_adopted=False,full_soc_functional_accepted=False,timing_accepted=False,manufacturing_approval=False,scope='No new formal fullchip/boot/physical run. Exactunchanged oldbaselines andnewfactored32SRAM native mapping plus complete retainedcell equations; strictboot andphysical/proof prerequisites stayopen.')
p=R/'docs/evidence/npu-eco-sram-mapping-20261006.json';p.write_text(json.dumps(dictout,indent=2)+'\n');(D/'source-allowlist.json').write_text(json.dumps(sources,indent=2)+'\n');(D/'evidence-allowlist.json').write_text(json.dumps({str(p.relative_to(R)):pin(p) for p in C.rglob('*') if p.is_file()},indent=2)+'\n');print(json.dumps(dict(sources=len(sources),compact=len(copied),members=187,stage_times={n:r['elapsed_seconds'] for n,r in native['stages'].items()})))
