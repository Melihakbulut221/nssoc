"""Seal the actual same4ns accepted-bank prefix context experiment and all prior failures."""
from pathlib import Path
import collections,hashlib,json,tarfile
R=Path.cwd();B=Path(__file__).resolve().parent
D={k:Path('/dev/shm')/f'nssoc-integrity-v24-balanced-{k}-01'for k in['map','import','sta']}
def pin(p):
 p=Path(p)
 with p.open('rb')as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
def dump(n,q):
 with(B/n).open('x')as f:json.dump(q,f,indent=2);f.write('\n')
status=json.loads((B/'continuation-status01.json').read_text());assert status['status']=='COMPLETE_NATIVE_SCREEN_FINITE_REVIEW_AND_PUBLICATION_REQUIRED'
assert len(status['stages'])==7 and all(x['returncode']==0 for x in status['stages'])
assert json.loads((B/'saved-controls-peer-vco03.json').read_text())['status']=='PASS_INDEPENDENT_SAVED_V24_COMPOSITE_FUNCTIONAL_CONTROLS'
files={};results={}
for k,expected in[('map','COMPLETE_NATIVE_MAP_FUNCTIONAL_REPLAY_REQUIRED'),('import','PASS_GRAPH_METADATA_AND_LITERAL_TIE_IMPORT'),('sta','COMPLETE_PREPLACEMENT_SCREEN_REVIEW_REQUIRED')]:
 d=D[k];q=json.loads((d/'result.json').read_text());assert q['status']==expected
 ins=q['inputs']if k!='sta'else q['cases'][0]['source_pins']
 for p,v in ins.items():assert pin(p)==v,p
 outs=q['outputs']if k!='sta'else q['cases'][0]['outputs'];base=d if k!='sta'else d/'rx'
 for n,v in outs.items():assert pin(base/n)==v,str(base/n)
 row=q if k!='sta'else q['cases'][0];assert row['returncode']==0 and row['native_allowed_cpus']==[6]and row['terminal_shared_free']>=528*1024**2
 results[k]=dict(path=str(d/'result.json'),**pin(d/'result.json'))
 for p in d.rglob('*'):
  if p.is_file()and not p.is_symlink():files[k+'/'+str(p.relative_to(d))]=p
proof=json.loads((B/'balanced-import-graph-proof.json').read_text());assert proof['status']=='PASS_COMPLETE_NATIVE_CELL_PIN_AND_PORT_DRIVER_GRAPH'
boundary=json.loads((B/'native-registered-boundary.json').read_text());assert boundary['status']=='PASS_EMITTED_REGISTERED_RETIRE_PAYLOAD_BOUNDARY_ONLY'and boundary['no_original_ring_content_q_in_output_d']and len(boundary['availability_consumer_flop_d'])==8
assert all(x['no_descriptor_payload_q']and x['no_original_ring_content_q']for x in boundary['availability_consumer_flop_d'])
timing=json.loads((B/'timing-comparison.json').read_text());assert not timing['acceptance'];old=json.loads((B.parent/'pcie-integrity-v23-20261006/timing-comparison.json').read_text());prior={(x['corner'],x['direction']):x['worst_slack_ns']for x in old['groups']if x['stage']=='PREPLACEMENT_REPAIRED'}
f=json.loads((B/'source-freeze03.json').read_text())
for n,v in f['sources'].items():assert pin(R/n)==v
for n in f['product_sources']:files['source/'+n]=R/n
m=json.loads((D['map']/'mapped.json').read_text())['modules']['soc_pcie_gen3_continuous_rx_integrity_v24'];cells=m['cells'];counts=collections.Counter(c['type']for c in cells.values());flops=sum(v for k,v in counts.items()if 'df'in k)
rows=[x for x in timing['groups']if x['stage']=='PREPLACEMENT_REPAIRED'];setup={x['corner']:x['worst_slack_ns']for x in rows if x['direction']=='max'};hold={x['corner']:x['worst_slack_ns']for x in rows if x['direction']=='min'}
assert set(setup)==set(hold)=={'slow','typical','fast'}
delta={x['corner']+'_'+x['direction']:x['worst_slack_ns']-prior[x['corner'],x['direction']]for x in rows}
oldcells=json.loads(Path('/dev/shm/nssoc-integrity-v23-balanced-map-01/result.json').read_text())['cells']
decision=dict(status='FINITE_NATIVE_SCREEN_COMPLETE_NOT_ADOPTED',native_cells=len(cells),flops=flops,cell_delta_vs_V23=len(cells)-oldcells,setup_ns=setup,hold_ns=hold,delta_vs_V23=delta,delta_vs_V17=timing['delta_vs_v17'],delta_vs_V11=timing['delta_vs_v11'],all_three_setup_nonnegative=all(x>=0 for x in setup.values()),all_three_hold_nonnegative=all(x>=0 for x in hold.values()),actual_descriptor_payload_flops=boundary['distinct_descriptor_payload_flops'],stable_baseline='V11',adopted=False,physical_acceptance=False,scope='Original4ns SS/TT/FF preplacement only. V24 accepted-bank token-only prefix context from V23; unchanged18case direct/cyclemiter and actual bank/promotion/cachefault witnesses plus3796416 relation comparisons/672 packing vectors. Actual computed slack signs and deltas retained without presuming pass. No mappedfunctional replay/CTS/routeRC/fullchip/PHYsignoff.')
dump('candidate-decision.json',decision)
for p in B.rglob('*'):
 if p.is_file()and not p.is_symlink()and '__pycache__'not in p.parts and p.name not in['seal-native01.log','active-checkpoint.json']and p.suffix not in['.xz','.gz']:
  files['method/'+str(p.relative_to(B))]=p
manifest={n:dict(original_path=str(p),**pin(p))for n,p in sorted(files.items())};dump('native-members.json',manifest);mp=B/'native-members.json'
a=B/'pcie-integrity-v24-native-preplacement-20261006.tar.xz';assert not a.exists()
with tarfile.open(a,'w:xz',preset=1)as t:
 for n,p in sorted(files.items()):t.add(p,arcname=n,recursive=False)
 t.add(mp,arcname='members.json',recursive=False)
with tarfile.open(a,'r:xz')as t:
 assert set(t.getnames())==set(manifest)|{'members.json'}
 for member in t:
  expected=pin(mp)if member.name=='members.json'else manifest[member.name];assert member.isfile()and member.size==expected['bytes']
  with t.extractfile(member)as s:assert hashlib.file_digest(s,'sha256').hexdigest()==expected['sha256']
for n,p in files.items():assert pin(p)=={k:manifest[n][k]for k in['bytes','sha256']}
q=dict(status='SEALED_ACTUAL_V24_PREFIX_CONTEXT_4NS_SCREEN_NOT_ADOPTED',source_freeze=pin(B/'source-freeze03.json'),source_peer=pin(B/'source-only-peer-vco03.json'),saved_controls_peer=pin(B/'saved-controls-peer-vco03.json'),native_policy=pin(B/'continuation-policy01.json'),native_peer=pin(B/'native-source-only-peer01.json'),native_results=results,timing_comparison=timing,native_import_pin_proof=proof,registered_boundary=pin(B/'native-registered-boundary.json'),critical_path=pin(B/'critical-path-attribution.json'),candidate_decision=decision,archive=dict(path=str(a),**pin(a),members=len(manifest)+1),full_readback=True,original_paths_rehashed=True,functional_publication=pin(B/'controls-composite-release01.json') if (B/'controls-composite-release01.json').exists() else None,physical_acceptance=False,scope='Allseven native stages completedonce withoutdispatch recovery. Original41PASS1hostFAIL retained;2targetedPASS repeat identical meaningful named mutation. All42 current predicates covered, MAX4118unrun. Same4ns preplacement metrics retained; no mappedport/formal/chiprouteRC/LVS/production acceptance. External runtime dependencies remain pinned rather than redistributed in this native capsule.')
p=B/'pcie-integrity-v24-native-validation-20261006.json';dump(p.name,q);print(json.dumps(dict(archive=q['archive'],validation=pin(p),decision=decision)))
