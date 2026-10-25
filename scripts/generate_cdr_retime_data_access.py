#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Widen measured retime data conductors in real GDS, preserving every intrinsic drawing."""
import argparse,json,sys
from pathlib import Path
from run_cloud_tx_layout_repair import sha
ROOT=Path(__file__).resolve().parents[1]
TOP='nssoc_cdr_pd484_localbus_v12'
def generate(out):
 import pya
 baseline=out/'baseline/layout';dest=out/'layout';dest.mkdir()
 L=pya.Layout();L.read(str(baseline/(TOP+'.gds')));assert L.dbu==.001
 top=L.cell(TOP);assert top is not None
 old=json.loads((baseline/'result.json').read_text());oldbox=top.bbox()
 before={(L.get_info(i).layer,L.get_info(i).datatype):pya.Region(top.begin_shapes_rec(i)).merged()for i in L.layer_indexes()}
 diagnosis=json.loads((out/'diagnosis.json').read_text())
 wire=pya.LayoutToNetlist();wire.read(str(out/'capture/source/wire/native05/wires.l2n'))
 binding=json.loads((out/'capture/source/wire/native05/result.json').read_text())
 assert binding['no_wire_geometry_change'] and binding['no_component_union_by_native_label']
 clusters={};expected_tags={'c':('a','ac'),'d':('b','bd')}
 for tag,graph in diagnosis.items():
  assert (graph['source_stage'],graph['filter_macro'])==expected_tags[tag]
  for pol,leg in graph['legs'].items():
   for name in ('source_cluster','filter_output_cluster','master_input_cluster'):
    key=leg[name];assert key not in clusters
    clusters[key]=dict(stage=tag,polarity=pol,chain_point=name)
 assert len(clusters)==12
 nets={n.cluster_id:n for n in wire.netlist().top_circuit().each_net()}
 selected={}
 for native in clusters:
  rows=[r for r in binding['wire_components']if r['native_cluster']==native]
  assert len(rows)==1,('Native data net does not have exactly one conductor',native)
  component=rows[0]['component'];assert component in nets
  selected[native]=dict(component=component,native_name=rows[0]['native_name'])
 overlay=L.create_cell('nssoc_cdr_retime_data_metal_v16');plan=[];growth_by_layer={}
 for metal in (30,50,67):
  whole=before[(metal,0)];layer=wire.layer_by_name('gds_'+str(metal))
  for native,info in selected.items():
   original=wire.shapes_of_net(nets[info['component']],layer,True).merged()
   assert (original-whole).is_empty()
   if original.is_empty():continue
   foreign=(whole-original).merged()
   # This is a conservative placement clearance, not a replacement DRC rule.
   # Only native560-rule DRC and deep/flat LVS can accept the result.
   proposed=(original.sized(250)-foreign.sized(800))&pya.Region(oldbox)
   # Remove only newly proposed sub200nm necks/slivers. Preserve the
   # complete known-good original conductor by adding the cleaned delta.
   # The native width/spacing deck is still the final independent gate.
   cleaned=(proposed.sized(-100).sized(100)&proposed).merged()
   added=(cleaned-original).merged()
   assert (added&foreign).is_empty()
   if not added.is_empty():overlay.shapes(L.layer(metal,0)).insert(added)
   growth_by_layer[metal]=(growth_by_layer.get(metal,pya.Region())+added).merged()
   plan.append(dict(native_cluster=native,wire_component=info['component'],native_name=info['native_name'],
    chain=clusters[native],gds_layer=metal,original_area_dbu2=original.area(),added_area_dbu2=added.area(),
    requested_growth_nm=250,foreign_original_metal_clearance_nm=800,minimum_proposed_feature_nm=200,removed_proposed_sliver_area_dbu2=(proposed-cleaned).area()))
 assert len(plan)>=12 and all(any(p['native_cluster']==n and p['added_area_dbu2']>0 for p in plan)for n in clusters)
 top.insert(pya.DCellInstArray(overlay.cell_index(),pya.DTrans()))
 assert top.bbox()==oldbox
 addition={(L.get_info(i).layer,L.get_info(i).datatype):pya.Region(overlay.begin_shapes_rec(i)).merged()for i in L.layer_indexes()}
 after={(L.get_info(i).layer,L.get_info(i).datatype):pya.Region(top.begin_shapes_rec(i)).merged()for i in L.layer_indexes()}
 assert {k for k,v in addition.items()if not v.is_empty()}<={(30,0),(50,0),(67,0)}
 keys=set(before)|set(after)|set(addition)
 expected={k:(before.get(k,pya.Region())+addition.get(k,pya.Region())).merged()for k in keys}
 def verdict(got):return all((got.get(k,pya.Region())^expected.get(k,pya.Region())).is_empty()for k in keys|set(got))
 assert verdict(after) and all((before.get(k,pya.Region())-after.get(k,pya.Region())).is_empty()for k in keys)
 faults=[]
 metal=next(m for m,r in growth_by_layer.items()if not r.is_empty())
 removed=pya.Region(next(growth_by_layer[metal].each()))
 bad=dict(after);bad[(metal,0)]=after[(metal,0)]-removed
 assert not verdict(bad);faults.append('removed_actual_new_data_metal')
 bad=dict(after);bad[(5,0)]=after.get((5,0),pya.Region())+pya.Region(pya.Box(oldbox.right+1000,oldbox.top+1000,oldbox.right+1100,oldbox.top+1100))
 assert not verdict(bad);faults.append('changed_unrelated_gate_geometry')
 bad=dict(after);bad[(30,0)]=after[(30,0)]+pya.Region(pya.Box(oldbox.right+1000,oldbox.top+1000,oldbox.right+1100,oldbox.top+1100))
 assert not verdict(bad);faults.append('unplanned_data_layer_geometry')
 opt=pya.SaveLayoutOptions();opt.select_cell(top.cell_index());L.write(str(dest/(TOP+'.gds')),opt)
 for name in ('schematic.cir',TOP+'.lef'):(dest/name).write_bytes((baseline/name).read_bytes())
 check=pya.Layout();check.read(str(dest/(TOP+'.gds')))
 saved={(check.get_info(i).layer,check.get_info(i).datatype):pya.Region(check.cell(TOP).begin_shapes_rec(i)).merged()for i in check.layer_indexes()}
 assert check.dbu==.001 and verdict(saved)
 proof=dict(status='PASS_NATIVE_RETIME_DATA_METAL_OVERLAY_REQUIRES_DRC_LVS_AND_FRESH_RC',
  original_devices=484,selected_data_conductors=12,allowed_added_layers=[30,50,67],plan=plan,
  original_geometry_retained=True,all_layers_exact=True,serialized_gds_checked=True,reference_and_lef_byte_identical=True,
  rejected=faults,source_gds_sha256=sha(baseline/(TOP+'.gds')),candidate_gds_sha256=sha(dest/(TOP+'.gds')),
  electrical_accepted=False,qualified_pex=False,full_phy_accepted=False,
  scope='Only actual routed M3/M4/M5 metal enlargement on twelve measured retime source/filter/base conductors. All original metal, vias, intrinsic devices, placements, reference and LEF retained. Added capacitance and unchanged via resistance require fresh full RC/wave validation.')
 (out/'geometry-proof.json').write_text(json.dumps(proof,indent=2)+'\n')
 d=dict(old);d.update(status='GENERATED_RETIME_DATA_METAL_OVERLAY_REQUIRES_NATIVE_DRC_LVS_RC_AND_LOADED_GATES',
  retime_data_access=proof,original_generation_inputs=old['inputs'],
  inputs={str(q):sha(q)for q in [Path(__file__),baseline/(TOP+'.gds'),baseline/'schematic.cir',baseline/(TOP+'.lef'),baseline/'result.json',out/'diagnosis.json',out/'capture/source/wire/native05/wires.l2n',out/'capture/source/wire/native05/result.json']})
 d['outputs']={q.name:sha(q)for q in dest.iterdir()if q.is_file()}
 (dest/'result.json').write_text(json.dumps(d,indent=2)+'\n');print(proof['status'])
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();generate(a.out.resolve())
