#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Independent source and saved-record checks; never import or execute producers."""
import ast
from collections import Counter
import datetime
import gzip
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

R = Path.cwd()
B = Path(__file__).resolve().parent
P = R/'hw/soc/out/pcie-vco-v6-divider-compact-v2-wire-v1-20261006'
def pin(p):
    p=Path(p)
    with p.open('rb') as stream:
        return {'bytes':p.stat().st_size,'sha256':hashlib.file_digest(stream,'sha256').hexdigest()}
def read(p): return json.loads(Path(p).read_text())
def nodes(s): return {n.name:ast.dump(n,include_attributes=False) for n in ast.parse(s).body if isinstance(n,(ast.FunctionDef,ast.ClassDef))}
def literal(s,name):
    for n in ast.parse(s).body:
        if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id==name for t in n.targets):return ast.literal_eval(n.value)
    raise AssertionError(name)
f=read(B/'source-freeze01.json')
assert pin(B/'source-freeze01.json')=={'bytes':48612,'sha256':'cd63353c149f89e207e6e1d3d54af287ea827c7519b4b979a5ceb8cfdb2428a6'}
for p,v in f['pins'].items(): assert pin(p)==v,p
for p,v in f['new_sources'].items(): assert pin(R/p)==v,p
bridges=[]
for filename in ('builder-source-bridge.json','characterizer-source-bridge.json'):
    j=read(B/filename)
    for row in j if isinstance(j,list) else [j]:
        before=''.join(x['before'] for x in row['opcodes'])
        after=''.join(x['after'] for x in row['opcodes'])
        for op in row['opcodes']:
            if op['tag']=='equal': assert op['before']==op['after']
        assert before==Path(row['before']['path']).read_text()
        assert after==Path(row['after']['path']).read_text()
        assert pin(row['before']['path'])=={k:row['before'][k] for k in ('bytes','sha256')}
        assert pin(row['after']['path'])=={k:row['after'][k] for k in ('bytes','sha256')}
        bridges.append({'method':row['after']['path'],'bridge':pin(B/filename),'before':row['before'],'after':row['after']})
for filename,target in [('launcher-source-bridge.json','launch_probe01.py'),('sealer-source-bridge.json','seal_probe01.py')]:
    row=read(B/filename)
    assert Path(row['parent']).read_text()==row['full_before']
    assert (B/target).read_text()==row['full_after']
    # Independent complete inverse, not merely the author's opcode ledger.
    reverted=row['full_after'].replace('cap24_v1','compact_v2').replace('cap24-v1','compact-v2').replace('div4-v8-cap-v1','div4-v7-compact-v2')
    assert reverted==row['full_before']
    bridges.append({'method':str(B/target),'bridge':pin(B/filename),'parent':pin(row['parent']),'after':pin(B/target)})
old=(R/'scripts/characterize_pcie_vco_v6_divider_compact_v2_wire_v1.py').read_text()
new=(R/'scripts/characterize_pcie_vco_v6_divider_cap24_v1_wire_v1.py').read_text()
a,b=nodes(old),nodes(new)
assert set(b)==set(a)|{'reference_rows'}
unchanged=[]
for name in a:
    if name in ('topology','config'):continue
    assert a[name]==nodes(new.replace('cap24-v1','compact-v2'))[name],name
    unchanged.append(name)
# Verify the complete characterizer inverse outside the new reference function.
reverted=new.replace('v8_cap24_v1','v7_compact_v2').replace('cap24_v1','compact_v2').replace('cap24-v1','compact-v2')
for name in ('BUILDER_SHA','DIVIDER_PINS'):
    ns=next(n for n in ast.parse(reverted).body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id==name for t in n.targets))
    os=next(n for n in ast.parse(old).body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id==name for t in n.targets))
    reverted=reverted.replace(ast.get_source_segment(reverted,ns),ast.get_source_segment(old,os),1)
for line in new.splitlines(keepends=True):
    if line.startswith(('REFERENCE =','REFERENCE_SHA =','PREVIOUS_REFERENCE_SHA =')):reverted=reverted.replace(line,'',1)
start=reverted.index('def reference_rows(');end=reverted.index('def config(',start)
reverted=reverted[:start]+reverted[end:]
reverted=reverted.replace('    _, nominal, nominal_texts = previous.config(vctrl, "")\n    nominal, reference = reference_rows(nominal, nominal_texts)\n','    _, nominal, _ = previous.config(vctrl, "")\n',1)
reverted=reverted.replace('    texts[REFERENCE.name] = reference\n','',1).replace('[str(REFERENCE),str(CHAIN),','[str(CHAIN),',1)
reverted=reverted.replace("loaded_physical_vco_v6_and_divider_v8_cap24_wire_div80","loaded_physical_vco_v6_and_divider_v7_wire_div80",1)
assert reverted==old
# Independent source-reference delta (comments alone excluded as documented).
v7=(R/'hw/soc/analog/pcie/clock_div4_hbt_v7.spice').read_text()
v8=(R/'hw/soc/analog/pcie/clock_div4_hbt_v8.spice').read_text()
expected=v7.replace('nssoc_clock_div4_hbt_v7','nssoc_clock_div4_hbt_v8')
for name,a,c in [('XCP','lp','ckp'),('XCN','ln','ckn')]:
    src=f'{name} {a} {c} cap_cmim w=20u l=20u'
    assert expected.count(src)==1
    expected=expected.replace(src,src.replace('20u','24u'))
def circuit(s):return [x.strip() for x in s.splitlines() if x.strip() and not x.lstrip().startswith('*')]
assert circuit(v8)==circuit(expected)
# Independently join actual source/native IDs to emitted primitive parameters.
fixtures=R/'sw/tests/fixtures'
oldfx=fixtures/'pcie_clock_div4_v7_compact_v2_hybrid_v1'
newfx=fixtures/'pcie_clock_div4_v8_cap24_v1_hybrid_v1'
def devices(folder):
    comp=read(folder/'composition.json');binding=read(folder/'source-native-bijection.json')
    by={x['native_id']:x for x in comp['records']}
    assert len(by)==len(binding['devices'])==91
    result={}
    for x in binding['devices']:
        r=by[x['native_id']]
        assert r['model']==x['model']
        result[x['source_name']]={'model':r['model'],'nets':x['source_nets'],'params':r['simulator_parameters'],'native':r['native_parameters']}
    assert len(result)==91 and sum(t['node']=='BODY_SUBSTRATE' for x in comp['records'] for t in x['terminals'])==85
    return result,comp
od,_=devices(oldfx);nd,comp=devices(newfx)
assert set(nd)==set(od)
changed=[k for k in nd if nd[k]!=od[k]]
assert set(changed)=={'DIV__XCP','DIV__XCN'}
for name in changed:
    target=json.loads(json.dumps(od[name]));target['params']={'w':'24.0u','l':'24.0u'};target['native'].update(w=24.0,l=24.0,A=576.0,P=96.0)
    assert nd[name]==target
bp=literal((R/'scripts/build_pcie_clock_div4_v8_cap24_v1_hybrid_v1.py').read_text(),'PINS')
for key,name in [('anchors','anchors.json'),('devices','device-location-geometry.json'),('geometry','wire-component-geometry.json'),('native','extracted.cir'),('wires','wires.spice')]:
    raw=gzip.decompress((newfx/'inputs'/(name+'.gz')).read_bytes())
    assert hashlib.sha256(raw).hexdigest()==bp[key]
assert (newfx/'hybrid-open.spice').read_bytes()==(B/'composed01/hybrid-open.spice').read_bytes()
assert (newfx/'composition.json').read_bytes()==(B/'composed01/composition.json').read_bytes()
# Inspect four saved recipes, without executing config/producer again.
recipes=[]
for path in sorted(B.glob('recipe-*.json')):
    j=read(path);rows=j['devices'];c=j['config']
    assert len(rows)==len({x['path'] for x in rows})==455
    assert sum(x['model']=='npn13g2' for x in rows)==64
    assert sum(x['model'] in ('ptap1','ntap1') for x in rows)==31
    assert j['vector_count']==956
    assert (c['wire_resistors'],c['wire_capacitors'])==(1271,1414)
    assert (c['step_s'],c['stop_s'],c['window_s'])==(5e-12,34e-9,[4e-9,34e-9])
    assert c['fixture'][-2:]==['VDIVBODY div_body_substrate 0 0','VDIVWREF div_wire_cref 0 0']
    assert sum(x.startswith('xchain.xdiv.') for x in (r['path'] for r in rows))==91
    assert sum(n=='div_body_substrate' for r in rows for n in r['nets'])==85
    native={r['path']:r for r in rows if r['path'].startswith('xchain.xdiv.')}
    for r in comp['records']:
        w=r['line'].lower().split(); actual=native['xchain.xdiv.'+w[0]]
        assert actual['model']==r['model'].lower()
        assert actual['params']=={k.lower():v.lower() for k,v in r['simulator_parameters'].items()}
    recipes.append({'path':str(path),'pin':pin(path),'devices':455,'vectors':956,'HBT':64,'finite_contacts':31})
assert len(recipes)==4
xml=[]
for name,count in [('source-controls01.xml',28),('handoff-controls01.xml',4)]:
    tree=ET.parse(B/name);cases=tree.findall('.//testcase')
    assert len(cases)==count and all(not any(x.tag in ('failure','error','skipped') for x in c) for c in cases)
    xml.append({'path':str(B/name),'pin':pin(B/name),'actual_passed':len(cases)})
raw_controls=[]
for name in f['pins']:
    p=Path(name)
    if 'pytest' not in p.parts[-3] and not any(x.startswith('pytest') for x in p.parts):continue
    raw_controls.append({'path':name,'pin':pin(p)})
    if p.name in ('owned-processes.json','actual-inner-owner.json'):
        r=read(p)
        assert r['elapsed_watchdog_seconds'] is None
        for e in r['processes']:
            assert e['status'] in ('REAPED_NO_LIVE_MEMBERS','FAILURE_REAPED')
            birth=e['identity'];proc=Path('/proc')/str(birth['pid'])/'stat'
            if proc.exists():assert proc.read_text().rsplit(') ',1)[1].split()[19]!=str(birth['start_ticks'])
    if p.name=='handoff-result.json':
        r=read(p);assert r['status'].startswith('PASS_REAL_SIGNAL_') and r['handlers_restored']
assert not Path('/dev/shm/nssoc-vco-v6-divider-cap24-v1-wire-06-01').exists()
receipt={'status':'PASS_SOURCE_ONLY_LOADED455_WIRE_MODEL','findings':[],'freeze':pin(B/'source-freeze01.json'),'source_pins':f['new_sources'],'launcher':pin(B/'launch_probe01.py'),'verified_input_pins':len(f['pins']),'complete_source_bridges':bridges,'independent_characterizer_full_inverse':True,'unchanged_function_ASTs':unchanged,'two_only_native_primitive_changes':changed,'unchanged_other_primitives':89,'complete_read_scope':['builder','characterizer and private inherited-global rebinding','SPICE top','full tests and launcher handoff tests','detached launcher','closed-result sealer'],'saved_recipes':recipes,'saved_XML':xml,'saved_raw_control_files':len(raw_controls),'saved_control_births_closed':True,'scope':['No reviewed producer, native simulation or test reexecution.','Only source/saved-control review; new loaded capture is still required.','Unchanged 34ns/5ps/27C/50fF/300mV and all electrical/functional predicates; 455 devices, 956 vectors, 64 native OFF readbacks, 31 finite contacts.','Full 1271R/1414C retained; 85 divider body terminals and independent body/wire reference boundaries remain explicit ideal bench assumptions.','Not qualified full PEX, RF/PVT, PLL lock, full PHY or main-chip closure.','Teardown signal control inner receipt retains its last HEALTHY write, but outer expected exception and exact dead child birth are preserved.','Draft preparation before V8 reference correction is preserved; it was not an executed native candidate.'],'method':pin(__file__),'utc':datetime.datetime.now(datetime.UTC).isoformat()}
with (B/'source-only-peer01-rx.json').open('x') as stream:json.dump(receipt,stream,indent=2);stream.write('\n')
sealer={'status':'PASS_SOURCE_ONLY_CAP24_LOADED455_CLOSED_SEALER','findings':[],'sealer':pin(B/'seal_probe01.py'),'bridge':pin(B/'sealer-source-bridge.json'),'full_inverse_paths_only':True,'source_peer':pin(B/'source-only-peer01-rx.json'),'scope':'Requires closed controller/native receipts, complete source/output hashes, full raw decompression/hash/finite-grid/all455 replay, all64 OFF startup readback and full archive member readback. Failed functional verdict is preserved. Run stdout outside the frozen/captured directory; no active native files or sealer outputs have been produced by this review.','method':pin(__file__)}
with (B/'sealer-source-only-peer-rx.json').open('x') as stream:json.dump(sealer,stream,indent=2);stream.write('\n')
print(json.dumps({'source_peer':pin(B/'source-only-peer01-rx.json'),'sealer_peer':pin(B/'sealer-source-only-peer-rx.json'),'input_pins':len(f['pins']),'saved_controls':32,'recipes':4}))
