# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Independent saved-source and actual proof/port readback; no native launch."""
import ast, hashlib, importlib.util, json, sys
from pathlib import Path
import xml.etree.ElementTree as ET
S=Path(__file__).absolute().parent; B=S.parent
E=Path('/dev/shm/nssoc-rx-prefetch-v2-repair16one-equivalence')
P=Path('/dev/shm/nssoc-rx-prefetch-v2-repair16one-physical-replay-01')
def pin(p):
 p=Path(p)
 with p.open('rb') as f:return {'bytes':p.stat().st_size,'sha256':hashlib.file_digest(f,'sha256').hexdigest()}
f=json.loads((S/'route-rc-source-freeze16one.json').read_text())
for section in ('files','inputs'):
 for path,v in f[section].items(): assert pin(path)==v,path
for key,name in [('method','prepare_route16one.py'),('bridge','route-rc-source-bridge16one.json'),('gate_review','pre-drt-proof-port-review16one.json')]:assert pin(S/name)==f[key]
bridges=json.loads((S/'route-rc-source-bridge16one.json').read_text()); assert len(bridges)==2
for bridge in bridges:
 for kind in ('before','after'):
  d=bridge[kind]; assert pin(d['path'])=={k:d[k] for k in ('bytes','sha256')}
  assert ''.join(o[kind] for o in bridge['opcodes'])==Path(d['path']).read_text()
 old=Path(bridge['before']['path']).read_text(); new=Path(bridge['after']['path']).read_text()
 def tcl_nodes(text):
  return [ast.dump(n,include_attributes=False) for n in ast.walk(ast.parse(text)) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id in ('lines','libs') for t in n.targets)]
 assert tcl_nodes(old)==tcl_nodes(new)
 def functions(text):return {n.name:ast.dump(n,include_attributes=False) for n in ast.parse(text).body if isinstance(n,ast.FunctionDef)}
 assert functions(old)==functions(new)
 assert 'p=owned_popen(' in new and "if p is not None and not complete:ns['stop_failed_group'](p)" in new
 assert 'Terminal shared scratch floor' in new
sys.path.insert(0,str(B)); spec=importlib.util.spec_from_file_location('root_readback_rx16one',B/'proof_gate_repair16one.py'); gate=importlib.util.module_from_spec(spec); spec.loader.exec_module(gate); binding=gate.verify_binding()
proof=json.loads((E/'equivalence.json').read_text()); assert proof['states']==1804 and proof['matched']==proof['targets']==5443 and not proof['mismatches']
mutation=json.loads((E/'mutation-controls.json').read_text()); assert len(mutation['controls'])==10
for name in ('result.json','owned-driver.json'):
 r=json.loads((P/name).read_text()); assert r['inputs']=={p:pin(p) for p in r['inputs']}
port=json.loads((P/'result.json').read_text()); assert port['tests']=={'passed':6,'failed':0,'skipped':0}
cases=[]
for xml in P.rglob('*.xml'):
 for c in ET.parse(xml).getroot().iter('testcase'):
  assert not any(c.find(k) is not None for k in ('failure','error','skipped'));cases.append(c.attrib)
assert len(cases)==6
review={'status':'PASS_SOURCE_ONLY_RX16ONE_ROUTE_RC_AND_SAVED_NATIVE_PROOF_PORTS','findings':[], 'method':pin(__file__),'freeze':pin(S/'route-rc-source-freeze16one.json'),'source_pins':f['files'],'whole_source_inverse_bridges':2,'native_Tcl_ASTs_unchanged':True,'inherited_functions_unchanged':True,'proof_binding':pin(E/'proof-execution-binding.json'),'canonical_states':1804,'canonical_functions':5443,'actual_fault_controls':10,'native_ports':{'passed':6,'failed':0,'skipped':0,'simulation_ns':sum(float(c['sim_time_ns']) for c in cases)},'scope':'Readback only. Exact new candidate proof binding and six actual native tests verified. Same native routing/extraction Tcl, original timing/model and actual wire acceptance gates. Reviewed WNOWAIT helper owns descendants; fresh route and extraction outputs still required. No signoff or qualified RC.'}
(S/'route-rc-source-only-peer-root16one.json').write_text(json.dumps(review,indent=2)+'\n'); print(json.dumps(review,indent=2))
