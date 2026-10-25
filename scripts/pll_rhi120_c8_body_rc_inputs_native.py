#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Extend whole-PLL native extraction by two actual, independently proved bulk points."""
import copy,json,os,sys
from pathlib import Path
import pll_rhi120_c8_rc_inputs_native as base
from run_cloud_tx_layout_repair import sha
def main(out):
 import pya
 base.main(out)
 original=json.loads((out/'wire/anchors08.json').read_text())
 before=json.loads((out/'native-inputs.json').read_text())
 (out/'base-anchors08.json').write_text(json.dumps(original,indent=2)+'\n')
 (out/'native-inputs-base.json').write_text(json.dumps(before,indent=2)+'\n')
 body=json.loads((out/'body/result.json').read_text())
 assert sha(out/'body/result.json')=='3ad2fb167b455eb93df5c64c125802d2e48c11b7b49f0328247e581a916f6def'
 assert body['source_head']=='4e64885879eb392bcea9d8eca1ca38b72e0ce801'and body['sources_unchanged']
 proof=json.loads((out/'body/regular-body-access.json').read_text());assert proof==body['body_access']
 assert len(proof['controls'])==5 and all(x['rejected']and x['cases']==4 for x in proof['controls'])
 plan=proof['plan'];assert plan['native_pmos_body_terminals']==125 and plan['island_count']==plan['tap_count']==4
 assert plan['new_reference_count']==2 and plan['fresh_wire_rc_required']
 extended=json.loads((out/'body/extended-anchors.json').read_text())
 assert sha(out/'body/extended-anchors.json')==proof['extended_anchors_sha256']
 assert extended['anchors'][:1604]==original['anchors']and extended['anchors'][1604:]==plan['new_physical_points']
 assert extended['rows']==original['rows']and extended['public']==original['public']
 assert extended['original_native_reference_counts']==original['counts']
 assert all(extended['logical_anchor_aliases'][k]==v for k,v in original['logical_anchor_aliases'].items())
 assert extended['logical_anchor_count']==1879 and extended['physical_anchor_count']==1606
 assert len(extended['anchors'])==len({(a['metal'],*a['point_dbu'])for a in extended['anchors']})==1606
 source=out/'source/source'
 gds=source/'parent/integrated'/(base.TOP+'.gds');db=source/'parent/physical/lvs_flat/result.lvsdb'
 assert sha(gds)==proof['source_gds_sha256']=='7e60ca3b1dd37f8f245e07ad80a29e4a311fc14301c1ab1339c485a59060d3f3'
 L=pya.Layout();L.read(str(gds));T=L.cell(base.TOP);assert L.dbu==.001
 N=pya.LayoutVsSchematic();N.read(str(db))
 W=pya.LayoutToNetlist();W.read(str(source/'wire/native05/wires.l2n'))
 geo=json.loads((source/'wire/native05/result.json').read_text())
 mapping={int(k):v for k,v in geo['native_layer_mapping'].items()}
 owners={r['component']:r['native_cluster']for r in geo['wire_components']}
 contact=pya.Region(T.begin_shapes_rec(L.layer(6,0))).merged()
 metal=pya.Region(T.begin_shapes_rec(L.layer(8,0))).merged()
 for a in plan['new_physical_points']:
  assert a['metal']==8 and a['native_cluster']==203 and a['logical_labels']==[a['label']]
  point=pya.Point(*a['point_dbu']);witness=pya.Region(pya.Box(point.x-1,point.y-1,point.x+1,point.y+1))
  assert(witness-contact).is_empty()and(witness-metal).is_empty()
  nn=N.probe_net(N.layer_by_index(mapping[8]),point);wn=W.probe_net(W.layer_by_name('gds_8'),point)
  assert nn is not None and wn is not None and nn.cluster_id==203 and wn.cluster_id==a['wire_component']and owners[wn.cluster_id]==203
  assert any(x['wire_anchor']==a['label']and x['point_dbu']==a['point_dbu']for x in plan['access_models'])
 assert {a['wire_component']for a in extended['anchors']}==set(owners)
 extended['inputs']=dict(original['inputs'])
 for p in [Path(__file__).resolve(),out/'body/result.json',out/'body/regular-body-access.json',out/'body/extended-anchors.json',
           out/'base-anchors08.json',out/'native-inputs-base.json']:extended['inputs'][str(p)]=sha(p)
 extended['status']='PASS_PLL845_1606_ACTUAL_POINTS_AND26_MIM_MASKS_REQUIRES_FRESH_RC'
 (out/'wire/anchors08.json').write_text(json.dumps(extended,indent=2)+'\n')
 result=copy.deepcopy(before)
 result.update(status=extended['status'],logical_points=1879,physical_points=1606,
  original_logical_points=1877,original_physical_points=1604,new_regular_body_contact_points=2,
  actual_regular_nwell_islands=4,actual_regular_taps=4,actual_regular_pmos_bodies=125,
  original_points_and_logical_aliases_preserved=True,body_geometry_source_sha256=sha(out/'body/result.json'),
  inputs=extended['inputs'],fresh_wire_rc_required=True)
 assert result['exact_coincident_aliases']==273
 (out/'native-inputs.json').write_text(json.dumps(result,indent=2)+'\n')
 print(json.dumps({k:result[k]for k in ('status','logical_points','physical_points','wire_components','new_regular_body_contact_points')}))
if __name__=='__main__':
 assert os.environ.get('GITHUB_ACTIONS')=='true'
 main(Path(sys.argv[1]).resolve())
