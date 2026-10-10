# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Independent source/saved-byte review; does not import or execute producers."""
import ast,datetime,gzip,hashlib,json
from pathlib import Path
import xml.etree.ElementTree as ET
R=Path.cwd();S=Path(__file__).resolve().parent;B=S.parent
E=Path('/dev/shm/nssoc-rx-prefetch-v2-repair14a-equivalence')
P=Path('/dev/shm/nssoc-rx-prefetch-v2-repair14a-physical-replay-01')
G=Path('/dev/shm/nssoc-rx-prefetch-v2-postroute-repair-14a')

def pin(p):
 p=Path(p)
 with p.open('rb') as f:return {'bytes':p.stat().st_size,'sha256':hashlib.file_digest(f,'sha256').hexdigest()}
def load(p):return json.loads(Path(p).read_text())
def check(pins):
 for p,v in pins.items():assert pin(p)==v,p
 return len(pins)
freeze=load(S/'route-rc-source-freeze.json');check(freeze['files'])
assert freeze['bridge']==pin(S/'route-rc-source-bridge.json')
assert freeze['gate_review']==pin(S/'pre-drt-proof-port-review.json')
assert freeze['method']==pin(S/'prepare_route_sources.py')
bridges=load(S/'route-rc-source-bridge.json');bridges_checked=[]
assert len(bridges)==2
for bridge in bridges:
 before=Path(bridge['before']['path']);after=Path(bridge['after']['path'])
 assert pin(before)=={k:v for k,v in bridge['before'].items() if k!='path'}
 assert pin(after)=={k:v for k,v in bridge['after'].items() if k!='path'}
 assert ''.join(op['before'] for op in bridge['opcodes'])==before.read_text()
 assert ''.join(op['after'] for op in bridge['opcodes'])==after.read_text()
 for op in bridge['opcodes']:
  assert op['tag'] in ('equal','replace')
  if op['tag']=='equal':assert op['before']==op['after']
  else:
   left=op['before'].replace('repair-13','repair-14a').replace('repair13','repair14a').replace('rx13_','rx14a_').replace('RX13','RX14A')
   if "r={'status':'RUNNING'" in left:
    old_scope=ast.parse(left.split("\nr=",1)[1] if '\nr=' in left else left)
    # One metadata paragraph changes; all executable dictionary fields identical.
    actual=op['after'];prefix="'scope':'";start=left.index(prefix)+len(prefix);end=left.index("','elapsed_watchdog_seconds'",start)
    astart=actual.index(prefix)+len(prefix);aend=actual.index("','elapsed_watchdog_seconds'",astart)
    left=left[:start]+actual[astart:aend]+left[end:]
   assert left==op['after'],after
 bridges_checked.append({'before':str(before),'after':str(after),'all_bytes_reconstructed':True,'only_versions_paths_and_scope':True})
# Read both entire ASTs and verify inherited cleanup body exactly, not just names.
def function(path,name):
 tree=ast.parse(Path(path).read_text());return ast.dump(next(x for x in tree.body if isinstance(x,ast.FunctionDef) and x.name==name),include_attributes=False)
assert function(B/'postroute_repair13.py','stop_failed_group')==function(B/'postroute_repair14a.py','stop_failed_group')
for method in ('drt_repair14a.py','detailed_rc_repair14a.py'):
 text=(B/method).read_text();ast.parse(text)
 for required in ("resource.RLIMIT_CORE,(0,0)","int(2.5*1024**3)","start_new_session=True","if p is not None and not complete:ns['stop_failed_group'](p)","free<528*1024**2","'elapsed_watchdog_seconds':None","r['inputs']=={str(p):pin(p) for p in files}"):
  assert required in text,(method,required)
 assert 'timeout=' not in text
assert 'set_propagated_clock [all_clocks]' in (B/'drt_repair14a.py').read_text()
assert 'set_global_routing_layer_adjustment Metal2-Metal5 0.30' in (B/'drt_repair14a.py').read_text()
assert '-coupling_threshold 0 -cc_model 10 -context_depth 5 -no_merge_via_res' in (B/'detailed_rc_repair14a.py').read_text()
assert "assert (OUT/'routed.v').read_bytes()==(B/'repaired.v').read_bytes()" in (B/'drt_repair14a.py').read_text()
assert "assert (B/'router-drc.rpt').stat().st_size==0" in (B/'detailed_rc_repair14a.py').read_text()
# Independently rehash saved proof inputs/outputs and expand both complete gzip graphs.
bind=load(E/'proof-execution-binding.json');assert bind['status']=='PASS_ACTUAL_RX14A_PROOF_AND_MUTATION_EXECUTION_BOUND'
assert bind['before_inputs']==bind['after_inputs'];ninputs=check(bind['before_inputs'])
assert bind['runtime_before']==bind['runtime_after'];assert pin(bind['runtime_before']['path'])==bind['runtime_before']['pin']
assert bind['expanded_graphs_before']==bind['expanded_graphs_after']
for name,record in bind['expanded_graphs_before'].items():
 assert pin(E/(name+'.json.gz'))==record['compressed']
 with gzip.open(E/(name+'.json.gz'),'rb') as f:
  digest=hashlib.sha256();size=0
  while part:=f.read(1024**2):size+=len(part);digest.update(part)
 assert {'bytes':size,'sha256':digest.hexdigest()}==record['expanded']
for name,value in bind['outputs'].items():assert pin(E/name)==value
assert [(x['method'],x['returncode']) for x in bind['runs']]==[('compare.py',0),('mutations.py',0)]
eq=load(E/'equivalence.json');assert eq['states']==1804 and eq['matched']==eq['targets']==5443 and eq['mismatches']==[]
controls=load(E/'mutation-controls.json');assert len(controls['controls'])==10 and all(x['status'].startswith('REJECTED_') for x in controls['controls'])
port=load(P/'result.json');owner=load(P/'owned-driver.json');assert port['status']=='PASS_PORT_ONLY_GEN3_RECEIVE_FRAMING' and port['tests']=={'passed':6,'failed':0,'skipped':0}
assert owner['status']=='PASS_EXACT_PROVED_RX14A_SIX_NATIVE_PORT_CASES'
port_inputs=check(port['inputs']);owner_inputs=check(owner['inputs'])
for name,value in port['outputs'].items():assert pin(P/name)==value
xml=ET.parse(P/'results.xml');cases=list(xml.getroot().iter('testcase'));assert len(cases)==6 and all(not list(c) for c in cases)
assert len({c.attrib['name'] for c in cases})==6
expected={'bytes':2094864,'sha256':'cc489bb50c225189126b36d173cf786a7837f1e9a0cebc8a200c2d7b7a191f91'}
assert pin(G/'repaired.v')==expected==bind['before_inputs'][str(G/'repaired.v')]==port['inputs'][str(G/'repaired.v')]
grt=load(G/'result.json');check(grt['inputs'])
for name,value in grt['outputs'].items():assert pin(G/name)==value
for path in ('/dev/shm/nssoc-rx-prefetch-v2-repair14a-drt-01','/dev/shm/nssoc-rx-prefetch-v2-repair14a-detailed-rc-01'):assert not Path(path).exists()
record={'status':'PASS_SOURCE_ONLY_RX14A_ROUTE_RC','freeze':pin(S/'route-rc-source-freeze.json'),'findings':[],'utc':datetime.datetime.now(datetime.UTC).isoformat(),'method':pin(Path(__file__)),'whole_source_bridges':bridges_checked,'saved_proof':{'inputs':ninputs,'states':1804,'targets':5443,'actual_rejected_controls':10,'both_complete_gzip_graphs_readback':True,'binding':pin(E/'proof-execution-binding.json')},'saved_ports':{'input_pins':port_inputs,'owner_input_pins':owner_inputs,'six_raw_xml_cases':[c.attrib['name'] for c in cases],'result':pin(P/'result.json'),'owner':pin(P/'owned-driver.json')},'candidate':expected,'runtime_policy':freeze['limits'],'unchanged_inherited_failure_only_cleanup':True,'native_or_reviewed_method_executed':False,'scope':'Fresh14a path/version/metadata changes only; mandatory exact proof/port/netlist binding and zero-routerDRC/complete-route gate reviewed. Same nominal RC across three cell corners, no qualifiedRC/fullchip/timing acceptance. Fresh launch resource and affinity preflight still required.'}
(S/'route-rc-source-only-peer-vco.json').write_text(json.dumps(record,indent=2)+'\n');print(record['status'],pin(S/'route-rc-source-only-peer-vco.json'))
