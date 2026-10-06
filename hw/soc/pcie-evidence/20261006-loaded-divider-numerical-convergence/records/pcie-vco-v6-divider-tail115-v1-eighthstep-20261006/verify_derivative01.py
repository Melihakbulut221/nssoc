# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Actual recipe/deck and bounded sparse scratch checks; no EDA."""
from pathlib import Path
import ast,hashlib,json,os,resource,sys,tempfile
os.sched_setaffinity(0,{10});resource.setrlimit(resource.RLIMIT_AS,(2*1024**3,)*2)
R=Path.cwd();B=Path(__file__).resolve().parent
sys.path[:0]=[str(B),str(R/'scripts'),str(B.parent/'pcie-vco-v6-divider-tail115-v1-quarterstep-20261006')]
import characterize_eighthstep01 as new
import characterize_quarterstep01 as old

def pin(p):
 p=Path(p)
 with p.open('rb') as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
checks=[];recipes=[]
for bias,fault in [(.6,''),(.85,''),(.6,'disconnect_divider_clock'),(.6,'wrong_feedback_modulus')]:
 a,ar,at=old.config(bias,fault);z,zr,zt=new.config(bias,fault)
 assert ar==zr and at==zt and len(ar)==455
 expected=dict(a,step_s=6.25e-13,sources=[str(B/'characterize_eighthstep01.py')if p==old.__file__ else p for p in a['sources']])
 assert z==expected
 da=old.deck(a,ar,at);dz=new.deck(z,zr,zt)
 assert da.count('.tran 1.25e-12 3.4e-08 0 1.25e-12')==1
 assert dz==da.replace('.tran 1.25e-12 3.4e-08 0 1.25e-12','.tran 6.25e-13 3.4e-08 0 6.25e-13')
 assert a['window_s']==z['window_s']==[4e-9,34e-9] and len(new.n.vectors(zr,z['extra_vectors']))==956
 recipes.append(dict(bias=bias,fault=fault,config=z,devices=zr,included_texts={k:dict(bytes=len(v.encode()),sha256=hashlib.sha256(v.encode()).hexdigest())for k,v in zt.items()},deck_sha256=hashlib.sha256(dz.encode()).hexdigest()))
 checks.append('exact455_recipe_and_only_tran_step_'+str(bias)+'_'+fault)
oldtree=ast.parse(Path(old.__file__).read_text());newtree=ast.parse(Path(new.__file__).read_text())
oldfn={x.name:ast.dump(x,include_attributes=False)for x in oldtree.body if isinstance(x,(ast.FunctionDef,ast.ClassDef))};newfn={x.name:ast.dump(x,include_attributes=False)for x in newtree.body if isinstance(x,(ast.FunctionDef,ast.ClassDef))}
exact=[k for k in oldfn if oldfn[k]==newfn[k]]
assert set(oldfn)-set(exact)=={'config','guard'}
for k in ['capture','measurement','native_limit']:
 a=old._scope[k];z=new._scope[k];assert a.__code__==z.__code__ and a.__defaults__==z.__defaults__ and a.__closure__==z.__closure__
assert new._scope['OWN_LIMIT']==new.OWN_LIMIT==512*1024**2 and old._scope['OWN_LIMIT']==256*1024**2
assert new._scope['guard'].__code__==new.guard.__code__ and new._scope['run_native'].__code__==new.run_native.__code__
assert new.FLOOR==old.FLOOR==512*1024**2 and new.RECEIPT_RESERVE==old.RECEIPT_RESERVE==2*1024**2
checks.append('exact_physics_screens_capture_lifecycle_and_scoped_budget')
# These real sparse files exercise the actual logical-byte accounting used by
# production guards, without allocating unnecessary shared-memory pages.
with tempfile.TemporaryDirectory(prefix='nssoc-halfstep-resource-control-',dir='/dev/shm')as raw:
 p=Path(raw);f=p/'owned-sparse.raw';inherited_bytes=new.guard(p)[1]
 with f.open('wb')as out:out.truncate(400*1024**2)
 assert new.guard(p)[1]==inherited_bytes+400*1024**2
 try:old.guard(p)
 except ValueError as e:assert 'Own256MiB' in str(e)
 else:raise AssertionError('Original cap unexpectedly accepted400MiB')
 checks.append('actual400MiB_sparse_owned_file_new_cap_pass_old_cap_reject')
 with f.open('r+b')as out:out.truncate(511*1024**2)
 try:new.guard(p)
 except ValueError as e:assert 'Own512MiB' in str(e)
 else:raise AssertionError('New cap ignored receipt reserve')
 checks.append('actual511MiB_sparse_owned_file_plus2MiB_reserve_rejected')
(B/'recipes01.json').write_text(json.dumps(recipes,indent=2)+'\n')
r=dict(status='PASS_EIGHTHSTEP_EXACT_RECIPE_DECK_AND_RESOURCE_CONTROLS',checks=checks,exact_function_classes=exact,source_pins={str(p):pin(p)for p in [Path(old.__file__),Path(new.__file__),Path(__file__)]},recipes=pin(B/'recipes01.json'),scope='No native/EDA launched. All455 rows and physical text bytes exactly unchanged for four recipes. Only output/maxstep1.25ps→0.625ps, fresh source/namespace, correct raw estimate and bounded512MiB cap differ. Original32+4 source/lifecycle controls are retained separately; no acceptance predicate change.')
(B/'derivative-controls01.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
