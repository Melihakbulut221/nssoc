from pathlib import Path
import ast,datetime,hashlib,json
R=Path.cwd();B=R/'hw/soc/out/pcie-integrity-v18-20261005';OLD=B.parent/'pcie-integrity-v17-20261005'
def pin(p):
 with Path(p).open('rb') as f:return dict(bytes=Path(p).stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
def dump(name,obj):
 with (B/name).open('x') as f:json.dump(obj,f,indent=2);f.write('\n')
s=(OLD/'continue_after_controls_v3.py').read_text().replace('V17','V18').replace('v17','v18').replace('continuation-status03','continuation-status01').replace('continuation-policy03','continuation-policy01').replace('continuation-owner03','continuation-owner01').replace('48a78275df28c51417f5e318750ccc77d933ccf34fd7188cdc3158445e101dcd','5b09e04a09709043074263ca9af866d38fe9067379ef11ffec0b2ad1ca6e1143').replace('WAITING_EXISTING_FROZEN_CONTROLS','VALIDATING_COMPLETED_FROZEN_CONTROLS')
a=s.index(' active=dict(');z=s.index('\n life.atomic',a)
s=s[:a]+" active=dict(status=record['status'],utc=record['utc'],continuation=dict(path=str(B/'continuation-status01.json'),controller=record['controller'],owner=str(B/'continuation-owner01.json')),V18_source_freeze=dict(path=str(B/'source-freeze.json'),**pin(B/'source-freeze.json')),completed_controls=policy['completed_controls'],PLL=policy['PLL'],next='Owned same2GiB CPU6 map, measured native read depth, literal-tie import+allpin graph proof and original4ns three-corner preplacement. All21 functional predicates complete; no PLL duplicate and no constraints relaxed.')"+s[z:]
a=s.index("  expected=policy['controls']");z=s.index("  stage('map'",a)
s=s[:a]+"  for gate in policy['completed_controls']:\n   p=Path(gate['path']);assert pin(p)=={k:gate[k] for k in ('bytes','sha256')}\n   assert json.loads(p.read_text())['status']==gate['status']\n  assert pin(B/'source-only-peer-pll02.json')==policy['peer_pin']\n  assert json.loads((B/'source-only-peer-pll02.json').read_text())['status']=='PASS_V18_FINAL_SOURCE_AND_CORRECTED_FOCUSED_HARNESS_PEER'\n"+s[z:]
with (B/'continue_native01.py').open('x') as f:f.write(s)
base=ast.parse((OLD/'continue_after_controls_v3.py').read_text());cur=ast.parse(s)
for name in ['pin','explicit_stop','verify_sources','stage']:
 x=next(n for n in base.body if isinstance(n,ast.FunctionDef) and n.name==name);y=next(n for n in cur.body if isinstance(n,ast.FunctionDef) and n.name==name)
 assert ast.dump(x,include_attributes=False)==ast.dump(y,include_attributes=False),name
assert 'supersession' not in s and "stage('seal_controls'" not in s
freeze=json.loads((B/'source-freeze.json').read_text())
for p,v in freeze['files'].items():assert pin(R/p)==v
methods=['run_balanced_map.py','measure_native_read_depth.py','balanced_import.py','prove_balanced_import.py','balanced_preplacement.py','review_timing.py','analyze_critical_path.py','peer-pin.json','source-only-peer-pll02.json','source-freeze.json','continue_native01.py','pcie-integrity-v18-core-controls-validation-20261005.json','public-controls-validation01.json','commit-controls02-validation.json']
gates=[]
for name in ['pcie-integrity-v18-core-controls-validation-20261005.json','public-controls-validation01.json','commit-controls02-validation.json']:
 p=B/name;j=json.loads(p.read_text());assert j['status'].startswith('PASS');gates.append(dict(path=str(p),**pin(p),status=j['status']))
prior=json.loads((OLD/'continuation-policy03.json').read_text())
policy=dict(method_pins={str(B/n):pin(B/n) for n in methods},source_pins=freeze['files'],completed_controls=gates,peer_pin=pin(B/'source-only-peer-pll02.json'),PLL=prior['PLL'],profile=prior['profile'],continuation_source_basis=dict(path=str(OLD/'continue_after_controls_v3.py'),**pin(OLD/'continue_after_controls_v3.py')),lifecycle_controls_inherited=prior['lifecycle_controls_inherited'],lifecycle_peer_inherited=prior['lifecycle_peer'],scope='No prior job supersession or control waiting; all functional gates already PASS. Original owner and stage teardown unchanged. One fresh native chain only.')
dump('continuation-policy01.json',policy)
checks={}
for name in ['balanced_import.py','balanced_preplacement.py','prove_balanced_import.py','analyze_critical_path.py']:
 assert (OLD/name).read_text().replace('v17','v18').replace('V17','V18')==(B/name).read_text();checks[name]='Exact version substitution only'
assert (OLD/'measure_native_read_depth.py').read_text().replace('analyze(a.candidate,17)','analyze(a.candidate,18)')==(B/'measure_native_read_depth.py').read_text();checks['measure_native_read_depth.py']='Exact candidate version integer only'
checks['run_balanced_map.py']='Same native commands, limit/teardown functions and profile. Sourcefreeze/publicraw/peer/core PASS gate and scope replacements only.'
a=(OLD/'run_balanced_map.py').read_text().replace('v17','v18').replace('V17','V18').replace('48a78275df28c51417f5e318750ccc77d933ccf34fd7188cdc3158445e101dcd','5b09e04a09709043074263ca9af866d38fe9067379ef11ffec0b2ad1ca6e1143').replace('v18-controls01','v18-public-controls01').replace('PASS_BALANCED_PAYLOAD_TREE_AND_ACTUAL_PUBLIC_FAULT_CONTROLS','PASS_BALANCED_COMMIT_AND_ACTUAL_PUBLIC_FAULT_CONTROLS').replace('source-only-peer-rx.json','source-only-peer-pll02.json').replace('Separate V18 balancedknown-eligibilitypayload read fromfrozenV11; allV11writes/control/fault/commit unchanged.','Separate V18 balancedlastcommitselection fromfrozenV17; alloriginalparserbranches andotheroutputs preserved.')
assert a==(B/'run_balanced_map.py').read_text()
checks['review_timing.py']='Frozen V4 parser and entire V17 timing analysis unchanged, with immediate-V17 delta added alongside V11.'
a=(OLD/'review_timing.py').read_text().replace('v17-balanced-sta','v18-balanced-sta')
b=(B/'review_timing.py').read_text();i=b.index('previous17 = ');z=b.index('markers = ',i);b=b[:i]+b[z:];b=b.replace(', delta_vs_v17=delta17','').replace("'delta_vs_v17':delta17,",'')
assert a==b
proof=dict(status='PASS_EXACT_INHERITED_NATIVE_LIFECYCLE_AND_PROFILE_BRIDGES',utc=datetime.datetime.now(datetime.UTC).isoformat(),methods=policy['method_pins'],sources_checked=len(freeze['files']),controller_functions_AST_exact=['pin','explicit_stop','verify_sources','stage'],helper_bridges=checks,policy=pin(B/'continuation-policy01.json'),inherited_lifecycle=prior['lifecycle_peer'],scope='Source-only bridge verification; no duplicated HDL/lifecycle/native tests. Root authorized native profile after independent focused validation; gates cannot accept pending or changed sources.')
dump('native-source-bridge01.json',proof)
print(json.dumps({'policy':pin(B/'continuation-policy01.json'),'bridge':pin(B/'native-source-bridge01.json'),'controller':pin(B/'continue_native01.py')}))
