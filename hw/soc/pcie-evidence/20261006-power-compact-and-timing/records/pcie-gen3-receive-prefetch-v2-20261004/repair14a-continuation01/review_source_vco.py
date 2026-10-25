from pathlib import Path
import ast, datetime, hashlib, json, os
R=Path.cwd(); B=R/'hw/soc/out/pcie-gen3-receive-prefetch-v2-20261004'; C=B/'repair14a-continuation01'; P=B/'repair14a-preroute-preservation'; Q=B/'repair14a-peer'
def pin(p):
 p=Path(p)
 with p.open('rb') as f:return {'bytes':p.stat().st_size,'sha256':hashlib.file_digest(f,'sha256').hexdigest()}
def checkpins(rows):
 for p,x in rows.items():assert pin(p)=={k:x[k] for k in ('bytes','sha256')},p
 return len(rows)
bridges=[]
for d in (Q,C,P):
 j=json.loads((d/'source-bridge.json').read_text()); rows=j if isinstance(j,list) else [j]
 for r in rows:
  for side in ('before','after'):
   p=Path(r[side]['path']);assert pin(p)=={k:r[side][k] for k in ('bytes','sha256')}
   assert ''.join(x[side] for x in r['opcodes']).encode()==p.read_bytes()
  bridges.append({'before':r['before'],'after':r['after'],'non_equal_blocks':sum(x['tag']!='equal' for x in r['opcodes'])})
m=json.loads((C/'manifest.json').read_text());n=checkpins(m['inputs']);q=checkpins(m['route_inputs']);assert(n,q)==(36,26)
for p in (Q/'source-freeze.json',P/'source-freeze.json'):
 j=json.loads(p.read_text());checkpins(j.get('files',j.get('inputs',{})))
reuse=json.loads((C/'lifecycle-controls-reuse.json').read_text());checkpins(reuse['inputs'])
def ast_parts(p):
 t=ast.parse(Path(p).read_text());f=next(x for x in ast.walk(t) if isinstance(x,ast.FunctionDef) and x.name=='run_stage'); main=next(x for x in t.body if isinstance(x,ast.FunctionDef) and x.name=='main'); tail=[x for x in main.body if isinstance(x,ast.Try)][-1];return ast.dump(f),ast.dump(tail)
assert ast_parts(C/'run.py')==ast_parts(B/'repair13-continuation01/run.py')
lifecycle=json.loads((B/'repair13-continuation01/lifecycle-controls.json').read_text());assert lifecycle
observed={}
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==m['boot_id']
for name in ('route_owner','route_native'):
 v=m[name];p=Path('/proc')/str(v['pid']);s=(p/'stat').read_text().rsplit(')',1)[1].split();assert int(s[19])==int(v['start_ticks']);assert s[0]!='Z';assert os.sched_getaffinity(v['pid'])=={8};observed[name]={'pid':v['pid'],'start_ticks':int(s[19]),'state':s[0],'affinity':[8]}
base={'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'reviewer':'independent VCO agent','method':pin(C/'review_source_vco.py'),'findings':[],'scope':'Source-only whole-byte review and saved lifecycle evidence; no reviewed method, router, extraction, kernel, port test, sealer or publisher executed.'}
chain={**base,'status':'PASS_SOURCE_ONLY_RX14A_DEPENDENT_CHAIN','manifest':pin(C/'manifest.json'),'input_pins_checked':n,'route_input_pins_checked':q,'four_method_whole_byte_bridges':bridges,'lifecycle_reused':{'exact_run_stage_and_post_context_AST':True,'saved_actual_controls':3,'no_controls_rerun':True},'observed_route':observed,'reviewed_gates':['same boot and exact existing owner/native births; observer does not own or signal the route','actual completed zero-DRC exact route, unchanged 26 inputs and complete outputs and proved netlist before fresh RC14a','saved-output review requires exact proof/compiled gzip/ports/SPEF/timing, preserves nominal timing PASS or FAIL and compares prior RX13','mandatory five complete native roots, all-member readback and immutable three-asset V3 publication','CPU8, 2.5GiB AS, 1GiB entry and 528MiB continuous/terminal floors, no healthy elapsed watchdog; 15s outer failure grace exceeds 5s inner RC','completion/teardown cancellation propagation and nonzero child failure bodies match the three saved actual RX13 controls'], 'limitations':['Stand-alone default150 receiver, unqualified nominal RC; no fullchip or full PHY acceptance.','Fresh final route/RC and actual controller execution are still required.']}
(C/'source-only-peer-vco.json').write_text(json.dumps(chain,indent=2)+'\n')
pre={**base,'status':'PASS_SOURCE_ONLY_RX14A_PREROUTE_PRESERVATION','freeze':pin(P/'source-freeze.json'),'whole_byte_bridge':bridges[-1],'reviewed_gates':['four closed GRT alternatives individually require complete zero-exit results and all current input/output hashes','selected14a canonical proof 1804 states/5443 targets, ten actual faults and six saved native port cases','six completed native roots only; active DRT roots and active drt14a/detailed-rc logs excluded','full member and source-after-seal hashes; unique14a asset names, prior RX13 verified public metadata','unchanged 70MiB per-member archive limit and 528MiB shared scratch floor; no EDA rerun'], 'limitations':['Finite pre-route preservation only; no final routing/timing/qualified RC/PHY acceptance.']}
(P/'source-only-peer-vco.json').write_text(json.dumps(pre,indent=2)+'\n')
for p in (C/'source-only-peer-vco.json',P/'source-only-peer-vco.json'):print(p,pin(p))
