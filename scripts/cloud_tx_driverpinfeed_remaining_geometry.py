#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Read exact remaining rail resistance and actual current native access geometry."""
import hashlib,json,os,shlex,subprocess,traceback
from pathlib import Path
import compare_cloud_routed_endpoints as reports
from run_cloud_tx_layout_repair import sha
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'cloud-tx-driverpinfeed-remaining-geometry'
def main():
 assert os.environ.get('GITHUB_ACTIONS')=='true'and os.environ.get('RUNNER_ENVIRONMENT')=='github-hosted'
 OUT.mkdir(exist_ok=False);reports.OUT=OUT
 r=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],accepted=False,full_phy_accepted=False,no_new_simulation=True,no_geometry_change=True)
 protected={}
 def save():(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
 def restore(group,run,head,summary,parts,directory,names):
  d,p=reports.restore_report(group,run,summary,parts,OUT/directory,names)
  assert d['source_head']==head and d['sources_unchanged']
  protected.update({OUT/directory/n:d['outputs'][n]for n in names})
  assert all(sha(p)==h for p,h in protected.items())
  return d,p
 save()
 try:
  methods=json.loads((ROOT/'scripts/tx-driverpinfeed-remaining-geometry-methods.json').read_text())
  assert all(sha(ROOT/p)==h for p,h in methods.items())
  names=['source/native01/wires.l2n','source/native01/result.json','source/source/layout/layout.gds','source/source/flat_lvs/result.lvsdb']
  native,np=restore('tx-output8088-driver-pinfeed-wires-anchors',40071267004,'737bef27ae4bd8ddb0b2740f2e0562cb51f8991b',
   'b40767d0a3dc77124ff0ae6ebf4f11f5c79fd4241492cbabc6b52ee30ffe4f8b','823af2aa83ea8cc284b21f9513233cbe8ab5e792628f01af7c23eebb99aaf74f','native',names)
  assert native['status']=='PASS_FRESH_DRIVER_PINFEED_NATIVE_WIRE_GRAPH_AND_ALL_TERMINAL_ANCHORS_REQUIRES_FRESH_RC'
  names=['rail-comparison/after-resistance.json','rail-comparison/before-resistance.json','rail-comparison/terminal-comparison.json','rail-comparison/result.json','intrinsic/source/anchors.json']
  composition,cp=restore('tx-output8088-driverpinfeed-composition',40072977220,'380763d925826786ff567e4e9bce75f770eaedc0',
   '5ce97973544098520f93a8dbdc6c56d63b63151ef98dc804334e93cf1b0d3baf','20edb394ae2f6c734ca8f7907602a2212eee67f09c24d887e9ce28f62d459894','composition',names)
  assert composition['status']=='PASS_ACTUAL_FULL8088_DRIVERPINFEED_PARENT_WIRE_COMPOSITION_AND25_CONTROLS_REQUIRES_LOADED_NATIVE_WAVES'
  assert len(composition['controls'])==25 and all(c['rejected']for c in composition['controls'])
  rail=json.loads((OUT/'composition/rail-comparison/result.json').read_text())
  assert rail['all8088_intrinsic_and_complete_terminal_body_fingerprints_equal']and rail['counts']==dict(drivers=128,final_tails=2,identity_controls=6)
  names=['rc01/full_tx_output8088_driver_pinfeed_wires.ext','rc01/full_tx_output8088_driver_pinfeed_wires.res.ext','rc01/full_tx_output8088_driver_pinfeed_wires.nodes','rc01/result.json']
  rc,rp=restore('tx-output8088-driverpinfeed-native-rc',40071489977,'b00c6f400c60190ff4ddcba200bbe0d6f92c8fe7',
   'b53c1db7d6d3c6097cb4c44ce17543449541f1e1fa2e3c96c4ca3d9e4afe9570','c63a118eff45cd273d3028c1016395a420b4a70e35ea58737887182f22dbc1f6','rc',names)
  assert rc['status']=='PASS_FRESH_TX_OUTPUT8088_DRIVERPINFEED_PRECISE_WIRE_RC_AND13_RAW_CORRUPTIONS_NOT_COMPOSED_ELECTRICAL_OR_PHY_ACCEPTANCE'
  after=json.loads((OUT/'composition/rail-comparison/after-resistance.json').read_text())
  comparison=json.loads((OUT/'composition/rail-comparison/terminal-comparison.json').read_text())
  selected=[driver+':'+rail for driver in ('d0p','d0n','d31p','d31n')for rail in ('avdd','avss')]+['final_tail_xd5667','final_tail_xd5674']
  assert len(selected)==10
  labels=[comparison[n]['after_reference_label']for n in selected]
  assert len(set(labels))==10
  (OUT/'selected.json').write_text(json.dumps(dict(names=selected,labels=labels),indent=2)+'\n')
  nodes=set()
  r['remaining_segments']={}
  for name in selected:
   d=after[name];row=dict(identity=comparison[name],effective_self_resistance_ohm=d['effective_self_resistance_ohm'],
    dominant=d['dominant_unit_injection_segments'][:8],largest_path=d['largest_path_resistors'][:4])
   for e in row['dominant']+row['largest_path']:nodes.update(e['original_extractor_nodes'])
   r['remaining_segments'][name]=row
  r['raw_extractor_node_records']={n:[]for n in nodes};r['ext_headers']={}
  for filename in names:
   p=OUT/'rc'/filename
   if not filename.endswith(('.ext','.nodes')):continue
   headers=[]
   with p.open()as f:
    for line in f:
     s=line.strip();fields=shlex.split(s)
     if not fields:continue
     if fields[0]in ('scale','tech','timestamp','version'):headers.append(s)
     if fields[0]in ('node','rnode')and len(fields)>1 and fields[1]in nodes:
      r['raw_extractor_node_records'][fields[1]].append(dict(file=filename,line=s))
   r['ext_headers'][filename]=headers
  r['sources']=dict(native=np,composition=cp,rc=rp);save()
  app=Path(os.environ['CLOUD_APPIMAGE']);assert sha(app)=='d6a349ec65be11456e96c4981d35f63ca34d3c85daf79a51e1ccb907bb5d7466'
  with(OUT/'native.log').open('w')as log:
   code=subprocess.call([str(app),'python',str(ROOT/'scripts/read_tx_driverpinfeed_remaining_geometry.py'),str(OUT)],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
  r['native_returncode']=code;save()
  if code:print((OUT/'native.log').read_text(errors='replace')[-16000:],flush=True)
  assert code==0
  geometry=json.loads((OUT/'geometry.json').read_text())
  assert geometry['status']=='COMPLETE_IMMUTABLE_NATIVE_RAIL_ACCESS_GEOMETRY_NOT_REPAIR'
  assert len(geometry['targets'])==10 and len(geometry['negative_controls'])==4 and all(x['rejected']for x in geometry['negative_controls'])
  r['negative_controls']=geometry['negative_controls']
  r['geometry_targets']={n:geometry['targets'][label]for n,label in zip(selected,labels,strict=True)}
  assert all(sha(p)==h for p,h in protected.items())and all(sha(ROOT/p)==h for p,h in methods.items())
  r.update(status='COMPLETE_EXACT_FRESH_RAIL_SEGMENTS_AND_NATIVE_ACCESS_GEOMETRY_NOT_REPAIR',sources_unchanged=True)
 except BaseException as e:r.update(status='FAIL_OR_ERROR',error=repr(e),traceback=traceback.format_exc());raise
 finally:
  r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};save()
if __name__=='__main__':main()
