"""Independent complete source inverse and control-binding review; no native run."""
from pathlib import Path
import ast,hashlib,json,re
R=Path.cwd();B=Path(__file__).resolve().parent;P=B.parent/'pcie-integrity-v23-20261006'
def pin(p):
 p=Path(p)
 with p.open('rb')as s:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(s,'sha256').hexdigest())
def read(p):return json.loads(Path(p).read_text())
def patch(old,diff):
 if not diff:return old
 lines=old.splitlines(True);d=diff.splitlines(True);out=[];at=0;i=2
 while i<len(d):
  m=re.match(r'@@ -(\d+)(?:,\d+)? \+\d+(?:,\d+)? @@',d[i]);assert m;start=int(m[1])-1;assert start>=at;out+=lines[at:start];at=start;i+=1
  while i<len(d)and not d[i].startswith('@@ '):
   tag,body=d[i][0],d[i][1:];assert tag in ' +-'
   if tag in ' -':assert lines[at]==body;at+=1
   if tag in ' +':out.append(body)
   i+=1
 out+=lines[at:];return ''.join(out)
p=B/'continuation-policy01.json';policy=read(p);bridge=read(B/'native-source-bridges01.json')
assert bridge['policy']==pin(p) and bridge['launcher']==pin(B/'detach_native01.py')
for key in ('method_pins','source_pins'):
 for name,value in policy[key].items():assert pin(R/name)==value,name
assert len(policy['method_pins'])==9 and len(policy['source_pins'])==193
assert len(bridge['rows'])==10
for row in bridge['rows']:
 for key in ('parent','candidate'):assert pin(row[key]['path'])=={k:row[key][k]for k in ('bytes','sha256')}
 assert patch(Path(row['parent']['path']).read_text(),row['whole_diff'])==Path(row['candidate']['path']).read_text()
for name in ('native_lifecycle02.py','measure_registered_boundary.py','balanced_import02.py','prove_balanced_import.py','balanced_preplacement02.py','analyze_critical_path.py'):
 assert (B/name).read_text().replace('v24','v23').replace('V24','V23')==(P/name).read_text(),name
for name in ('run_balanced_map03.py','continue_native03.py'):
 new=ast.parse((B/name).read_text().replace('v24','v23').replace('V24','V23'));old=ast.parse((P/name).read_text())
 for node in old.body:
  if isinstance(node,ast.FunctionDef)and not(name=='continue_native03.py'and node.name=='save'):
   other=next(n for n in new.body if isinstance(n,ast.FunctionDef)and n.name==node.name);assert ast.dump(node,include_attributes=False)==ast.dump(other,include_attributes=False),(name,node.name)
# Full native map execution tail, including wait/terminal floor/exact owned cleanup, is identical.
a=(P/'run_balanced_map03.py').read_text();b=(B/'run_balanced_map03.py').read_text().replace('v24','v23').replace('V24','V23');assert a[a.index('def save():'):]==b[b.index('def save():'):]
# Exact added timing comparison only; all existing parser arithmetic retained.
a=(P/'review_timing.py').read_text();b=(B/'review_timing.py').read_text().replace('integrity-v24-balanced','integrity-v23-balanced')
i=b.index('previous23_path=');e=b.index('markers = list(',i);addition=b[i:e];assert '88bb268620e50544e608cce9ec6b72848a4c80833045f1390d5165711df89ab9' in addition
assert (b[:i]+b[e:]).replace('delta_vs_v23=delta23, ','')==a
assert pin(P/'timing-comparison.json')['sha256']=='88bb268620e50544e608cce9ec6b72848a4c80833045f1390d5165711df89ab9'
for row in policy['controls'].values():assert pin(row['path'])=={k:row[k]for k in ('bytes','sha256')}
v=read(policy['controls']['validation']['path']);sp=read(policy['controls']['independent_peer']['path']);assert v['status']=='PASS_V24_PREFIX_CONTEXT_COMPOSITE_CONTROLS' and sp['status']=='PASS_INDEPENDENT_SAVED_V24_COMPOSITE_FUNCTIONAL_CONTROLS' and not sp['findings']
assert sp['validation']==pin(policy['controls']['validation']['path'])
assert v['pytest_executions']==44 and v['passed_executions']==43 and v['historical_failed_executions']==1 and v['current_42_predicates_covered']
assert v['source_freeze']==pin(B/'source-freeze03.json') and v['source_peer']==pin(B/'source-only-peer-vco03.json')
assert policy['source_pins']==read(B/'source-freeze03.json')['sources']
controller=ast.parse((B/'continue_native03.py').read_text());stages=[]
for n in ast.walk(controller):
 if isinstance(n,ast.Call)and isinstance(n.func,ast.Name)and n.func.id=='stage':
  name=ast.literal_eval(n.args[0]);cmd=n.args[1];path=ast.literal_eval(cmd.elts[1].args[0].right);stages.append((name,path));assert path in policy['actual_stage_paths'] and pin(B/path)==policy['actual_stage_paths'][path]
assert stages==[('map','run_balanced_map03.py'),('registered_boundary','measure_registered_boundary.py'),('import','balanced_import02.py'),('import_graph_proof','prove_balanced_import.py'),('preplacement','balanced_preplacement02.py'),('timing_review','review_timing.py'),('critical_path','analyze_critical_path.py')]
assert policy['CPU']==6 and policy['AS_bytes']==2*1024**3 and policy['clock_period_ns']==4.0
for path in policy['fresh_outputs']:assert not Path(path).exists()
for name in ('continuation-status01.json','signed-wire-census.json','detached-native01-once.json'):[None for _ in [0] if not(B/name).exists()] or (_ for _ in ()).throw(AssertionError(name))
for name,_ in stages:assert not(B/(name+'.controller.log')).exists()
ancestry=policy['native_lifecycle_ancestry'];assert pin(ancestry['peer'])==ancestry['pin']
# Bind observed static native runtime/reference bytes for the dispatcher's fresh preflight.
observed=[R/'hw/soc/tools/oss-cad-suite/bin/yosys',R/'hw/soc/tools/oss-cad-suite/bin/yosys-abc',Path('/dev/shm/nssoc-integrity-v2-balanced-map-01/map.ys'),Path('/dev/shm/nssoc-integrity-v2-balanced-map-01/abc-structural.script'),P/'timing-comparison.json']
for source in ('balanced_preplacement02.py','review_timing.py'):
 text=(B/source).read_text()
 for raw in re.findall(r"Path\('([^']+)'\)",text):
  q=Path(raw)
  if q.is_file():observed.append(q)
observed_pins={str(q):pin(q)for q in observed}
out=dict(status='PASS_SOURCE_ONLY_V24_NATIVE_CONTINUATION',policy=pin(p),launcher=pin(B/'detach_native01.py'),findings=[],method=pin(__file__),source_count=193,method_count=9,whole_bridges=10,actual_stage_paths=policy['actual_stage_paths'],saved_controls_peer=pin(policy['controls']['independent_peer']['path']),observed_static_native_input_pins=observed_pins,checks=['All193 policy source pins/nine method pins and ten complete parent-to-candidate byte bridges rehashed and reconstructed. Six complete helpers differ only by V23/V24 version or are identical; complete native map tail and all runtime/cleanup functions unchanged.','Read full map/control gates, controller and detached launcher. Exactly actual44executions43PASS/1historicalhostFAIL and independent42-predicate saved peer are prerequisites. RTL/stimulus freeze03, every helper receipt, seven exact current helper basenames and fresh outputs/logs bound.','Map remains same balanced ABC150-byte profile. Registered-boundary actual Q/D analysis, signed wire metadata exact inverse, two literal ties and exhaustive original-cell/pin/port-driver graph with actual graph controls inherited. Same original4ns/corners/port delays/loads and native reporting; added pinned V23 comparison only.','Exact owned birth/boot/group cleanup and original real lifecycle-control ancestry retained. CPU6/2GiB native stages, entry and continuous/terminal shared floors, explicit signal propagation and sanitized detached launch unchanged; no healthy elapsed timeout.','No producer import/native/control execution. Native runtime and old mapping-template bytes are additionally observed here; dispatch must recheck this observed_static_native_input_pins map immediately before launch alongside policy. Native methods independently record/recheck their actual inputs and outputs. Full native result and timing acceptance remain unproved.'])
(B/'native-source-only-peer01.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({'status':out['status'],'receipt':pin(B/'native-source-only-peer01.json')}))
