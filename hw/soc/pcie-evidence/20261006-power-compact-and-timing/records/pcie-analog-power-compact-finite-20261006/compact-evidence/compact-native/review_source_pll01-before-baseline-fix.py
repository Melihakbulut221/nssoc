"""Independent compact-source, preserved control and deterministic coordinate review; no native work."""
from pathlib import Path
import ast,collections,hashlib,json,re
R=Path.cwd();B=R/'hw/soc/out/pcie-divider-v7-compact-v2-20261006';F=B/'source-freeze01.json'
def pin(p):
 p=Path(p)
 with p.open('rb')as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
def funcs(p):
 return {n.name:ast.dump(n,include_attributes=False)for n in ast.parse(Path(p).read_text()).body if isinstance(n,(ast.FunctionDef,ast.ClassDef))}
assert pin(F)['sha256']=='faf5e4fb2c7727c409cdc7db8122d976c0ad0d00232d5864ca01ba4c648cd983'
f=json.loads(F.read_text());assert len(f['inputs'])==498
for p,v in f['inputs'].items():assert pin(p)==v,(p,pin(p),v)
for p,v in f['product_sources'].items():assert pin(p)==v
bridges=json.loads((B/'source-bridge01.json').read_text());assert len(bridges)==7
for x in bridges:
 for side in ['before','after']:
  p=Path(x[side]['path']);assert pin(p)=={k:x[side][k]for k in ['bytes','sha256']};assert ''.join(r[side]for r in x['opcodes'])==p.read_text()
v1=B.with_name('pcie-divider-v7-compact-v1-20261006')
x=json.loads((v1/'generator-source-bridge.json').read_text())
for side in ['before','after']:
 p=Path(x[side]['path']);assert pin(p)=={k:x[side][k]for k in ['bytes','sha256']};assert ''.join(r[side]for r in x['opcodes'])==p.read_text()
flow=R/'hw/soc/flow';old=funcs(flow/'check_pcie_clock_div4_v7.py');new=funcs(flow/'check_pcie_clock_div4_v7_compact_v2.py')
for name in f['inherited_exact_checker_functions']:assert old[name]==new[name],name
# All source-graph/device/reference functions retain the exact earlier layout AST.
gold=funcs(flow/'make_pcie_clock_div4_v7_power_v2.py');gen=funcs(flow/'make_pcie_clock_div4_v7_compact_v2.py')
unchanged=[]
for n in gold:
 if n not in ['main','placement_plan']:
  assert gen[n]==gold[n],n;unchanged.append(n)
# Execute only three pure coordinate definitions. No producer main/import/native call.
tree=ast.parse((flow/'make_pcie_clock_div4_v7_compact_v2.py').read_text());selected=[n for n in tree.body if isinstance(n,ast.FunctionDef)and n.name in ['placement_plan','bus_offset','substrate_tap_position']]
ns={'TAPS':18,'PORTS':('CLKP','CLKN','QP','QN','DIV_AVDD','AVSS','SUB')};exec(compile(ast.Module(body=selected,type_ignores=[]),'pure-coordinate-source','exec'),ns)
base=Path('/dev/shm/nssoc-div4-v7-power-v2-layout-01/result.json');before=json.loads(base.read_text());rows=[r for r in before['instances']if r['kind']!='substrate_tap'];assert len(rows)==73
plan,starts,nets=ns['placement_plan'](rows);assert starts=={0:0.0,1:176.0,2:328.0}
# Independent compact coordinates from the SAVED predecessor's actual spatial order.
independent={};by={r['name']:r for r in rows};lanes={i:[]for i in range(3)};oldcollisions=[];clearances=[]
for rid,count in enumerate([30,17,26]):
 ordered=sorted([r for r in rows if r['placement_row']==rid],key=lambda r:r['placement_um'][0]);assert len(ordered)==count
 x=160.0
 for row in ordered:
  y=56.0 if row['kind']=='hbt'else 60-row['length_um']-(0.61 if row['kind']=='resistor'else 0.60)
  independent[row['name']]=(rid,x,round((starts[rid]+y)/.005)*.005)
  offsets={'hbt':(-9,-6,-3),'resistor':(-6,-3),'capacitor':(-9,-5)}[row['kind']]
  lanes[rid].extend(x+z for z in offsets)
  x+=36 if row['kind']=='capacitor'and row['width_um']==20 else 24
 assert x<=900
 for i in range(6):
  oldx=181+i*120
  if oldx in lanes[rid]:oldcollisions.append([rid,oldx])
  newx=171+i*120;clearances.append(min(abs(newx-k)for k in lanes[rid]))
assert independent==plan;assert len(oldcollisions)==12 and min(clearances)==4
assert len({ns['substrate_tap_position'](i,starts)for i in range(18)})==18
for i in range(18):assert ns['substrate_tap_position'](i,starts)==(170+(i%6)*120,starts[i//6]+4)
assert sum(len(x)for x in nets.values())==47
for rid,ordered in nets.items():
 heights=[ns['bus_offset'](ordered,n)for n in ordered];assert heights[0]==72
 for a,b,pa,pb in zip(ordered,ordered[1:],heights,heights[1:]):assert pb-pa==(8 if {a,b}&{'DIV_AVDD','AVSS'}else 4)
# Version-only audit retains full geometry checks; source reviewed manually in full.
a=(flow/'audit_pcie_clock_div4_v7_compact_v2.py').read_text();assert a.replace('compact_v2','compact_v1')==(flow/'audit_pcie_clock_div4_v7_compact_v1.py').read_text()
checker=(flow/'check_pcie_clock_div4_v7_compact_v2.py').read_text();assert 'PASS_DIV4_V7_COMPACT_V2_STANDALONE' in checker
assert f['python']in f['inputs']and pin(f['python'])==f['inputs'][f['python']]
assert f['pdk'].endswith('/c4b8b4e5e7a05f375cca3815d51b3a37721fbf5c/ihp-sg13g2')
assert pin(B/'launch01.py')==f['launcher'];assert str(B/'prepare_launch01.py')in f['inputs']
assert all(not Path(f[k]).exists()for k in ['layout','checks'])
control=B/'source-controls02.log';assert control.read_text().strip().endswith('61 passed in 2.18s')
prior=B/'source-controls01.log';assert '1 failed, 60 passed' in prior.read_text()
# Rehash after all read-only inspection, including this final cut.
assert f['inputs']=={p:pin(p)for p in f['inputs']}
report=dict(status='PASS_SOURCE_ONLY_DIVIDER_V7_COMPACT_V2',findings=[],source_freeze=pin(F),source_pins=f['product_sources'],launcher=pin(B/'launch01.py'),preparer=pin(B/'prepare_launch01.py'),verified_inputs=len(f['inputs']),full_body_bridges=7,original_power_to_compact_bridge=True,exact_checker_functions=f['inherited_exact_checker_functions'],exact_source_graph_functions=unchanged,selected_python=dict(path=f['python'],**pin(f['python'])),pdk=f['pdk'],independent_coordinate_review=dict(saved_baseline=pin(base),primitive_count=73,groups=[30,17,26],starts=starts,new_device_positions=73,taps=18,row_buses=47,old_lane_collisions=oldcollisions,min_new_tap_to_device_escape_center_um=min(clearances)),geometry_review=['Read entire compact generator, original-to-compact full delta, both compact revisions, complete geometry audit and retained parent leaf/raw-GDS/via-template readers.','Audit requires exact unchanged91 device identities/metadata and per-instance native geometry at each declared new placement, plus634 via geometry multiset;725 total leaves. All47 power arrays bind actual placements, exact independent native cut/enclosure template, and independent rawGDS boundaries.','Eight power straps and47 local buses require actual full drawing coverage; exact7 topports,960um width and<600um height. Four actual in-memory geometry corruptions must fail exact named checks.','Topology/source/bias are unchanged; new coordinates/routes remain subject to fresh560category mainDRC, deep+flat91device LVS,8reference+6physical faults and3LEF predicates (21 steps). No fresh native result claimed.','V1 stale POWER_V2 final status corrected in separately namedV2; parent layout/context pinned.','Preparer binds all498 pins/current peer/boot/runtime; launcher requiresCPU10+fresh roots+1GiB then exec preserves birth/group. Tested ProcessOwner methods exact prior with2GiB/80MiB/512MiB guards, final-exit stop checks and no healthy timeout.'],saved_controls=dict(passed=61,log=pin(control),historical_failed_first_collision_witness=pin(prior),rerun_by_peer=False),method=pin(Path(__file__)),scope='Source/byte/coordinate review only. No layout generation, DRC/LVS/RC extraction, native transient or lifecycle test executed by reviewer; actual geometry and loaded455 acceptance remain pending.',native_run_by_peer=False)
p=B/'source-only-peer01-pll.json';assert not p.exists();p.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
