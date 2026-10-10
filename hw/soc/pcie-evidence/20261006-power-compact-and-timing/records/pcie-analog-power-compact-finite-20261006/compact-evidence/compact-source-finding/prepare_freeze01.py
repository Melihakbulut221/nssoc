from pathlib import Path
import hashlib,json,difflib,ast
R=Path.cwd();B=Path(__file__).resolve().parent;P=R/'hw/soc/out/pcie-divider-v7-power-v1-20261005'
def pin(p):
 p=Path(p)
 with p.open('rb') as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
p=P/'launch03.py';q=B/'launch01.py';s=p.read_text().replace('launch-manifest03.json','launch-manifest01.json').replace('identity-checkpoint03.json','identity-checkpoint01.json').replace('PASS_SOURCE_ONLY_DIVIDER_V7_POWER_V2_AUDIT_V3','PASS_SOURCE_ONLY_DIVIDER_V7_COMPACT_V1').replace('check_pcie_clock_div4_v7_power_v2_audit_v3.py','check_pcie_clock_div4_v7_compact_v1.py').replace("if not roots[0].is_dir() or roots[1].exists() or any(p.parent != Path('/dev/shm') or not p.name.startswith('nssoc-div4-v7-power-v2-') for p in roots):", "if any(p.exists() or p.parent != Path('/dev/shm') or not p.name.startswith('nssoc-div4-v7-compact-v1-') for p in roots):").replace('Exact saved generated layout and fresh native checker root required','Both compact native roots must be fresh')
a="    if {str(p.relative_to(roots[0])):pin(p) for p in roots[0].rglob('*') if p.is_file()} != manifest['layout_files']:\n        raise ValueError('Every actual generated layout byte remains exact')\n";assert a in s;s=s.replace(a,"")
s=s.replace("'--layout', manifest['layout'], '--out', manifest['checks']]", "'--layout', manifest['layout'], '--out', manifest['checks'], '--generate']")
s=s.replace("    roots = [Path(manifest[n]) for n in ('layout', 'checks')]", "    if manifest['boot_id'] != Path('/proc/sys/kernel/random/boot_id').read_text().strip():\n        raise ValueError('Same prepared boot identity required')\n    roots = [Path(manifest[n]) for n in ('layout', 'checks')]")
q.write_text(s)
pairs=[(R/'hw/soc/flow/make_pcie_clock_div4_v7_power_v2.py',R/'hw/soc/flow/make_pcie_clock_div4_v7_compact_v1.py'),(R/'hw/soc/flow/check_pcie_clock_div4_v7_power_v2_audit_v3.py',R/'hw/soc/flow/check_pcie_clock_div4_v7_compact_v1.py'),(R/'hw/soc/flow/audit_pcie_clock_div4_v7_power_v3.py',R/'hw/soc/flow/audit_pcie_clock_div4_v7_compact_v1.py'),(R/'sw/tests/test_pcie_clock_div4_v7_power_v2_layout.py',R/'sw/tests/test_pcie_clock_div4_v7_compact_v1_layout.py'),(R/'sw/tests/test_pcie_clock_div4_v7_power_v2_native.py',R/'sw/tests/test_pcie_clock_div4_v7_compact_v1_native.py'),(P/'launch03.py',B/'launch01.py')]
bridges=[]
for old,new in pairs:
 a,b=old.read_text().splitlines(keepends=True),new.read_text().splitlines(keepends=True)
 bridges.append(dict(before=dict(path=str(old),**pin(old)),after=dict(path=str(new),**pin(new)),opcodes=[dict(tag=t,before=''.join(a[i:j]),after=''.join(b[k:l])) for t,i,j,k,l in difflib.SequenceMatcher(None,a,b,autojunk=False).get_opcodes()]))
(B/'source-bridge01.json').write_text(json.dumps(bridges,indent=2)+'\n')
# Verify all previous checked dependencies are still exact. This includes original
# primitive/native references, 90 PDK inputs, deck locks, owner and EDA runtimes.
f=json.loads((P/'source-freeze03.json').read_text());inputs=dict(f['inputs']);assert inputs=={p:pin(p) for p in inputs}
for p in [*B.rglob('*'),P/'source-freeze03.json',P/'native03-saved-peer-rx.json',P/'native03-finite-review-ready.json',P/'launch-runtime-freeze02.json']:
 if p.is_file() and '__pycache__' not in p.parts:inputs[str(p)]=pin(p)
for old,new in pairs:
 inputs[str(old)]=pin(old);inputs[str(new)]=pin(new)
rt=json.loads((P/'launch-runtime-freeze02.json').read_text())
for p,x in rt['inputs'].items():assert pin(p)==x;inputs[p]=x
for p in Path('/dev/shm/nssoc-div4-v7-power-v2-layout-01').iterdir():
 if p.is_file():inputs[str(p)]=pin(p)
for p in [R/'hw/soc/out/pcie-vco-v6-divider-power-v2-wire-v1-20261006/release-06-01.json',R/'hw/soc/out/pcie-vco-v6-divider-power-v2-wire-v1-20261006/saved-wave-diagnosis06.json']:
 inputs[str(p)]=pin(p)
products={str(new):pin(new) for old,new in pairs[:-1]}
oldtree=ast.parse(pairs[1][0].read_text());newtree=ast.parse(pairs[1][1].read_text());oldfunc={n.name:ast.dump(n,include_attributes=False) for n in oldtree.body if isinstance(n,ast.FunctionDef)};newfunc={n.name:ast.dump(n,include_attributes=False) for n in newtree.body if isinstance(n,ast.FunctionDef)};same=[n for n in oldfunc if oldfunc[n]==newfunc[n]];assert set(oldfunc)-set(same)=={'main'}
out=dict(status='FROZEN_COMPACT_V1_SOURCE_ONLY_REQUIRES_PEER_AND_FRESH_NATIVE',inputs=inputs,product_sources=products,launcher=pin(B/'launch01.py'),inherited_exact_checker_functions=same,python=rt['selected_python'],pdk=rt['selected_pdk'],layout='/dev/shm/nssoc-div4-v7-compact-v1-layout-01',checks='/dev/shm/nssoc-div4-v7-compact-v1-checks-01',control_status='60 actual source/lifecycle controls passed; first expected-row arithmetic failure retained',scope='Identical91 intrinsic devices/18finite taps/634via geometry multiset, new compact coordinates and shorter signal tracks. Existing power strap topology retained with new coordinates. No actual compact generation/DRC/LVS/RC/simulation yet.')
(B/'source-freeze01.json').write_text(json.dumps(out,indent=2)+'\n');print(len(inputs),pin(B/'source-freeze01.json'))
