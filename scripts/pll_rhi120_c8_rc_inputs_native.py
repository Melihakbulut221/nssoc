#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Whole PLL physical port planes, exact coincident-point aliases and MIM masks."""
import copy,json,os,shutil,sys
from collections import Counter
from pathlib import Path
from run_cloud_tx_layout_repair import sha
TOP='nssoc_pll845_divider3p2_rhi120_c8_development'
METALS=(8,10,30,50,67,126,134)
VIAS=(19,29,49,66,125,133)
def main(out):
 import pya
 source=out/'source';raw=source/'source'
 assert sha(source/'result.json')=='558a1d37cb69163ed67d4641b91d56467a8fb998f378e9d2dec6e6370beebe0a'
 prior=json.loads((source/'result.json').read_text())
 original=json.loads((source/'anchors.json').read_text())
 assert original==prior['binding']and prior['sources_unchanged']and prior['native_returncode']==0
 assert not original['unresolved']and original['salicide_reference_count']==30
 assert len(original['negative_controls'])==11 and all(x['rejected']for x in original['negative_controls'])
 assert original['counts']['terminals']==2737 and original['counts']['anchors']==1877
 gds=raw/'parent/integrated'/(TOP+'.gds');db=raw/'parent/physical/lvs_flat/result.lvsdb'
 assert sha(gds)=='7e60ca3b1dd37f8f245e07ad80a29e4a311fc14301c1ab1339c485a59060d3f3'
 L=pya.Layout();L.read(str(gds));T=L.cell(TOP);assert T is not None and L.dbu==.001
 N=pya.LayoutVsSchematic();N.read(str(db));c=N.netlist().top_circuit()
 assert c.name==TOP and c.pin_count()==17 and len(list(c.each_device()))==845
 graph=json.loads((raw/'wire/native05/result.json').read_text())
 wire=pya.LayoutToNetlist();wire.read(str(raw/'wire/native05/wires.l2n'))
 mapping={int(k):v for k,v in graph['native_layer_mapping'].items()}
 owners={x['component']:x['native_cluster']for x in graph['wire_components']}
 assert len(owners)==235
 W=pya.Layout();W.read(str(raw/'wire/whole-pll-mim-masks.gds'));WT=W.top_cell()
 assert WT.name=='pump_wires'and W.dbu==.001
 regions={}
 for m in METALS+VIAS+(36,129):
  regions[m]=pya.Region(T.begin_shapes_rec(L.layer(m,0))).merged()
  assert(regions[m]^pya.Region(WT.begin_shapes_rec(W.layer(m,0)))).is_empty(),'Whole physical geometry differs'
 assert regions[36].count()==26
 mim=json.loads((raw/'native-mim-geometry.json').read_text())
 assert mim['source_gds_sha256']==sha(gds)and mim['native_devices']==845
 assert mim['all26_mim_masks_preserved']and len(mim['native_mim_bindings'])==26
 rows=original['rows'];terminal={(r['device'],r['terminal']):r for r in rows}
 assert len(terminal)==2737
 assert Counter(r['disposition']for r in rows)==dict(ACTUAL_TERMINAL_METAL_POINT_REFERENCE=1860,RETAINED_INTRINSIC_BODY_NO_SUBSTRATE_SPREADING=819,RETAINED_SHARED_INTRINSIC_DIFFUSION_NO_METAL_OR_DIFFUSION_R=58)
 groups={}
 for a in original['anchors']:
  m=a['metal'];q=pya.Point(*a['point_dbu']);nid=a['native_cluster']
  nn=N.probe_net(N.layer_by_index(mapping[m]),q)
  wn=wire.probe_net(wire.layer_by_name('gds_'+str(m)),q)
  assert nn is not None and wn is not None and nn.cluster_id==nid
  assert wn.cluster_id==a['wire_component']and owners[wn.cluster_id]==nid
  witness=pya.Region(pya.Box(q.x-1,q.y-1,q.x+1,q.y+1))
  assert(witness-regions[m]).is_empty()
  if m==67:assert(witness&regions[36]).is_empty(),'Metal5 label overlaps intrinsic MIM plate'
  groups.setdefault((m,q.x,q.y),[]).append(a)
 a=copy.deepcopy(original);a['anchors']=[];aliases={}
 for key,items in groups.items():
  assert len({(x['wire_component'],x['native_cluster'])for x in items})==1
  point=copy.deepcopy(items[0]);point['logical_labels']=[x['label']for x in items]
  point['coincident_witnesses']=copy.deepcopy(items);a['anchors'].append(point)
  for item in items:assert item['label']not in aliases;aliases[item['label']]=point['label']
 assert len(aliases)==1877 and len(a['anchors'])<=1877
 assert {v['wire_component']for v in a['anchors']}==set(owners)
 for row in a['rows']:
  if row['disposition']=='ACTUAL_TERMINAL_METAL_POINT_REFERENCE':
   row['wire_anchor']=aliases[row['reference_label']]
 for port in a['public']:port['wire_anchor']=aliases[port['reference_label']]
 directory=out/'wire';(directory/'native05').mkdir(parents=True,exist_ok=False)
 target=directory/'native05/wires.gds';shutil.copyfile(raw/'wire/whole-pll-mim-masks.gds',target)
 assert sha(target)==sha(raw/'wire/whole-pll-mim-masks.gds')
 a.update(status='PASS_ALL_PLL845_NATIVE_POINTS_AND26_MIM_MASKS_REQUIRES_RC',
  logical_anchor_aliases=aliases,logical_anchor_count=1877,physical_anchor_count=len(a['anchors']),
  public_ports=17,point_quantization_used_to_merge=False)
 inputs=[Path(__file__).resolve(),source/'result.json',source/'anchors.json',gds,db,
  raw/'wire/native05/result.json',raw/'wire/native05/wires.l2n',
  raw/'wire/whole-pll-mim-masks.gds',raw/'native-mim-geometry.json',target]
 a['inputs']={str(p):sha(p)for p in inputs}
 (directory/'anchors08.json').write_text(json.dumps(a,indent=2)+'\n')
 result=dict(status=a['status'],devices=845,native_terminals=2737,logical_points=1877,
  physical_points=len(a['anchors']),exact_coincident_aliases=1877-len(a['anchors']),
  wire_components=235,native_mim_devices=26,original_metal_via_and_mim_geometry_unchanged=True,
  all_physical_points_reprobed=True,qualified_pex=False,wire_rc_extracted=False,
  unmodeled_intrinsic_body_references=819,unmodeled_shared_diffusion_references=58,
  salicide_access_resistance_modeled=False,source_gds_sha256=sha(gds),output_gds_sha256=sha(target),
  inputs=a['inputs'])
 (out/'native-inputs.json').write_text(json.dumps(result,indent=2)+'\n')
 print(json.dumps({k:result[k]for k in ('status','devices','native_terminals','logical_points','physical_points','wire_components','native_mim_devices')}))
if __name__=='__main__':
 assert os.environ.get('GITHUB_ACTIONS')=='true'
 main(Path(sys.argv[1]).resolve())
