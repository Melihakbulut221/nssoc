"""Independent saved-layout reader lifetime/source binding review, no native run."""
from pathlib import Path
import ast,hashlib,json
R=Path('/home/hasanmelih/Documents/ChatGPT/nnsoc');B=Path(__file__).resolve().parent
def pin(p):
 p=Path(p)
 with p.open('rb') as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
def funcs(p):return {n.name:ast.dump(n,include_attributes=False)for n in ast.parse(Path(p).read_text()).body if isinstance(n,ast.FunctionDef)}
fp=B/'source-freeze03.json';assert pin(fp)==dict(bytes=93629,sha256='9357282c68898e1a54017c4c6284c4238b003b85bb127b5ed1ee7fef289d9ace')
f=json.loads(fp.read_text());assert len(f['inputs'])==341
for p,v in f['inputs'].items():assert pin(p)==v,p
for p,v in f['product_sources'].items():assert pin(p)==v,p
bridges=json.loads((B/'source-bridge03.json').read_text());assert len(bridges)==3
for b in bridges:
 for side in ['before','after']:
  assert ''.join(o[side]for o in b['opcodes']).encode()==Path(b[side]['path']).read_bytes()
flow=R/'hw/soc/flow';old=funcs(flow/'audit_pcie_clock_div4_v7_power_v2.py');new=funcs(flow/'audit_pcie_clock_div4_v7_power_v3.py')
for n in ['pin','require','compare_regions','via_template','compare_instances']:assert old[n]==new[n],n
oc=funcs(flow/'check_pcie_clock_div4_v7_power_v2.py');nc=funcs(flow/'check_pcie_clock_div4_v7_power_v2_audit_v3.py')
same=[n for n in oc if n!='main'];assert all(oc[n]==nc[n]for n in same)
layout=Path('/dev/shm/nssoc-div4-v7-power-v2-layout-01')
assert {str(p.relative_to(layout)):pin(p)for p in layout.rglob('*')if p.is_file()}==f['layout_files']
failed=Path(f['actual_failure']['checks']);result=json.loads((failed/'result.json').read_text())
assert result['status']=='FAILED_OR_INCOMPLETE' and result['generation_execution']['returncode']==0
assert result['power_geometry_execution']['returncode']!=0 and not result['steps']
raw=(flow/'audit_pcie_clock_div4_v7_power_v3.py').read_text()
for key in ['old_layout, oldbox','new_layout, newbox','old_instance_layout, old_instances','new_instance_layout, new_instances','raw_vias = raw_gds_regions','independent_raw_gds_boundary_instances_verified=47']:
 assert key in raw
launch=(B/'launch03.py').read_text();assert "'--generate'" not in launch and "manifest['layout_files']" in launch
runtime=json.loads((B/'launch-runtime-freeze02.json').read_text())
for p,v in runtime['inputs'].items():assert pin(p)==v
assert runtime['PDK_files_already_in_source_freeze']=={p:v for p,v in f['inputs'].items()if p.startswith(runtime['selected_pdk_input_prefix'])}
prep=B/'prepare_launch03.py';ast.parse(prep.read_text())
assert not Path('/dev/shm/nssoc-div4-v7-power-v2-checks-02').exists()
r=dict(status='PASS_SOURCE_ONLY_DIVIDER_V7_POWER_V2_AUDIT_V3',freeze=pin(fp),source_pins=f['product_sources'],launcher=pin(B/'launch03.py'),findings=[],method=pin(Path(__file__)),prepare_launch=pin(prep),prior_source_peer=pin(B/'source-only-peer02-rx.json'),source_input_count=341,complete_three_source_inverse=True,unchanged_auditor_functions=['pin','require','compare_regions','via_template','compare_instances'],unchanged_checker_functions=same,saved_layout_files=f['layout_files'],
 review='Read complete three-file delta and new raw-GDS boundary parser. Both recursive drawing and instance readers now return their Layout owners, retained as four live variables for the full audit. No geometry/template/instance-bijection predicate is removed. New independent big-endian GDS record reader accepts only rectangular BOUNDARY elements in the selected native via cells, checks complete records, expected field set, closed five-point rectangle and exact class set; it rejects PATH/SREF/AREF/TEXT/BOX forms. All47 added instance local layer Regions must equal those actual raw GDS boundaries. Four geometry faults and every previous strict quantity remain unchanged. New checker changes only auditor/self-method binding; all other helper ASTs exact. Same-PID launch uses full four-file saved-layout hash inventory and fresh checks02, omits generation. Runtime addendum and90-file selected PDK prefix remain pinned.',
 actual_prior_result='Native physical generation exit0, then first auditor failed before any DRC/LVS stage; old failure, diagnostics and source bytes remain immutable. GDS118282bytes SHA663b60fc14cc9c8e2b4d9a5a758aee6bcd61bdf307c6b3a69a28e63bc470340c is reused exactly.',
 native_executed=False,limitations='Source-only reader correction approval. The lifetime explanation is supported by saved raw-boundary evidence but successful corrected native audit/DRC/LVS remains to be measured. No geometry or simulation rerun by reviewer; no RC, loaded455, fullPHY or manufacturing acceptance.')
p=B/'source-only-peer03-rx.json';assert not p.exists();p.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(dict(path=str(p),**pin(p))))
