"""Read-only guide audit: coordinate/admission controls without native geometry."""
import ast,json,hashlib,copy
from pathlib import Path
from decimal import Decimal
root=Path(__file__).resolve().parents[1]
src=(root/'scripts/mainchip_route47_guides_native.py').read_text();tree=ast.parse(src)
from mainchip_snapshot_reload_contract import need
ns=dict(need=need,Decimal=Decimal,json=json,hashlib=hashlib)
functions=[n for n in tree.body if isinstance(n,ast.FunctionDef)and n.name in('coordinate','intersects','validate_scope')]
assert len(functions)==3
exec(compile(ast.Module(body=functions,type_ignores=[]),'<exact audited pure functions>','exec'),ns)
assert ns['coordinate']('103.5800',1000)==103580
assert ns['coordinate']('-0.0050',2000)==-10
bad=0
for value,units in [('NaN',1000),('Infinity',1000),('0.0001',1000),('1.0',0),('1.0',True),(1.0,1000)]:
 try:ns['coordinate'](value,units)
 except ValueError:bad+=1
 else:raise AssertionError((value,units))
assert bad==6
f=ns['intersects']
assert f([0,0,10,10],[10,0,20,10])
assert not f([0,0,10,10],[11,0,20,10])
assert f([0,0,10,10],[5,5,5,5])
for a,b in [([10,0,0,10],[0,0,10,10]),([0,0,10,10],[False,0,10,10]),([0,0,10],[0,0,10,10])]:
 try:f(a,b)
 except ValueError:bad+=1
 else:raise AssertionError((a,b))
assert bad==9
fixture=json.loads((root/'scripts/mainchip-route47-guide-scope-fixture.json').read_bytes())
check=ns['validate_scope']
def run_scope(v):return check(v['result'],v['delta'],v['selection']['selected'])
assert run_scope(fixture)==dict(native_clock_and_other_wires_unchanged=True,complete_DEF_scope_verified=True,changed_signal_count=46,selected_signal_count=47,production_accepted=False)
def mutate(path,value):
 v=copy.deepcopy(fixture);p=v
 for k in path[:-1]:p=p[k]
 p[path[-1]]=value
 try:run_scope(v)
 except (ValueError,KeyError):return
 raise AssertionError(path)
cases=[
 (['delta','all_clocks_unchanged'],False),
 (['delta','all_other_wires_unchanged'],False),
 (['result','temporary47_protection_restored'],False),
 (['result','all_nonselected_wires_and_clocks_unchanged'],False),
 (['delta','complete_DEF','other_records_byte_exact'],False),
 (['delta','complete_DEF','non_NETS_bytes_exact'],False),
 (['delta','complete_DEF','accepted'],True),
 (['delta','complete_DEF','changed_signal_count'],45),
 (['delta','complete_DEF','changed_signal_count'],True),
 (['delta','complete_DEF','changed_signal_names_sha256'],'0'*64),
 (['delta','complete_DEF','changed_signal_names'],fixture['delta']['complete_DEF']['changed_signal_names'][:-1]),
 (['delta','selected'],fixture['delta']['selected'][:-1]),
 (['delta','changed'],fixture['delta']['changed'][:-1]),
 (['delta','mode'],'clear'),
 (['selection','selected'],fixture['selection']['selected'][:-1]),
 (['delta','changed'],fixture['delta']['changed'][:-1]+['outside-scoped-owner']),
]
for key in ('physical_acceptance','timing_accepted','full_phy_accepted'):
 for record in ('result','delta'):cases.append(([record,key],True))
for path,value in cases:mutate(path,value)
scope_negative_controls=len(cases)
assert scope_negative_controls==22
# Reproduces the old mistaken predicate using real preserved evidence.
assert fixture['delta']['complete_DEF']['accepted']is False
s=(root/'scripts/mainchip_route47_guides_inner.py').read_text();t=ast.parse(s)
assignment=next(n for n in t.body if isinstance(n,ast.Assign)and any(isinstance(x,ast.Name)and x.id=='PHASES'for x in n.targets))
assert ast.literal_eval(assignment.value)==('guide-audit',)
assert "report['snapshot_reload_qualified']=False"in s and "report['guide_observation_complete']=True"in s
assert 'write_db'not in src and 'write_def'not in src and 'detailed_route'not in src
assert 'odb.Rect(*r["bbox_dbu"]).intersects(odb.Rect(*g["box"]))'in src
cfg=json.loads((root/'scripts/mainchip-route47-guide-inputs.json').read_bytes())
assert cfg['producer']['run']==41440285882 and len(cfg['index']['files'])==72 and len(cfg['selected'])==6
assert len(set(cfg['selected']))==6 and set(cfg['selected'])<=set(cfg['index']['files'])
out=root/'route47-guide-controls';out.mkdir()
(out/'result.json').write_text(json.dumps(dict(status='PASS_READONLY_GUIDE_SOURCE_COORDINATE_CONTROLS',negative_controls=bad,scope_negative_controls=scope_negative_controls,actual_scope_fixture_run=41440285882,native_executed=False,geometry_changed=False,memory_cause_proven=False),sort_keys=True,indent=2)+'\n')
