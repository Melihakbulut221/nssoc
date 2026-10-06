from pathlib import Path
import ast,difflib,hashlib,json
R=Path.cwd();B=Path(__file__).resolve().parent;P=B.with_name('pcie-divider-v9-bias-v1-20261006')
def pin(p):
 p=Path(p)
 with p.open('rb')as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
files=[f'hw/soc/flow/{x}_pcie_clock_div4_v9_bias_v1.py'for x in ['make','check','audit']]+[f'sw/tests/test_pcie_clock_div4_v9_bias_v1_{x}.py'for x in ['layout','native']]
pairs=[(R/p,R/p.replace('v9_bias_v1','v10_tail_v1'))for p in files]+[(R/'hw/soc/analog/pcie/clock_div4_hbt_v9.spice',R/'hw/soc/analog/pcie/clock_div4_hbt_v10.spice')]+[(P/n,B/n)for n in ['launch01.py','prepare_launch01.py']]
bridges=[]
for old,new in pairs:
 a,b=old.read_text().splitlines(keepends=True),new.read_text().splitlines(keepends=True)
 operations=[dict(tag=t,before=''.join(a[i:j]),after=''.join(b[k:l]))for t,i,j,k,l in difflib.SequenceMatcher(None,a,b,autojunk=False).get_opcodes()]
 assert ''.join(x['before']for x in operations)==old.read_text() and ''.join(x['after']for x in operations)==new.read_text()
 bridges.append(dict(before=dict(path=str(old),**pin(old)),after=dict(path=str(new),**pin(new)),opcodes=operations))
(B/'source-bridge01.json').write_text(json.dumps(bridges,indent=2)+'\n')
f=json.loads((P/'source-freeze01.json').read_text());inputs=dict(f['inputs']);assert inputs=={p:pin(p)for p in inputs}
for p in [P/'source-freeze01.json',P/'native-saved-peer-rx.json',P/'native-finite-review-ready01.json',Path('/dev/shm/nssoc-div4-v9-bias-v1-layout-01/result.json'),Path('/dev/shm/nssoc-div4-v9-bias-v1-layout-01/nssoc_clock_div4_v9_bias_v1_layout.gds')]:inputs[str(p)]=pin(p)
for p in B.rglob('*'):
 if p.is_file() and '__pycache__'not in p.parts and p.name!='source-freeze01.json':inputs[str(p)]=pin(p)
for old,new in pairs:inputs[str(old)]=pin(old);inputs[str(new)]=pin(new)
functions=lambda p:{n.name:ast.dump(n,include_attributes=False)for n in ast.parse(p.read_text()).body if isinstance(n,(ast.FunctionDef,ast.ClassDef))}
a=functions(pairs[1][0]);b=functions(pairs[1][1]);assert set(a)==set(b);assert [n for n in a if a[n]!=b[n]]==['main']
assert '64 passed' in(B/'source-controls01.log').read_text();assert 'All checks passed!'in(B/'ruff01.log').read_text()
assert 'PASS_SAVED_NATIVE_L127_REFERENCE_EXACT_INDEPENDENT_RECTANGLES'in(B/'saved-rppd01/read.log').read_text()
out=dict(status='FROZEN_TAIL115_ONE_NATIVE_REFERENCE_CHANGE_REQUIRES_PEER_AND_NATIVE',inputs=inputs,product_sources={str(new):pin(new)for old,new in pairs[:6]},launcher=pin(B/'launch01.py'),inherited_exact_checker_functions=[n for n in a if a[n]==b[n]],python=f['python'],pdk=f['pdk'],layout='/dev/shm/nssoc-div4-v10-tail-v1-layout-01',checks='/dev/shm/nssoc-div4-v10-tail-v1-checks-01',control_status='64 actual source/lifecycle controls PASS. Saved original GDS actual second-stage reference matches all9 independent Decimal PDK layer formulas. No new generation/DRC/LVS has run.',scope='Only DIV__XSECOND__XBIAS straight rppd W1um/L12.7um→11.5um. Both24um MIMs, twoL8 clock pull-downs and90 other intrinsic devices plus all91 connections retained. Separate exact cloned clock-div2 subcircuit preserves all first-stage devices. Independent native rppd shape formula and two reference faults added to prior eight; original21 native checks/resources/lifecycle unchanged. Fresh ten-geometry-control comparison, DRC/LVS/RC and loaded455 behavior required.',experiment='Margin hypothesis, not a confirmed cause or physical/electrical closure. Prior Bias8 full34ns functional failure is immutable; early divided interval is not acceptance.',ancestor_failure=str(R/'hw/soc/out/pcie-vco-v6-divider-bias8-v1-wire-v1-20261006/validation-06-01.json'))
assert not (B/'source-freeze01.json').exists();(B/'source-freeze01.json').write_text(json.dumps(out,indent=2)+'\n');print(len(inputs),pin(B/'source-freeze01.json'))
