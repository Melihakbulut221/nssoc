from pathlib import Path
import json,hashlib,difflib
B=Path(__file__).resolve().parent;R=B.parents[3];OLD=B.parent/'pcie-divider-v7-wire-v5-20261005';O4=B.parent/'pcie-divider-v7-wire-v4-20261005'
def pin(p):return {'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
names=['probe_native_cells','probe_device_locations','probe_wire_components','probe_terminal_anchors','prepare_anchors','bind_source_ids','run_geometry'];bridges=[]
for name in names:
 old=(O4 if name=='run_geometry' else OLD)/(name+'.py');new=B/(name+'.py');s=old.read_text();t=s
 for a,b in [('nssoc-div4-v7-layout-01','nssoc-div4-v7-power-v2-layout-01'),('nssoc-div4-v7-checks-02','nssoc-div4-v7-power-v2-checks-02'),('nssoc-div4-v7-wire-native-02','nssoc-div4-v7-power-v2-wire-native-01'),('nssoc-div4-v7-wire-geometry-04','nssoc-div4-v7-power-v2-wire-geometry-01'),('nssoc-div4-v7-wire-geometry-05','nssoc-div4-v7-power-v2-wire-geometry-01'),('nssoc_clock_div4_v7_layout','nssoc_clock_div4_v7_power_v2_layout')]:t=t.replace(a,b)
 if name in ('probe_native_cells','probe_device_locations'):t=t.replace('==678','==725').replace('via_stack=587','via_stack=634')
 if name=='run_geometry':
  marker="        N.mkdir()\n";assert t.count(marker)==1;t=t.replace(marker,"""        completed = json.loads((C / 'result.json').read_text())
        assert completed['status'] == 'PASS_DIV4_V7_POWER_V2_STANDALONE_MAIN_DRC_STRICT_DEEP_FLAT_LVS_LEF_NEGATIVE_CONTROLS_ONLY'
        assert completed['outputs'] == {n: pin(C / n)['sha256'] for n in completed['outputs']}
        assert completed['power_geometry_audit']['status'] == 'PASS_ACTUAL_GDS_POWER_ONLY_ADDITION_AND_FOUR_GEOMETRY_CONTROLS'
        assert completed['power_geometry_audit']['independent_raw_gds_boundary_instances_verified'] == 47
        N.mkdir()
""")
 assert not new.exists();new.write_text(t);aa=s.splitlines(True);zz=t.splitlines(True);ops=[dict(tag=k,before=''.join(aa[a:b]),after=''.join(zz[c:d])) for k,a,b,c,d in difflib.SequenceMatcher(None,aa,zz,autojunk=False).get_opcodes()];bridges.append(dict(before=dict(path=str(old),**pin(old)),after=dict(path=str(new),**pin(new)),opcodes=ops))
p=B/'native_unsimplified.lvs';assert not p.exists();p.write_bytes((O4/'native_unsimplified.lvs').read_bytes());(B/'draft-source-bridge.json').write_text(json.dumps(bridges,indent=2)+'\n');(B/'draft-only.json').write_text(json.dumps({'status':'SOURCE_DRAFT_ONLY_NATIVE_POWER_LAYOUT_CHECKS_PENDING','native_executed':False,'source_peered':False,'fresh_intrinsic_count_required':91,'native_leaf_count_required':725,'vias_required':634,'all283terminals_205anchors_85bodyterms_37conductors_72unpurgedclusters_required':True,'scope':'Only paths/top label and actual47additional via-leaf census differ from completed source; fresh extraction and graph/geometry binding require completed powerGDS strict native checks first.'},indent=2)+'\n')
