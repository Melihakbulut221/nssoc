# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Freeze complete finite570 recipes, dependencies and closed controls only."""
from pathlib import Path
import ast,difflib,hashlib,json,math,os,shutil,sys,zlib
import numpy as np
B=Path(__file__).resolve().parent;R=Path.cwd();sys.path.insert(0,str(B))
import characterize_clamped570_02 as m

def pin(path):
 path=Path(path)
 with path.open('rb')as f:return dict(bytes=path.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())

def main():
 assert not(B/'source-freeze02.json').exists()and not m.NATIVE_ROOT.exists()
 assert sys.executable==str(R/'hw/soc/tools/cocotb-venv/bin/python')
 assert os.sched_getaffinity(0)=={10}
 controls={}
 for label,folder,count in [('finite','finite-controls05',11),('storage','storage-controls04',23),('lifecycle','lifecycle-controls04',7)]:
  path=B/folder/'result.json';d=json.loads(path.read_text());assert d['status'].startswith('PASS_')and d['cases']==count
  assert d.get('source',d.get('producer',d.get('driver')))==pin(Path(m.__file__))
  assert all(x['passed']for x in d['outcomes']);controls[label]=dict(path=str(path),pin=pin(path),cases=count,status=d['status'])
 recipes=[]
 for v in m.POINTS:
  c,rows,texts=m.config(v);deck=m.deck(c,rows,texts);vectors=m.n.vectors(rows,c['extra_vectors'])
  assert len(rows)==570 and len(vectors)==1133 and deck.count('.tran ')==1 and '3.125e-13' in deck
  (B/f'recipe02-v{int(v*100):03d}.cir').write_text(deck)
  recipes.append(dict(vctrl=v,config=c,devices=rows,physical_texts=texts,deck=deck,observations=vectors))
 (B/'recipes02.json').write_text(json.dumps(recipes,indent=2)+'\n')
 # The whole parent functions are included in the already written bridge.
 bridge=json.loads((B/'driver-source-bridge02.json').read_text());assert bridge['output']==pin(Path(m.__file__))
 tree=ast.parse(Path(m.__file__).read_text())
 for row in bridge['functions']:
  node=next(x for x in tree.body if isinstance(x,(ast.FunctionDef,ast.ClassDef))and x.name==row['name'])
  assert ast.get_source_segment(Path(m.__file__).read_text(),node)+'\n'==row['after']
 assert next(x for x in bridge['functions']if x['name']=='run_native')['before']==next(x for x in bridge['functions']if x['name']=='run_native')['after']
 sourcefreeze=m.S/'source-freeze01.json';source=json.loads(sourcefreeze.read_text());parent=m.P16/'source-freeze01.json';old=json.loads(parent.read_text());paths=set()
 for inventory in (source['inputs'],old['pins']):
  for p,value in inventory.items():assert pin(p)==value,p;paths.add(Path(p))
 paths.update([sourcefreeze,m.S/'source-contract-peer-root01.json',parent,m.P16/'source-only-peer01-root.json',m.P16/'launch-runtime-freeze01.json'])
 N=Path('/dev/shm/nssoc-vco-v6-divider-tail115-v1-sixteenthstep-06-01');native=json.loads((N/'result.json').read_text())
 assert native['status']=='PASS_NATIVE_LOADED_FEEDBACK_SCREEN'
 paths.update([N/'result.json',N/'wave.raw.gz'])
 # Explicit arithmetic is before launch; no claim about a real570 waveform.
 columns=1134;width=columns*8;rawmax=m.MAX_ROWS*width+m.HEADER_CAP+64
 # zlib's conservative compressBound expression plus extra gzip header margin.
 gzipbound=rawmax+(rawmax>>12)+(rawmax>>14)+(rawmax>>25)+64
 auxiliary=m.POINT_LIMIT-gzipbound-m.RECEIPT_RESERVE
 assert auxiliary>200*1024**2 and 3*m.POINT_LIMIT<=m.AGGREGATE_LIMIT
 resource_contract=dict(status='PREDECLARED_FINITE570_THREE_POINT_SSD_RESOURCE_ENVELOPE',points_v=list(m.POINTS),native_root=str(m.NATIVE_ROOT),raw_columns=columns,saved_vectors=1133,maximum_accepted_rows=m.MAX_ROWS,row_bytes=width,grid_rows_without_extra=math.floor(34e-9/3.125e-13)+1,raw_payload_cap=m.MAX_ROWS*width,header_cap=m.HEADER_CAP,actual_inherited_header_bound=65536+4097,raw_total_limit=rawmax,conservative_gzip_bound=gzipbound,point_cap=m.POINT_LIMIT,three_point_caps=3*m.POINT_LIMIT,aggregate_cap=m.AGGREGATE_LIMIT,remaining_per_point_for_all_spice_op_logs_metadata=auxiliary,receipt_reserve=m.RECEIPT_RESERVE,failed_tail_reserve=m.FAILED_TAIL_RESERVE,CPU=10,address_space_limit=2*1024**3,native_file_size_limit=45*1024**2,shared_entry_floor=1024**3,shared_continuous_terminal_floor=m.FLOOR,ssd_entry_free='4GiB minus already retained aggregate bytes plus1GiB floor',ssd_continuous_terminal_floor=m.SSD_FLOOR,all_regular_files_counted=True,only_nonregular='exact direct-point stream.fifo',elapsed_watchdog=None,observations_retained_bound=dict(vectors=len(m.OBS),float64_bytes=m.MAX_ROWS*len(m.OBS)*8,notes='Only bounded observation rows retained; raw full-width payload is processed in65536-byte chunks. finish concatenation and per-device block temporary arrays still count against actual2GiBAS. ngspice memory is independently limited by child2GiBAS; no inferred PASS.'),failure_scope='Normal data writes reserve2MiB; only an already-failing capture may consume at most1MiB to fsync the exact prefix already received. It always re-raises. This can cross a triggering shared/SSD operational floor during failed-only closure but cannot produce PASS; at least1MiB actual SSD space and both byte caps remain required. Hardware/I/O failure or external complete disk exhaustion can still prevent preservation; no power-loss or resume guarantee.',durability='Finite gzip fsync at close only. Live compressed tail is not crash durable and is not a solver checkpoint. Original failed gzip/source/log/OP and received prefix retained; unread FIFO data is not claimed captured.',numerical_scope='Each point uses one0.3125ps full34ns run. No570 adjacent-step convergence, pump reachability, signed tuning range or closed-loop acceptance is inherited from455 N16.')
 (B/'resource-contract02.json').write_text(json.dumps(resource_contract,indent=2)+'\n')
 selected_runtime={str(Path(sys.executable)):pin(sys.executable),str(Path(sys.prefix)/'pyvenv.cfg'):pin(Path(sys.prefix)/'pyvenv.cfg')}
 package=Path(np.__file__).parent
 for root in (package,package.parent/'numpy.libs'):
  if root.exists():paths.update(p for p in root.rglob('*')if p.is_file()and '__pycache__'not in p.parts and p.suffix!='.pyc')
 for module in tuple(sys.modules.values()):
  path=getattr(module,'__file__',None)
  if path and Path(path).is_file():
   path=Path(path)
   if path.suffix=='.pyc'and path.with_suffix('.py').exists():path=path.with_suffix('.py')
   if path.suffix!='.pyc':paths.add(path)
 paths.update(map(Path,selected_runtime));paths.add(Path(shutil.which('taskset')))
 runtime=dict(status='SELECTED_LEXICAL_RUNTIME_AND_NUMPY_PINNED',python=sys.executable,python_version=sys.version,numpy_version=np.__version__,numpy_root=str(package),selected=selected_runtime,taskset=str(shutil.which('taskset')),env_removed=['PYTHONPATH','PYTHONHOME','PYTHONEXECUTABLE','PYTHONOPTIMIZE','LD_PRELOAD','GH_TOKEN','GITHUB_TOKEN'],scope='Authoritative41 controls rerun using this exact selected lexical runtime. Earlier preparation controls used MinicondaPython3.14/NumPy2.5.2 and remain historical. Selected production is Python3.12/NumPy2.5.3; exact current interpreter/config/imported modules and complete NumPy nonbytecode distribution are frozen.')
 (B/'runtime02.json').write_text(json.dumps(runtime,indent=2)+'\n')
 for p in B.rglob('*'):
  if p.is_file()and '__pycache__'not in p.parts and p.suffix!='.pyc':paths.add(p)
 for p in B.parent.glob('pcie-tail115-connected570-*.log'):paths.add(p)
 # The freezer stdout lives outside this selected glob to prevent self-log drift.
 for p in paths:assert not p.name.startswith('source-freeze')or p!=B/'source-freeze02.json'
 pins={str(p.absolute()):pin(p)for p in sorted(paths)}
 outputs=['driver_custom02.py','capture_custom02.py','prepare_driver02.py','characterize_clamped570_02.py','launch_three02.py','test_finite_controls05.py','test_storage_controls04.py','test_lifecycle_controls04.py','freeze_source02.py']
 record=dict(status='FROZEN_CLAMPED570_THREE_POINT_DIAGNOSTICS_PENDING_SOURCE_PEER',pins=pins,products={name:pin(B/name)for name in outputs},source570_freeze=pin(sourcefreeze),source570_peer=pin(m.S/'source-contract-peer-root01.json'),parent455_freeze=pin(parent),full_driver_bridge=pin(B/'driver-source-bridge02.json'),recipe_pin=pin(B/'recipes02.json'),resource_contract=pin(B/'resource-contract02.json'),runtime=pin(B/'runtime02.json'),actual_controls=controls,actual_cases=41,inherited_source_handoff_controls=old['inherited_controls'],predeclared=dict(points_v=list(m.POINTS),models=570,HBT=64,contacts=31,source_model_terminals=2097,wire_resistors=1271,wire_capacitors=1414,saved_vectors=1133,columns=1134,step_s=3.125e-13,stop_s=34e-9,window_s=[4e-9,34e-9],original_division_checks=13,new_idle_clamp_checks=4,polarity_selected=False),scope='Source/control-only. One new sequential3point finite SSD campaign after independent peer and fresh boot/runtime/resource checks. Full570 safety and exact original13 division/startup/log gates unchanged; added PFD idle/reset/actual external clamp/current checks. No new native yet; no tuning sign/range, quasistatic pump force, connected-loop/PLL/CDR, longrun/PVT or fullPHY acceptance. Historical455 functional/numerical outcomes retain their original separate finite scope.')
 (B/'source-freeze02.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(dict(pins=len(pins),freeze=pin(B/'source-freeze02.json'),driver=pin(Path(m.__file__)),actual_cases=41,resource=resource_contract)))
if __name__=='__main__':main()
