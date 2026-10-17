"""Independent closed-arm input rehash/raw TSV recount; never launch EDA."""
from pathlib import Path
import ast,csv,difflib,hashlib,importlib.util,json,math,re,sys
B=Path(__file__).resolve().parent;R=B.parents[3]
def pin(p):
 p=Path(p)
 with p.open('rb')as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
def read(p):return json.loads(Path(p).read_text())
f=read(B/'source-freeze07.json');assert pin(B/'source-freeze07.json')['sha256']=='a10c01d965af0686e9afc73df3811f77ab588aff46a061b3e9e2c213b14a1e60'
assert f['prior_freeze']==pin(B/'source-freeze06.json')
for n,v in f['sources'].items():assert pin(n)==v,n
old=B/'pair02-original/methods/scripts/run_npu_eco_physical.py';new=R/'scripts/run_npu_eco_physical.py'
assert pin(old)==f['native_producer_source']
assert old.read_text().replace("pin(entry['path'])","pin(Path(entry['path']))")==new.read_text() and old.read_text().count("pin(entry['path'])")==1
prior_test=B/'pair02-original/methods/sw/tests/test_npu_eco_physical.py';current_test=R/'sw/tests/test_npu_eco_physical.py'
a=ast.parse(prior_test.read_text());z=ast.parse(current_test.read_text());assert ast.dump(ast.Module(body=z.body[:-1],type_ignores=[]),include_attributes=False)==ast.dump(a,include_attributes=False)
last=z.body[-1];assert isinstance(last,ast.FunctionDef)and last.name=='test_comparison_reopens_serialized_boot_path_before_replaying_readiness'
assert 'changed' in ast.unparse(last.decorator_list[0]) and '[False, True]' in ast.unparse(last.decorator_list[0])
assert pin(B/'controls07.log')==f['controls']['log']and '70 passed' in(B/'controls07.log').read_text()
method=B/'recover_pair02_comparison.py';result=B/'pair02-comparison-recovered01.json';assert pin(method)==f['recovery_method']and pin(result)==f['recovered_result']
s=method.read_text();ast.parse(s)
assert 'captured.pin = lambda path: original_pin(Path(path))'in s
assert "assert captured.ROOT == B / 'pair02-original/methods'"in s
assert 'subprocess'not in s and '.run('not in s
state=read(B/'pair02-status.json');assert state['status']=='FAILED_PRESERVED'and 'AttributeError' in state['error']
proc=Path('/proc')/str(state['controller']['pid'])/'stat'
if proc.exists():
 row=proc.read_text().split(') ',1)[1].split();assert row[19]!=state['controller']['start_ticks']or row[0]=='Z'
# Replay only the exact captured compare function through reviewed narrow adapter.
# This parses existing evidence; the module's native run()/main() is never called.
spec=importlib.util.spec_from_file_location('peer_saved_pair_recovery',method);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
replayed=module.check();saved=read(result);assert replayed==saved
independent={};output_pins=0
for variant in ['original','factored']:
 root=B/f'pair02-{variant}';j=read(root/'result.json');assert pin(root/'result.json')==state['completed'][variant]['result']
 assert j['status']=='FRESH_NPU_PHYSICAL_COMPLETE_ESTIMATE_ONLY'and j['all_inputs_rechecked']is True and j['execution']['returncode']==0
 for n,v in j['outputs'].items():assert pin(root/n)==v;output_pins+=1
 summaries={}
 for name,path in [('setup',root/'capture/setup-endpoints.tsv'),('hold',root/'capture/fresh_grt/endpoints.tsv')]:
  with path.open()as stream:rows=list(csv.DictReader(stream,delimiter='\t'))
  assert len(rows)=={'original':20138,'factored':20163}[variant] and len({x['endpoint']for x in rows})==len(rows)
  raw_native=read(root/'capture/fresh_grt/native.json');assert len(rows)==raw_native['endpoint_count']==raw_native['engine_endpoint_count']==raw_native['exported_endpoint_count']
  values=[float(x['global_vertex_slack_seconds'])for x in rows if x['global_vertex_slack_seconds']!='UNCONSTRAINED']
  assert values and all(math.isfinite(x)for x in values)
  count=sum(x<0 for x in values);worst=min(values);m=saved['comparison'][variant]
  assert worst==m[name+'_wns_seconds']and count==m[name+'_violating_endpoints']
  summaries[name]=dict(all_endpoints=len(rows),constrained=len(values),violations=count,wns_seconds=worst,compensated_vertex_tns_seconds=math.fsum(min(x,0)for x in values),raw=pin(path))
 native=read(root/'capture/fresh_grt/native.json');assert native['negative_vertex_endpoints']==summaries['hold']['violations']
 text=(root/'capture/electrical.rpt').read_text();parts=re.split(r'^max (slew|capacitance)\s*$',text,flags=re.M);assert parts[0].strip()=='' and len(parts)==5
 ec={parts[i]:parts[i+1].count('(VIOLATED)')for i in [1,3]};assert ec['slew']==m['slew_violations']and ec['capacitance']==m['capacitance_violations']
 summaries['electrical']=ec;independent[variant]=summaries
for k,v in saved['comparison']['factored_minus_original'].items():assert v==saved['comparison']['factored'][k]-saved['comparison']['original'][k]
assert saved['comparison']['factored_minus_original']['setup_wns_seconds']<0
assert not any(saved['comparison'][k]for k in ['candidate_adopted','timing_accepted','manufacturing_approval'])
sealer=B/'seal_pair02.py';ss=sealer.read_text();ast.parse(ss)
for line in ["recovered = recovery.check()","assert recovered == load(B / 'pair02-comparison-recovered01.json')","assert recovery_peer['result'] == pin(B / 'pair02-comparison-recovered01.json')","assert recovery_peer['method'] == pin(B / 'recover_pair02_comparison.py')","assert recovery_peer['freeze'] == pin(B / 'source-freeze07.json')","for name, expected in load(B / 'source-freeze07.json')['sources'].items():","assert set(seen) == set(pins)","assert pin(path) == seen[name]"]:
 assert line in ss,line
assert "state['status'] == 'FAILED_PRESERVED'"in ss and 'PASS_INDEPENDENT_SAVED_PAIR02_COMPARISON_RECOVERY'in ss
inputs={str(p):pin(p)for p in [B/'source-freeze07.json',method,result,sealer,old,new,prior_test,current_test,B/'controls07.log',B/'pair02-status.json']}
r=dict(status='PASS_INDEPENDENT_SAVED_PAIR02_COMPARISON_RECOVERY',findings=[],result=pin(result),method=pin(method),freeze=pin(B/'source-freeze07.json'),review_method=pin(__file__),sealer=pin(sealer),inputs=inputs,full_captured_compare_replayed_without_EDA=True,independent_raw_endpoint_and_electrical_recounts=independent,reviewer_correction='Initial reader assumed both physically optimized arms retain20138endpoints. Actual raw tables and native engine/export counters give20138original/20163factored. Original method/log retained; current reader independently counts and binds each full population, no producer edits or timing relaxation.',all_arm_output_pins_rehashed=output_pins,product_change='Exactly one Path normalization, all native production sources unchanged in captured arms.',source_controls='Actual70 tests saved; exactly two new changed/unchanged real JSON path hasher regressions, all previous test ASTs identical.',prior_native_failure_preserved=True,setup_worsened_ns=saved['comparison']['factored_minus_original']['setup_wns_seconds']*1e9,hold_improved_ns=saved['comparison']['factored_minus_original']['hold_wns_seconds']*1e9,native_or_sealer_executed=False,candidate_adopted=False,scope='Both original native arms genuinely completed before Python metadata comparison failure. Rehashed completed outputs and replayed exact captured raw audit/readiness/geometry with Path-only adapter; independently recounted20138original and20163factored setup/hold endpoint rows and all electrical violation lines. Recovered comparison is a worse setup estimate, not adoption or full-chip signoff. Updated sealer requires this exact peer/result/method/freeze and full native preservation; sealer not executed.')
out=B/'comparison-recovery-peer-pll01.json';assert not out.exists();out.write_text(json.dumps(r,indent=2)+'\n');print(pin(out))
