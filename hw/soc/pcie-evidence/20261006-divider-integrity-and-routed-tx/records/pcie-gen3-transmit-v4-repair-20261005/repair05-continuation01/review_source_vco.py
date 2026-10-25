from pathlib import Path
import ast,hashlib,json,re
R=Path.cwd();B=R/'hw/soc/out/pcie-gen3-transmit-v4-repair-20261005';C=Path(__file__).resolve().parent;Q=B/'repair05-peer'
def pin(p):
 p=Path(p)
 with p.open('rb')as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
m=json.loads((C/'manifest.json').read_text())
for group in ['inputs','route_inputs']:
 for name,w in m[group].items():assert pin(name)==w
rows=json.loads((C/'source-bridge.json').read_text());assert json.loads((Q/'source-derivation.json').read_text())==rows[:2];rows.append(json.loads((C/'launcher-source-bridge.json').read_text()))
for row in rows:
 for key in ['before','after']:assert pin(row[key]['path'])=={k:row[key][k]for k in ['bytes','sha256']}
 a=''.join(v['before']for v in row['opcodes']);b=''.join(v['after']for v in row['opcodes']);assert a==Path(row['before']['path']).read_text()and b==Path(row['after']['path']).read_text()
 for part in row['opcodes']:
  if part['tag']=='equal':assert part['before']==part['after']
func=lambda p,n:next(v for v in ast.walk(ast.parse(p.read_text()))if isinstance(v,(ast.FunctionDef,ast.ClassDef))and v.name==n)
old=Path(rows[2]['before']['path']);new=C/'run.py';t=func(new,'run_stage');o=func(old,'run_stage')
for node in ast.walk(t):
 if isinstance(node,ast.Call)and isinstance(node.func,ast.Attribute)and node.func.attr=='launch':
  e=[k for k in node.keywords if k.arg=='env'];assert len(e)==1
  assert ast.unparse(e[0].value)=="{k: v for k, v in os.environ.items() if k not in ('PYTHONPATH', 'PYTHONHOME', 'PYTHONEXECUTABLE')}";node.keywords.remove(e[0])
assert ast.dump(t,include_attributes=False)==ast.dump(o,include_attributes=False)
life=json.loads((C/'lifecycle-controls-reuse.json').read_text())
for name,w in life['inputs'].items():assert pin(name)==w
assert life['controls']==3 and life['exact_stage_AST_after_removing_only_env_sanitizer']and life['inner_helper_byte_equal_RX16']
assert (B/'owned_lifecycle05.py').read_bytes()==(B.parent/'pcie-gen3-receive-prefetch-v2-20261004/owned_lifecycle16.py').read_bytes()
text=(C/'run.py').read_text();assert "FAILURE_GRACE_SECONDS=15.0"in text and "528MiB terminal scratch floor"in text and text.index('    # A stop delivered')<text.rindex('        owner.check()')
assert "require(not RC.exists()"in text and 'original_DRT_owned_by_this_controller=False'in text
for name in ['detailed_rc_repair05.py','repair05-peer/review.py','repair05-peer/seal.py']:
 p=B/name;assert p.is_file()and str(p)in m['inputs']
assert m['candidate_netlist']=='/dev/shm/nssoc-tx-path-v4-postroute-repair-05/repaired.v'
assert m['boot_id']==Path('/proc/sys/kernel/random/boot_id').read_text().strip()
observed={}
for key in ['route_owner','route_native']:
 d=m[key];f=Path(f"/proc/{d['pid']}/stat").read_text().rsplit(') ',1)[1].split();assert f[0]!='Z'and f[19]==str(d['start_ticks'])and int(f[2])==d['process_group'];observed[key]=dict(pid=d['pid'],start_ticks=f[19],process_group=int(f[2]),state=f[0])
current=json.loads(Path('/dev/shm/nssoc-tx-path-v4-repair05-drt-01/result.json').read_text());assert current['inputs']==m['route_inputs'] and current['pid']==m['route_native']['pid']
assert not(C/'result.json').exists()and not Path('/dev/shm/nssoc-tx-path-v4-repair05-detailed-rc-01').exists()
# The150 annotations are harmless only after actual input connectivity checks.
review=(Q/'review.py').read_text();assert "len(cases) == 6"in review and 'len(values) == 4'in review and "('setup', 'hold', 'recovery', 'removal')"in review
assert 'len(unannotated) == 150'in review and 'assert set(connected) == set(loads)'in review
assert 'all(pin(path) == h for path,h in inputs.items())'in review and 'not recomputed[\'mismatches\']'in review
seal=(Q/'seal.py').read_text();assert 'assert actual == members'in seal and 'assert members == {name: pin(p)'in seal
for name in ['nssoc-tx-path-v4-postroute-repair-05','nssoc-tx-path-v4-repair05-equivalence','nssoc-tx-path-v4-repair05-physical-replay-02','nssoc-tx-path-v4-repair05-drt-01','nssoc-tx-path-v4-repair05-detailed-rc-01']:assert name in seal
for name in ['pcie-tx-repair05-preroute-validation-20261006.json','release01.json','package.json']:assert(B/'repair05-preroute-preservation'/name).is_file()
# Explicit immutable publication names must agree producer/controller.
for name in ['pcie-tx-repair05-finite-physical-validation-20261006.json']:assert name in seal and name in text
r=dict(status='PASS_SOURCE_ONLY_TX05_ROUTE_RC_CONTINUATION',manifest=pin(C/'manifest.json'),launcher=pin(C/'launch.py'),findings=[],method=pin(__file__),whole_source_bridges=len(rows),inputs_rehashed=len(m['inputs']),route_inputs_rehashed=len(m['route_inputs']),observed_existing_births=observed,prior_actual_lifecycle_controls=pin(C/'lifecycle-controls-reuse.json'),review=['Full reviewer/sealer/controller/launcher source read and all four whole-body inverse ledgers reconstructed. Exact current05 roots/ports02, prior03 actualRC comparison and finite failure-history source list verified.','Same original4ns/no false or multicycle exceptions; measured setup/hold/recovery/removal kept regardless of sign. All150 dummy-output exceptions require actual input-only netlist and fullSPEF clock-input bindings.','All five native roots and mandatory capture sets required; complete compiled gzip and expanded proof JSON hashes rechecked; unchanged canonical3850state/11680function proof rerun on saved bytes only, ten savedfaults and three actualport XML retained.','Controller observes exact original route but never signals it; zeroDRC and same proved netlist gate freshRC, exact saved-output review, fullmember readback then three unique immutableV3 assets.','Inherited owned stages and post-context guard exact except sanitized Python environment; terminal floor and15s outer/2s inner cleanup retained with three outer and actual nested saved controls.','Fresh detached source/manifest/boot/birth launcher gate, exclusive launch marker and filelogs; no native rerun or launch by reviewer.'],scope='Source-only review and saved-pin readback. Actual new routed RC/timing/peer/publication remains pending; no qualifiedPEX/fullPHY/chip or foundry acceptance.')
out=C/'source-only-peer-vco.json';assert not out.exists();out.write_text(json.dumps(r,indent=2)+'\n');print(pin(out))
