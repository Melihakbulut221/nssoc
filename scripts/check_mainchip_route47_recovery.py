"""Check recovery source deltas and hostile transport metadata without native CAD."""
import ast,json,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def source(p):return(ROOT/p).read_text()
def fn(s,name):
 t=ast.parse(s);return next(n for n in t.body if isinstance(n,ast.FunctionDef)and n.name==name)
def body(s,name):return ast.dump(fn(s,name),include_attributes=False)
old=source('scripts/mainchip_snapshot_reload_inner.py');new=source('scripts/mainchip_route47_recovery_inner.py')
# Main keeps original runtime, cgroup, source, supervision and cleanup controls.
normalized=old.replace('COMPLETE_ACTUAL47_NATIVE_ROUTE_OBSERVATION','COMPLETE_ACTUAL47_SNAPSHOT19_OBSERVATION').replace('FAIL_ACTUAL47_NATIVE_ROUTE_OBSERVATION','FAIL_ACTUAL47_SNAPSHOT19_OBSERVATION')
assert body(normalized,'main')==body(new,'main')
a=fn(old,'execute');b=fn(new,'execute');assert isinstance(b.body[0],ast.If)
assert ast.dump(ast.Module(body=a.body,type_ignores=[]),include_attributes=False)==ast.dump(ast.Module(body=b.body[1:],type_ignores=[]),include_attributes=False)
oldh=source('scripts/cloud_mainchip_snapshot_reload.py');newh=source('scripts/cloud_mainchip_route47_recovery.py')
for name in('sha','fp','api','write','own_sources','acquire_snapshot'):assert body(oldh,name)==body(newh,name)
native=source('scripts/mainchip_route47_recovery_native.py')
assert native.index('sys.path.insert(0,"/work/tail-source/scripts")')<native.index('import mainchip_route47_native as n')
c=json.loads((ROOT/'scripts/mainchip-route47-recovery-inputs.json').read_bytes())
assert c['producer']['run']==41415994457 and c['producer']['source']=='f808321a65ca9197f10e75f2f59073d47095a718'
assert len(c['index']['files'])==100 and len(c['selected'])==len(set(c['selected']))==7
assert set(c['selected'])<=set(c['index']['files'])
assert c['index']['files']['work/bulk-postdrt-antenna/drt_iter19.odb']==dict(bytes=214392179,sha256='a93e921ccd7abb164dbe2ff3f6a1a1c26777d707399cea7580d7c5d08ea11017')
assert 'routed-fixed.odb'not in ''.join(c['index']['files'])
phases=next(n for n in ast.parse(new).body if isinstance(n,ast.Assign)and any(isinstance(t,ast.Name)and t.id=='PHASES'for t in n.targets))
assert ast.literal_eval(phases.value)==('recover','route-restore','restore-import','route-audit','final-check','measure')
from mainchip_snapshot_reload_contract import validate_archive_member
count=0
for name,regular,size in [('../escape',True,1),('/absolute',True,1),('unknown',True,1),(c['selected'][0],False,c['index']['files'][c['selected'][0]]['bytes']),(c['selected'][0],True,1)]:
 try:validate_archive_member(name,regular,size,c['index']['files'],set())
 except AssertionError:count+=1
 else:raise AssertionError(name)
assert count==5
out=ROOT/'route47-recovery-controls';out.mkdir()
(out/'result.json').write_text(json.dumps(dict(status='PASS_RECOVERY_SOURCE_AND_TRANSPORT_CONTROLS',negative_transport_controls=count,original_native_audits_unchanged=True,current_route_calls=0,native_executed=False,physical_acceptance=False,timing_accepted=False),sort_keys=True,indent=2)+'\n')
print('PASS recovery source deltas, five hostile transport controls and exact saved candidate')
