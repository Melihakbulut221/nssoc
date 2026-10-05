# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Saved input/source-only review; no binder or native execution."""
from pathlib import Path
import ast,hashlib,json
B=Path(__file__).resolve().parent;W=B.parent

def pin(p):
 p=Path(p)
 with p.open('rb') as stream:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(stream,'sha256').hexdigest())
f=json.loads((B/'source-freeze.json').read_text())
assert pin(B/'source-freeze.json')==dict(bytes=29472,sha256='721a005163fa62676bca2a10cb3b8a87f563cbfbb577114ef03d676b4fe336d5')
assert f['inputs']=={p:pin(p) for p in f['inputs']}
assert f['method']==pin(B/'run.py')
g=json.loads((W/'geometry-execution.json').read_text());assert g['status']=='PASS_DIVIDER_V7_SAVED_NATIVE_GEOMETRY_AND_SOURCE_BIJECTION_ONLY'
assert g['outputs']=={p:pin(p) for p in g['outputs']}
s=(B/'run.py').read_text();ast.parse(s)
old=(W/'run_geometry.py').read_text()
for tag in ["names = {'require', 'atomic', 'lifecycle', 'limits', 'scratch_bytes',", "selected = [n for n in ast.parse(CHECKER.read_text()).body", "LIFECYCLE_SHA='39312e364fa2a788784d88f3a63845f64db25bb420e2ee5d58c07a8c805bc886'",'SCRATCH_LIMIT=80 * 1024**2, SHARED_FLOOR=512 * 1024**2,','ENTRY_FREE=1024**3, LAUNCH_RESERVATION=24 * 1024**2,']:
 assert tag in s and tag in old
source=(W/'bind_source_ids.py').read_text();assert source.count("G=Path('/dev/shm/nssoc-div4-v7-layout-01')")==1
assert "assert len(rows)==len(used)==len(g['instances'])==91" in source
assert 'assert len(net_map)==len(reverse)==38' in source
assert 'assert all(len(v)==1 for v in net_map.values())' in source
R=Path('/dev/shm/nssoc-div4-v7-layout-01');ref=json.loads((R/'result.json').read_text());native=json.loads((W/'device-location-geometry.json').read_text())
cl=[r for r in ref['instances'] if r['name']=='DIV__XFIRST__XSP'];assert len(cl)==1 and cl[0]['nets'][0]=='CLKP'
up=[r for r in ref['instances'] if r['name']=='DIV__XFIRST__XUP'];assert len(up)==1 and up[0]['length_um']==4.0
assert sum(r['name']=='TAP0' for r in ref['instances'])==1
caps=[r for r in native['devices'] if r['model']=='cap_cmim'];assert len(caps)==6 and caps[0]['parameters']['A']>0
# The source rechecks each expected pre-edit value, counts exact one structural
# difference, requires inverse complete bytes and preserves source/native inputs.
result=dict(status='PASS_SOURCE_ONLY_DIVIDER_V7_BINDING_CONTROLS',findings=[],freeze=pin(B/'source-freeze.json'),method=pin(__file__),producer=pin(B/'run.py'),inputs_rehashed=len(f['inputs']),geometry_execution=pin(W/'geometry-execution.json'),geometry_output_count=len(g['outputs']),review=['Five copied-input runs only: exact positive, single CLKP reference reassignment, one physical resistor reference length, exactly one finite tap removal, and one native MIM area corruption.','No real design mutation or new extraction; test name reference_clock_swap is a one-terminal reference reassignment, not a simulated differential clock interchange.','Each binder copy changes only fixture G root and asserts byte-exact inverse. All source/device/net/parameter/location predicates remain exact production bytes.','Positive compares complete semantic output excluding provenance paths. Each negative requires returncode1, no output, actual traceback and its specific production assertion, preventing compiler/runtime errors from masquerading as rejection.','Exact already-reviewed seven lifecycle function ASTs privately cloned; unchanged CPU10,2GiB and scratch floors, completion/teardown guards.','All saved source pins and completed positive geometry outputs checked; actual five run results still pending.'],reviewed_method_or_native_executed=False,scope='Source-only harness peer; four faults exercise binding/reference checks, not actual electrical faults. No RC/timing/qualifiedPEX acceptance.')
assert not (B/'source-only-peer.json').exists();(B/'source-only-peer.json').write_text(json.dumps(result,indent=2)+'\n');print(result['status'],pin(B/'source-only-peer.json'))
