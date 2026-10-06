"""Seal actual registered-retire native result without promoting component signoff."""
from pathlib import Path
import json,hashlib,tarfile,collections
R=Path.cwd();B=Path(__file__).resolve().parent
D={k:Path('/dev/shm')/('nssoc-integrity-v21-balanced-'+k+'-01')for k in ['map','import','sta']}
def pin(p):
 p=Path(p)
 with p.open('rb')as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
def dump(name,obj):
 with (B/name).open('x')as f:json.dump(obj,f,indent=2);f.write('\n')
assert json.loads((B/'continuation-status03.json').read_text())['status']=='COMPLETE_NATIVE_SCREEN_FINITE_REVIEW_AND_PUBLICATION_REQUIRED'
assert json.loads((B/'controls-release01.json').read_text())['status']=='PASS_IMMUTABLE_RELEASE_ROUNDTRIPS'
files={};records={}
for k,status in [('map','COMPLETE_NATIVE_MAP_FUNCTIONAL_REPLAY_REQUIRED'),('import','PASS_GRAPH_METADATA_AND_LITERAL_TIE_IMPORT'),('sta','COMPLETE_PREPLACEMENT_SCREEN_REVIEW_REQUIRED')]:
 d=D[k];q=json.loads((d/'result.json').read_text());assert q['status']==status;records[k]=dict(path=str(d/'result.json'),**pin(d/'result.json'))
 ins=q['inputs']if k!='sta'else q['cases'][0]['source_pins']
 for p,v in ins.items():assert pin(p)==v
 outs=q['outputs']if k!='sta'else q['cases'][0]['outputs'];base=d if k!='sta'else d/'rx'
 for name,v in outs.items():assert pin(base/name)==v
 for p in d.rglob('*'):
  if p.is_file()and not p.is_symlink():files[k+'/'+str(p.relative_to(d))]=p
proof=json.loads((B/'balanced-import-graph-proof.json').read_text());assert proof['status']=='PASS_COMPLETE_NATIVE_CELL_PIN_AND_PORT_DRIVER_GRAPH'
boundary=json.loads((B/'native-registered-boundary.json').read_text());assert boundary['status']=='PASS_EMITTED_REGISTERED_RETIRE_PAYLOAD_BOUNDARY_ONLY'and boundary['no_original_ring_content_q_in_output_d']and len(boundary['availability_consumer_flop_d'])==8
assert all(x['no_descriptor_payload_q']and x['no_original_ring_content_q']for x in boundary['availability_consumer_flop_d'])
timing=json.loads((B/'timing-comparison.json').read_text());assert not timing['acceptance']
freeze=json.loads((B/'source-freeze04.json').read_text())
for n,v in freeze['sources'].items():assert pin(R/n)==v;files['source/'+n]=R/n
cells=json.loads((D['map']/'mapped.json').read_text())['modules']['soc_pcie_gen3_continuous_rx_integrity_v21']['cells'];counts=collections.Counter(c['type']for c in cells.values());flops=sum(v for k,v in counts.items()if 'df'in k)
repaired=[x for x in timing['groups']if x['stage']=='PREPLACEMENT_REPAIRED'];setup={x['corner']:x['worst_slack_ns']for x in repaired if x['direction']=='max'};hold={x['corner']:x['worst_slack_ns']for x in repaired if x['direction']=='min'}
assert set(setup)==set(hold)=={'slow','typical','fast'}
prior=json.loads((D['map'].parent/'nssoc-integrity-v17-balanced-map-01/result.json').read_text())['cells']
decision=dict(status='FINITE_NATIVE_SCREEN_COMPLETE_NOT_ADOPTED',native_cells=len(cells),flops=flops,cell_delta_vs_V17=len(cells)-prior,flop_delta_vs_V17=flops-9410,setup_ns=setup,hold_ns=hold,all_three_setup_nonnegative=all(v>=0 for v in setup.values()),all_three_hold_nonnegative=all(v>=0 for v in hold.values()),delta_vs_V17=timing['delta_vs_v17'],delta_vs_V11=timing['delta_vs_v11'],delta_vs_V19=timing['delta_vs_v19'],actual_descriptor_payload_flops=boundary['distinct_descriptor_payload_flops'],stable_baseline='V11',adopted=False,physical_acceptance=False,scope='Same original4ns SS/TT/FF preplacement only. Explicit+one internalcycle candidate, original16public cases composite and meaningful faultcontrols. No fullmappedport replay/formal/routeRC or physicalsignoff; residualsetupcannotbe waived.')
dump('candidate-decision.json',decision)
# Only closed outputs/methods; own log and mutable operational entry excluded.
for p in B.rglob('*'):
 if p.is_file()and not p.is_symlink()and '__pycache__'not in p.parts and p.name not in ['seal-native03.log','active-checkpoint.json']:
  files['method/'+str(p.relative_to(B))]=p
manifest={n:dict(original_path=str(p),**pin(p))for n,p in sorted(files.items())};mp=B/'native-members.json';dump(mp.name,manifest)
a=B/'pcie-integrity-v21-native-preplacement-20261006.tar.xz';assert not a.exists()
with tarfile.open(a,'w:xz',preset=3)as t:
 for n,p in sorted(files.items()):t.add(p,arcname=n,recursive=False)
 t.add(mp,arcname='members.json',recursive=False)
with tarfile.open(a,'r:xz')as t:
 assert set(t.getnames())==set(manifest)|{'members.json'}
 for m in t.getmembers():
  expected=pin(mp)if m.name=='members.json'else manifest[m.name];assert m.isfile()and m.size==expected['bytes']
  with t.extractfile(m)as f:assert hashlib.file_digest(f,'sha256').hexdigest()==expected['sha256']
for n,p in files.items():assert pin(p)=={k:manifest[n][k]for k in ['bytes','sha256']}
x=dict(status='SEALED_ACTUAL_REGISTERED_RETIRE_4NS_PREPLACEMENT_NOT_ADOPTED',source_freeze=pin(B/'source-freeze04.json'),source_peer=pin(B/'source-only-peer-rx04.json'),native_policy=pin(B/'continuation-policy03.json'),native_peer=pin(B/'native-source-only-peer03.json'),preserved_observer_failure=pin(B/'native-recovery-basis03.json'),native_results=records,timing_comparison=timing,native_import_pin_proof=proof,registered_boundary=pin(B/'native-registered-boundary.json'),critical_path=pin(B/'critical-path-attribution.json'),candidate_decision=decision,archive=dict(path=str(a),**pin(a),members=len(manifest)+1),full_readback=True,original_paths_rehashed=True,scope='V21 separate from V17 with explicit1cycle retirementdescriptor. Actual32pytestPASS/1historicalFAIL across33executions, initial unqualified negative retained butexcluded; unchanged15publicpositives pluscorrected16th and4strictproductmutants,4096literal+14XZ and9literalmutants,2ready1limitedmiters+1bypassmutant. MAX4118 profile unrun. Completed101103cellmap reused onceafter preservedmissing-internal-alias observerKeyError; actualQ/Dconsumercheck thennativeimport6graphmutants andoriginal4nsSS/TT/FF. No mappedfunctionalreplay/CTS/routeRC/wholechipLVS/fullPHY/production approval.',physical_acceptance=False)
p=B/'pcie-integrity-v21-native-validation-20261006.json';dump(p.name,x);print(json.dumps(dict(archive=x['archive'],validation=pin(p),decision=decision)))
