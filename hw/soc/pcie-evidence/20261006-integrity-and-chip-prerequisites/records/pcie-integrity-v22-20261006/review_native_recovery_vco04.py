from pathlib import Path
import ast,hashlib,json
B=Path(__file__).resolve().parent;R=B.parents[3]
def pin(p):
 p=Path(p)
 with p.open('rb')as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
p=B/'continuation-policy04.json';policy=json.loads(p.read_text())
for name,w in policy['method_pins'].items():assert pin(name)==w
for name,w in policy['source_pins'].items():assert pin(R/name)==w
bridge=json.loads((B/'native-source-recovery-bridge03.json').read_text());parent=Path(bridge['parent']['path']);assert pin(parent)=={k:bridge['parent'][k]for k in ['bytes','sha256']}
s=parent.read_text();assert s.count(bridge['removed_completed_stages'])==1;s=s.replace(bridge['removed_completed_stages'],bridge['replacement'])
for a,b in bridge['replacements']:assert a in s;s=s.replace(a,b)
assert s==(B/'continue_native03.py').read_text()
for a,b in [('continuation-status03','continuation-status04'),('continuation-policy03','continuation-policy04'),('continuation-owner03','continuation-owner04'),('native-source-only-peer03','native-source-only-peer04'),("name+'.controller.log'","name+'.recovery04.controller.log'")]:assert a in s;s=s.replace(a,b)
assert s==(B/'continue_native04.py').read_text()
# Independently enumerate actual invoked helper paths, not just substitutions.
stages=[]
for node in ast.walk(ast.parse(s)):
 if isinstance(node,ast.Call)and isinstance(node.func,ast.Name)and node.func.id=='stage':
  name=ast.literal_eval(node.args[0]);arg=node.args[1].elts[1].args[0];assert isinstance(arg,ast.BinOp)and isinstance(arg.left,ast.Name)and arg.left.id=='B';file=B/ast.literal_eval(arg.right)
  assert file.is_file()and str(file)in policy['method_pins']and pin(file)==policy['method_pins'][str(file)]
  assert not(B/(name+'.recovery04.controller.log')).exists();stages.append(dict(name=name,path=str(file),**pin(file)))
assert [v['name']for v in stages]==['saved_map_boundary_import','import_graph_proof','preplacement','timing_review','critical_path']
assert not any(v['path'].endswith(('run_balanced_map02.py','balanced_import02.py','measure_registered_boundary.py'))for v in stages)
q=json.loads((B/'native-recovery-basis03.json').read_text());assert q['status']=='SAVED_COMPLETE_V22_MAP_BOUNDARY_IMPORT_DISPATCH_TYPO_RETAINED'
for name,w in q['files'].items():assert pin(name)==w
assert q['boot_id']==Path('/proc/sys/kernel/random/boot_id').read_text().strip()
for birth in q['closed_births']:
 f=Path(f"/proc/{birth['pid']}/stat")
 assert not f.exists()or f.read_text().rsplit(') ',1)[1].split()[19]!=birth['start_ticks']
counts=[]
for dirname,status in [('nssoc-integrity-v22-balanced-map-01','COMPLETE_NATIVE_MAP_FUNCTIONAL_REPLAY_REQUIRED'),('nssoc-integrity-v22-balanced-import-01','PASS_GRAPH_METADATA_AND_LITERAL_TIE_IMPORT')]:
 base=Path('/dev/shm')/dirname;d=json.loads((base/'result.json').read_text());assert d['status']==status and d['returncode']==0
 for name,w in d['inputs'].items():assert pin(name)==w and q['files'][name]==w
 for name,w in d['outputs'].items():assert pin(base/name)==w and q['files'][str(base/name)]==w
 counts.append(dict(root=str(base),status=status,inputs=len(d['inputs']),outputs=len(d['outputs'])))
old=json.loads((B/'continuation-status02.json').read_text());assert [v['returncode']for v in old['stages']]==[0,0,0,2]
assert 'prove_balanced_import02.py'in (B/'import_graph_proof.controller.log').read_text()
assert not Path('/dev/shm/nssoc-integrity-v22-balanced-sta-01').exists()
a=(B/'detach_native03.py').read_text()
for x,y in [('continuation-policy03','continuation-policy04'),('native-source-only-peer03','native-source-only-peer04'),('continuation-status03','continuation-status04'),('detached-native03','detached-native04'),('continue_native03','continue_native04')]:a=a.replace(x,y)
a=a.replace(str(pin(B/'continuation-policy03.json')),str(pin(p))).replace("with (B/'detached-native04-once.json')", "assert not list(B.glob('*.recovery04.controller.log')), 'Fresh recovery logs required'\nwith (B/'detached-native04-once.json')")
assert a==(B/'detach_native04.py').read_text()
r=dict(status='PASS_SOURCE_ONLY_V22_MERGED_NATIVE_CONTINUATION',policy=pin(p),findings=[],method=pin(__file__),detacher=pin(B/'detach_native04.py'),recovery_basis=pin(B/'native-recovery-basis03.json'),all_saved_files_rehashed=len(q['files']),saved_native=counts,enumerated_actual_stage_paths=stages,historical_peer_miss=pin(B/'native-peer02-stage-path-correction.json'),historical_prelaunch_finding=pin(B/'native-source-only-peer03-findings-vco.json'),scope='Read-only source and saved-byte review. Whole02→03 and03→04 bodies reconstructed; exact completed map/boundary/import reused, actual dispatch exit2 and all old logs retained; five actual helper paths exist and are pinned, new exclusive log paths absent. Same owned stage lifecycle and corrected02 STA floor/birth cleanup; original4ns PDK/RTL profile unchanged. No reviewed method, map/import/STA, control or native rerun.')
out=B/'native-source-only-peer04.json';assert not out.exists();out.write_text(json.dumps(r,indent=2)+'\n');print(pin(out))
