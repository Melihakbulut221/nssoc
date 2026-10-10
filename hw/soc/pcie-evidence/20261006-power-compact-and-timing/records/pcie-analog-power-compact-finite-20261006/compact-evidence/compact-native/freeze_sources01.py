from pathlib import Path
import hashlib,json,difflib,ast
R=Path.cwd();B=Path(__file__).resolve().parent;P=B.with_name('pcie-divider-v7-compact-v1-20261006')
def pin(p):
 p=Path(p)
 with p.open('rb') as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
files=[f'hw/soc/flow/{x}_pcie_clock_div4_v7_compact_v1.py' for x in ['make','check','audit']]+[f'sw/tests/test_pcie_clock_div4_v7_compact_v1_{x}.py' for x in ['layout','native']]
pairs=[(R/p,R/p.replace('compact_v1','compact_v2')) for p in files]+[(P/n,B/n) for n in ['launch01.py','prepare_launch01.py']]
bridges=[]
for old,new in pairs:
 a,b=old.read_text().splitlines(keepends=True),new.read_text().splitlines(keepends=True)
 bridges.append(dict(before=dict(path=str(old),**pin(old)),after=dict(path=str(new),**pin(new)),opcodes=[dict(tag=t,before=''.join(a[i:j]),after=''.join(b[k:l])) for t,i,j,k,l in difflib.SequenceMatcher(None,a,b,autojunk=False).get_opcodes()]))
(B/'source-bridge01.json').write_text(json.dumps(bridges,indent=2)+'\n')
f=json.loads((P/'source-freeze01.json').read_text());inputs=dict(f['inputs']);assert inputs=={p:pin(p) for p in inputs}
for p in [*B.rglob('*'),P/'source-freeze01.json',P/'self-review-tap-lane-collision.json',P/'prepare_launch01.py']:
 if p.is_file() and '__pycache__' not in p.parts:inputs[str(p)]=pin(p)
for old,new in pairs:inputs[str(old)]=pin(old);inputs[str(new)]=pin(new)
products={str(new):pin(new) for old,new in pairs[:5]}
out=dict(f,status='FROZEN_COMPACT_V2_SAFE_TAP_LANES_SOURCE_ONLY_REQUIRES_PEER_AND_NATIVE',inputs=inputs,product_sources=products,launcher=pin(B/'launch01.py'),layout='/dev/shm/nssoc-div4-v7-compact-v2-layout-01',checks='/dev/shm/nssoc-div4-v7-compact-v2-checks-01',control_status='61 source/lifecycle controls passed; prior expected-row and false first collision witness errors retained. Actual12 oldtap collisions eliminated by all18 newpositions with minimum4um escape-center clearance.',scope='Separately versioned compactV2: all91intrinsic geometries/topology,18physical contacts and634via geometry multiset unchanged; shortened routing/compactplacements and correctedtap lane coordinates require actual freshDRC/LVS/RC/loaded455. No native generated.')
(B/'source-freeze01.json').write_text(json.dumps(out,indent=2)+'\n');print(len(inputs),pin(B/'source-freeze01.json'))
