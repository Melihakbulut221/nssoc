#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""GitHub-only actual GDS/LVS readback for measured TX rail bottlenecks."""
import json,os,subprocess,traceback
from pathlib import Path
import compare_cloud_routed_endpoints as reports
from run_cloud_tx_layout_repair import sha
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'cloud-tx-output8088-return64via3-rail-geometry'
def main():
 assert os.environ.get('GITHUB_ACTIONS')=='true'and os.environ.get('RUNNER_ENVIRONMENT')=='github-hosted'
 OUT.mkdir(exist_ok=False);reports.OUT=OUT
 result=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],accepted=False,full_phy_accepted=False,no_new_simulation=True)
 def save():(OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n')
 save()
 try:
  methods=json.loads((ROOT/'scripts/tx-output8088-return64via3-rail-geometry-methods.json').read_text())
  assert all(sha(ROOT/p)==h for p,h in methods.items())
  names=['native01/wires.l2n','native01/result.json','source/layout/layout.gds','source/flat_lvs/result.lvsdb']
  prior,proof=reports.restore_report('tx-output8088-power128return64via3-native-wires',39987745998,
   'f348e701bddb909351b03f9af63f781bfdd5f45f8ac603a42c36ea8d70cca788',
   '5df817a434a153aa5273de51857f420c8b6c85305e9fc0c1958fb9030a3256d8',OUT/'native',names)
  assert prior['status']=='PASS_TX_OUTPUT8088_POWER128RETURN64VIA3_METAL_VIA_GRAPH_BOUND_TO_ALL_NATIVE_DEVICES_NO_RC'and prior['sources_unchanged']
  assert prior['source_head']=='9c1b4f3b1054c570700765396a0afef4da1a16da'
  selected=['composed/intrinsic/source/anchors.json']
  ar,ap=reports.restore_report('tx-output8088-power128return64via3-interfaces',40003582105,
   '48aa3b39422955f78d94749252eb8a545153979141d1bb7cd7f9f207c6e3949b',
   '8ecda0d1aca0a3afae744bf0ce826746ac016c4571f65b0f167e5e007eba6cb5',OUT/'anchors',selected)
  assert ar['source_head']=='59868b07b123933168a9e5b201236480fb67827c'and ar['sources_unchanged']
  protected={OUT/'native'/n:prior['outputs'][n]for n in names}
  protected.update({OUT/'anchors'/n:ar['outputs'][n]for n in selected})
  app=Path(os.environ['CLOUD_APPIMAGE']);assert sha(app)=='d6a349ec65be11456e96c4981d35f63ca34d3c85daf79a51e1ccb907bb5d7466'
  result.update(native_source=proof,anchor_source=ap);save()
  with(OUT/'native.log').open('w')as f:
   code=subprocess.call([str(app),'python',str(ROOT/'scripts/read_tx_output8088_return64via3_rail_geometry.py'),str(OUT)],cwd=ROOT,stdout=f,stderr=subprocess.STDOUT)
  result['native_returncode']=code;save()
  if code:print((OUT/'native.log').read_text(errors='replace')[-16000:],flush=True)
  assert code==0
  geom=json.loads((OUT/'geometry.json').read_text())
  assert geom['status']=='COMPLETE_IMMUTABLE_NATIVE_RAIL_ACCESS_GEOMETRY_NOT_REPAIR'
  assert len(geom['targets'])==10 and len(geom['negative_controls'])==4 and all(x['rejected']for x in geom['negative_controls'])
  result['target_count']=len(geom['targets']);result['negative_controls']=geom['negative_controls']
  result['targets']={}
  for label,t in geom['targets'].items():
   result['targets'][label]=dict(anchor=t['anchor'],terminals=t['terminals'],
    metals={m:dict(same_net_local=v['same_net_local'],
     nearest_same_net=[dict(distance_lower_bound_dbu2=z['distance_lower_bound_dbu2'],bbox_dbu=z['geometry']['bbox_dbu'],area_dbu2=z['geometry']['area_dbu2'])for z in v['nearest_same_net']])for m,v in t['metals'].items()},
    hierarchy=[dict(cell=z['cell'],path=z['path'],transform=z['transform'],bbox_dbu=z['bbox_dbu'],own_shapes={m:v for m,v in z['own_shapes'].items()if m in ('8','67','126','134')})for z in t['hierarchy']if not any(y in z['cell'].lower()for y in ('nmos','pmos','tap','via'))])
  assert all(sha(p)==h for p,h in protected.items())and all(sha(ROOT/p)==h for p,h in methods.items())
  result.update(status=geom['status'],sources_unchanged=True,scope='Read-only actual native GDS, flat LVS and wire ownership. No geometry modification or new simulation.')
 except BaseException as e:result.update(status='FAIL_OR_ERROR',error=repr(e),traceback=traceback.format_exc());raise
 finally:
  result['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};save()
if __name__=='__main__':main()
