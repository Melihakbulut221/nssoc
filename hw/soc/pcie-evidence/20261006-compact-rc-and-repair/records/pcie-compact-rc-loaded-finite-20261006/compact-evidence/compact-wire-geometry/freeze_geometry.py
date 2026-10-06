from pathlib import Path
import hashlib,json
B=Path(__file__).resolve().parent;R=B.parents[3];OLD=B.with_name('pcie-divider-v7-power-v2-wire-v2-20261006');P=B.with_name('pcie-divider-v7-compact-v2-20261006');G=Path('/dev/shm/nssoc-div4-v7-compact-v2-layout-01');C=Path('/dev/shm/nssoc-div4-v7-compact-v2-checks-01')
def pin(p):
 p=Path(p)
 with p.open('rb') as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
closed=json.loads((C/'result.json').read_text());assert closed['status']=='PASS_DIV4_V7_COMPACT_V2_STANDALONE_MAIN_DRC_STRICT_DEEP_FLAT_LVS_LEF_NEGATIVE_CONTROLS_ONLY' and len(closed['steps'])==21;assert closed['outputs']=={n:pin(C/n)['sha256'] for n in closed['outputs']}
assert closed['power_geometry_audit']['power_arrays']==47 and closed['power_geometry_audit']['physical_primitives']==91
peerpath=P/'native-saved-peer-rx.json';peer=json.loads(peerpath.read_text());assert peer['status']=='PASS_INDEPENDENT_SAVED_COMPACT_V2_NATIVE_RESULT' and peer['findings']==[];assert peer['checks']==pin(C/'result.json') and peer['geometry']==pin(C/'power-geometry.json') and peer['GDS']==pin(G/'nssoc_clock_div4_v7_compact_v2_layout.gds') and peer['ready']==pin(P/'native-finite-review-ready01.json')
inputs={}
for p in [OLD/'geometry-source-freeze.json',P/'source-freeze01.json']:
 f=json.loads(p.read_text());assert f['inputs']=={p:pin(p) for p in f['inputs']};inputs.update(f['inputs']);inputs[str(p)]=pin(p)
for p in [*G.rglob('*'),*C.rglob('*'),*B.glob('*.py'),B/'native_unsimplified.lvs',B/'source-bridge01.json',B/'draft-only.json',OLD/'geometry-source-only-peer.json',OLD/'saved-geometry-peer.json',P/'source-only-peer01-pll.json',peerpath,P/'native-finite-review-ready01.json',P/'native-archive01.json']:
 if p.is_file():inputs[str(p)]=pin(p)
r=dict(status='FROZEN_FRESH_COMPACT_V2_NATIVE_WIRE_GEOMETRY_REQUIRES_SOURCE_PEER',inputs=inputs,producer_sources={str(B/n):pin(B/n) for n in ['run_geometry.py','probe_native_cells.py','probe_device_locations.py','probe_wire_components.py','probe_terminal_anchors.py','prepare_anchors.py','bind_source_ids.py','native_unsimplified.lvs']},source_expected_census=dict(devices=91,terminals=283,metal_terminals=198,body_terminals=85,anchors=205,ports=7,conductors=37),actual_prior_hierarchy_census=dict(devices=91,via_stack=634,all_leaves=725),complete_native_cluster_partition_expected=dict(raw=72,electrical=38,body_only=1,auxiliary=34),prior_completed_native_layout=pin(C/'result.json'),new_native_extraction=True,original_source_and_all_intrinsic_models_unchanged=True,no_qualified_pex=True,scope='Fresh compact layout with actual DRC/LVS21 and nativegeometry4 pass. Seven parent wire methods retain all91/283/205/37/72 strict geometry/full source bijection checks. No body terminal deletion or implicit short; seven active metal layers remain mandatory. Actual RC and loaded455 still separate.')
p=B/'geometry-source-freeze.json';assert not p.exists();p.write_text(json.dumps(r,indent=2)+'\n');print(pin(p),len(inputs))
