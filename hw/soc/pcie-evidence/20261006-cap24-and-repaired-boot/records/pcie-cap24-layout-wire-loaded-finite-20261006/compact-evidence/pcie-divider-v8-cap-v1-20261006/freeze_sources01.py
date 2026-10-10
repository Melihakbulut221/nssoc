from pathlib import Path
import ast,difflib,hashlib,json
R=Path.cwd();B=Path(__file__).resolve().parent;P=B.with_name('pcie-divider-v7-compact-v2-20261006')
def pin(p):
 p=Path(p);b=p.read_bytes();return dict(bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
files=[f'hw/soc/flow/{x}_pcie_clock_div4_v7_compact_v2.py'for x in ['make','check','audit']]+[f'sw/tests/test_pcie_clock_div4_v7_compact_v2_{x}.py'for x in ['layout','native']]
pairs=[(R/p,R/p.replace('v7_compact_v2','v8_cap_v1'))for p in files]+[(R/'hw/soc/analog/pcie/clock_div4_hbt_v7.spice',R/'hw/soc/analog/pcie/clock_div4_hbt_v8.spice')]
for name in ['launch01.py','prepare_launch01.py']:
 s=(P/name).read_text().replace('V7_COMPACT_V2','V8_CAP_V1').replace('v7_compact_v2','v8_cap_v1').replace('nssoc-div4-v7-compact-v2-','nssoc-div4-v8-cap-v1-').replace('source-only-peer01-pll.json','source-only-peer01-rx.json')
 (B/name).write_text(s);pairs.append((P/name,B/name))
bridges=[]
for old,new in pairs:
 a,b=old.read_text().splitlines(keepends=True),new.read_text().splitlines(keepends=True)
 bridges.append(dict(before=dict(path=str(old),**pin(old)),after=dict(path=str(new),**pin(new)),opcodes=[dict(tag=t,before=''.join(a[i:j]),after=''.join(b[k:l]))for t,i,j,k,l in difflib.SequenceMatcher(None,a,b,autojunk=False).get_opcodes()]))
(B/'source-bridge01.json').write_text(json.dumps(bridges,indent=2)+'\n')
f=json.loads((P/'source-freeze01.json').read_text());inputs=dict(f['inputs']);assert inputs=={p:pin(p)for p in inputs}
for folder in [B,P/'native03-peer-rx']:
 if folder.exists():
  for p in folder.rglob('*'):
   if p.is_file() and '__pycache__' not in p.parts and p.name!='source-freeze01.json':inputs[str(p)]=pin(p)
for p in [P/'source-freeze01.json',P/'native-saved-peer-rx.json',Path('/dev/shm/nssoc-div4-v7-compact-v2-layout-01/result.json'),Path('/dev/shm/nssoc-div4-v7-compact-v2-layout-01/nssoc_clock_div4_v7_compact_v2_layout.gds')]:inputs[str(p)]=pin(p)
for old,new in pairs:inputs[str(old)]=pin(old);inputs[str(new)]=pin(new)
products={str(new):pin(new)for old,new in pairs[:6]}
functions=lambda p:{n.name:ast.dump(n,include_attributes=False)for n in ast.parse(p.read_text()).body if isinstance(n,(ast.FunctionDef,ast.ClassDef))}
a=functions(pairs[1][0]);b=functions(pairs[1][1]);expected=['main','fault_reference'];assert [n for n in a if a[n]!=b[n]]==['fault_reference','main']
out=dict(f,status='FROZEN_CAP24_TWO_NATIVE_MIM_CHANGE_REQUIRES_PEER_AND_NATIVE',inputs=inputs,product_sources=products,launcher=pin(B/'launch01.py'),layout='/dev/shm/nssoc-div4-v8-cap-v1-layout-01',checks='/dev/shm/nssoc-div4-v8-cap-v1-checks-01',control_status='62 current source/lifecycle controls; earlier59PASS2FAIL and61PASS1FAIL retained. Two original20um MIMs now24um, exact36um pitch and Decimal2.4um conservative escape gap. Actual fresh native geometry/DRC/LVS and electrical behavior unmeasured.',scope='Only XCP/XCN physical MIM geometry changes. All other89 intrinsic geometries/connections/DCbias,18contacts and634via geometry multiset remain strict. Independent PDK Decimal MIM rectangle formula includes all actual cut/enclosure polygons; two new meaningful geometry faults added to original four. Original21 native gates and CPU10 resources/lifecycle unchanged. No generated native yet.')
assert '62 passed' in (B/'source-controls04.log').read_text()
(B/'source-freeze01.json').write_text(json.dumps(out,indent=2)+'\n');print(len(inputs),pin(B/'source-freeze01.json'))
