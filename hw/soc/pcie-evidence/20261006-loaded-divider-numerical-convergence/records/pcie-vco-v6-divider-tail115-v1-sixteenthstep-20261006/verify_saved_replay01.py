# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Execute exact saved-reader AST regions on already closed historical captures."""
from pathlib import Path
import ast,copy,gzip,hashlib,importlib.util,json,os,resource,sys
os.sched_setaffinity(0,{10});resource.setrlimit(resource.RLIMIT_AS,(2*1024**3,)*2)
import numpy as np
R=Path.cwd();B=Path(__file__).resolve().parent;E=B.parent/'pcie-vco-v6-divider-tail115-v1-eighthstep-20261006';S=B.parent/'pcie-tail115-streaming-replay-v1-20261006'
sys.path[:0]=[str(S),str(B),str(R/'scripts')]
from raw_table01 import open_table,file_pin
import characterize_sixteenthstep01 as characterizer
f=json.loads((S/'source-freeze01.json').read_text());assert all(file_pin(p)==v for p,v in f['pins'].items())
peer=json.loads((S/'source-only-peer-pll01.json').read_text());assert peer['status']=='PASS_SOURCE_ONLY_BOUNDED_SAVED_RAW_MEMMAP_READER'and peer['findings']==[]and peer['freeze']==file_pin(S/'source-freeze01.json')
roots=[(Path('/dev/shm/nssoc-vco-v6-divider-tail115-v1-'+n+'-06-01'),step)for n,step in [('wire',5e-12),('halfstep',2.5e-12),('quarterstep',1.25e-12),('eighthstep',6.25e-13)]]
inputs={str(p):file_pin(p)for p in [Path(__file__),B/'seal_probe01.py',B/'compare_saved_steps01.py',B/'characterize_sixteenthstep01.py',S/'source-freeze01.json',S/'source-only-peer-pll01.json',E/'step-comparison01.json']}
for root,_step in roots:
 for n in ['result.json','wave.raw.gz']:inputs[str(root/n)]=file_pin(root/n)
 expected=json.loads((root/'result.json').read_text())
 assert all(x['status']=='REAPED_NO_LIVE_MEMBERS'for x in json.loads((root/'owned-processes.json').read_text())['processes'])
 for p,v in expected['inputs'].items():assert file_pin(p)==v
 for p,v in expected['outputs'].items():assert file_pin(root/p)==v
# Only the outer iterator is replaced with explicit already closed historical roots.
# Every expression and assertion in the actual production capture loop is exact.
tree=ast.parse((B/'compare_saved_steps01.py').read_text());loop=next(n for n in tree.body if isinstance(n,ast.For)and isinstance(n.target,ast.Tuple)and [x.id for x in n.target.elts]==['root','step']);original_loop=ast.dump(loop,include_attributes=False)
replay=copy.deepcopy(loop);replay.iter=ast.Name(id='saved_roots',ctx=ast.Load());ast.fix_missing_locations(replay)
ns=dict(Path=Path,gzip=gzip,hashlib=hashlib,json=json,np=np,open_table=open_table,B=B,R=R,results=[],saved_roots=roots)
for name in ['pin','crossings']:
 node=next(n for n in tree.body if isinstance(n,ast.FunctionDef)and n.name==name);exec(compile(ast.Module(body=[node],type_ignores=[]),'exact_compare_function','exec'),ns)
exec(compile(ast.Module(body=[replay],type_ignores=[]),'exact_capture_loop_saved_roots','exec'),ns)
assert ns['results']==json.loads((E/'step-comparison01.json').read_text())['captures']
# Exact sealer context body: preserve all455 bounds, full measurements,
# actual timegrid and startup/OFF checks. Native-step precondition is separately
# checked by four exact recipe controls, so this region may replay an old step.
stree=ast.parse((B/'seal_probe01.py').read_text());block=next(n for n in stree.body if isinstance(n,ast.With)and isinstance(n.items[0].context_expr,ast.Call)and isinstance(n.items[0].context_expr.func,ast.Name)and n.items[0].context_expr.func.id=='open_table')
N=roots[-1][0];r=json.loads((N/'result.json').read_text());m=characterizer.core
with gzip.open(N/'wave.raw.gz','rb')as stream:header,meta=m.life.tiny.parse_header(stream,m.n.vectors(r['devices'],r['config']['extra_vectors']))
ss=dict(P=N,r=r,m=m,np=np,B=B,header=header,meta=meta,open_table=open_table)
exec(compile(ast.Module(body=[block],type_ignores=[]),'exact_sealer_saved_context','exec'),ss)
assert len(ss['contacts'])==31 and len(ss['other'])==424
assert all(file_pin(p)==v for p,v in inputs.items())
record=dict(status='PASS_EXACT_STREAMED_COMPARISON_AND_SEALER_SAVED_AST_CONTROLS',inputs=inputs,checks=[dict(name='all_four_closed_comparison_records_exact',captures=4,values=[x['full_values']for x in ns['results']],original_native_statuses=[x['native_status']for x in ns['results']],full_results_equal=True),dict(name='all_eighth455_sealer_bounds_measurements_timegrid_startup_exact',values=r['values'],HBT64_OFF=True,contacts31=True,original_native_status=r['status'])],production_loop_ast_sha256=hashlib.sha256(original_loop.encode()).hexdigest(),production_sealer_context_ast_sha256=hashlib.sha256(ast.dump(block,include_attributes=False).encode()).hexdigest(),peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,scope='Actual future loader regions executed on immutable historical files only. Comparator outer iterator alone selects four prior roots; every production loop body expression unchanged. Sealer exact context preserves original455/native/grid predicates; no archive or native source executed. Current native and numerical verdicts remain unchanged; no new simulation.')
(B/'saved-replay-controls01.json').write_text(json.dumps(record,indent=2)+'\n');print(file_pin(B/'saved-replay-controls01.json'),record['peak_rss_kib'])
