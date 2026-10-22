#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Compare both immutable native return networks without replacing any waveform."""
import hashlib,json,math,os,subprocess
from collections import Counter
from pathlib import Path
import cloud_tx_power128feed32_return_network as original
import compare_cloud_routed_endpoints as reports
import build_pcie_local_vco_hybrid_v6 as parser
from run_cloud_tx_layout_repair import sha
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'cloud-tx-power128return32-return-comparison'
controls=original.controls
def main():
 assert os.environ.get('GITHUB_ACTIONS')=='true'and os.environ.get('RUNNER_ENVIRONMENT')=='github-hosted'
 OUT.mkdir(exist_ok=False);reports.OUT=OUT
 result=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],accepted=False,electrical_accepted=False,full_phy_accepted=False,qualified_pex=False,no_new_transient=True)
 def save():(OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n')
 def asset(aid,name,digest):
  b=subprocess.check_output(['gh','api','repos/Melihakbulut221/nssoc/releases/assets/'+str(aid),'-H','Accept: application/octet-stream'])
  p=OUT/name;p.write_bytes(b);assert sha(p)==digest
  return json.loads(b)
 save()
 try:
  method=json.loads((ROOT/'scripts/tx-return32-comparison-method.json').read_text())
  for path,digest in method['protected'].items():assert sha(ROOT/path)==digest
  result['controls']=controls();assert len(result['controls'])==10
  old=asset(665351651,'original-return-diagnosis.json','8f7c02eb7623d0e069c45a2c60933ba540efb13a85f954f464fbaadce6980327')
  assert old['status']=='PASS_ORIGINAL_NATIVE_TX_RETURN_NETWORK_DIAGNOSIS_NOT_ELECTRICAL_ACCEPTANCE'and old['sources_unchanged']
  op=old['source']['prepared']
  names=['whole8088/source/composed/composition.json','whole8088/source/composed/output8088-wire.spice']
  old_report,old_proof=reports.restore_report(op['group'],op['run'],op['summary_sha256'],op['parts_sha256'],OUT/'old',names)
  assert old_report['source_unchanged']
  old_model=OUT/'old'/names[1];old_comp=json.loads((OUT/'old'/names[0]).read_text())
  assert sha(old_model)==old['source']['model_sha256']=='2572406e76c5db277acaf2a50d95c6a1b476e26e44f9a1fb388537e95bec3177'
  pin=json.loads((ROOT/'docs/evidence/tx-output8088-power128return32-composition-pass-20261022.json').read_text())
  assert pin['run']==39768389212 and pin['summary_sha256']=='2f542d1300f11ed79edd94767bb1d55c0dc04e794ce6fde7eb085460a79d2b47'
  new_report,new_proof=reports.restore_report('tx-output8088-power128return32-composition',pin['run'],pin['summary_sha256'],pin['parts_sha256'],OUT/'new',['composition.json','output8088-wire.spice'])
  assert new_report==pin['report']and new_report['sources_unchanged']and len(new_report['controls'])==25
  new_model=OUT/'new/output8088-wire.spice';new_comp=json.loads((OUT/'new/composition.json').read_text())
  assert sha(new_model)==new_report['model_sha256']=='a9faee6c09dbaa599e8fac3051c0f778c5939479c6bc3c4769cff6763662168f'
  def intrinsic(comp):
   return {d['instance']:dict(native_id=d['native_id'],model=d['model'],parameters=d['parameters'],
    terminals=[{k:t.get(k)for k in ['terminal','native_cluster','reference_label','disposition']}for t in d['terminals']])
    for d in comp['device_records']}
  assert intrinsic(old_comp)==intrinsic(new_comp),'Intrinsic/native physical terminal identity changed'
  assert old_comp['counts']==new_comp['counts']and old_comp['interface']==new_comp['interface']
  result['native_intrinsic_and_reference_identity_exact']=True
  comparisons={}
  protected={p:sha(p)for p in [old_model,new_model,OUT/'old'/names[0],OUT/'new/composition.json']}
  for label,model,comp in [('old',old_model,old_comp),('return32',new_model,new_comp)]:
   rows=parser.statements(model.read_text())
   assert rows[0]==['.subckt','nssoc_tx_output8088_wire_v1',*comp['interface']]and rows[-1]==['.ends','nssoc_tx_output8088_wire_v1']
   assert Counter(r[0][0]for r in rows[1:-1])==dict(X=8088,R=140222,C=99906)
   graph,adj=original.resistor_graph([r for r in rows[1:-1]if r[0].startswith('R')])
   solve,nodes=original.solver(graph,adj,'avss')
   assert set(comp['interface'])&nodes=={'avss'}
   records={'xtree.'+d['instance'].lower():d for d in comp['device_records']}
   inverse={v:k for k,v in comp['wire_node_map'].items()};assert len(inverse)==len(comp['wire_node_map'])
   targets={}
   for key,prior in old['targets'].items():
    name=prior['device'];emitter=next(t for t in records[name]['terminals']if t['terminal']=='E')
    assert emitter['native_cluster']==prior['actual_native_terminal']['native_cluster']==2
    assert emitter['reference_label']==prior['actual_native_terminal']['reference_label']
    row=solve(emitter['node'])
    for edge in row['dominant_edges']:
     edge['raw_wire_a']=inverse[edge['a']];edge['raw_wire_b']=inverse[edge['b']]
    row.update(device=name,actual_native_terminal=emitter)
    if label=='old':
     assert math.isclose(row['effective_resistance_ohm'],prior['effective_resistance_ohm'],rel_tol=1e-9,abs_tol=1e-9)
    targets[key]=row
   assert len(targets)==63
   comparisons[label]=targets
  deltas={}
  for key in comparisons['old']:
   a=comparisons['old'][key]['effective_resistance_ohm'];b=comparisons['return32'][key]['effective_resistance_ohm']
   deltas[key]=dict(old_ohm=a,return32_ohm=b,delta_ohm=b-a,ratio=b/a,reduction_percent=100*(1-b/a))
  result.update(source=dict(original_passive_diagnosis_sha256='8f7c02eb7623d0e069c45a2c60933ba540efb13a85f954f464fbaadce6980327',old=old_proof,return32=new_proof),
   networks=comparisons,deltas=deltas,original_raw_counts=dict(X=8088,R=140222,C=99906),
   scope='Exact passive wire-only DC unit-current sensitivity to the physical avss port; capacitors are open only for this mathematical diagnostic. All original/native R/C records and waveform captures remain untouched. This neither predicts total operating voltage nor qualifies PEX or full loaded electrical acceptance.')
  save()
  assert deltas['output_tail']['return32_ohm']<deltas['output_tail']['old_ohm'],'Physical return widening did not reduce target resistance'
  assert all(sha(p)==h for p,h in protected.items())
  for path,digest in method['protected'].items():assert sha(ROOT/path)==digest
  result.update(status='PASS_ACTUAL_RETURN32_PASSIVE_TARGET_RESISTANCE_REDUCTION_REQUIRES_ORIGINAL_FULL_TRANSIENT',sources_unchanged=True,original63target_resistances_reproduced=True)
 except BaseException as error:
  import traceback
  result.update(status='FAIL_RETURN32_PASSIVE_COMPARISON',error=repr(error),traceback=traceback.format_exc());raise
 finally:
  result['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'}
  save();print(result['status'],flush=True)
if __name__=='__main__':main()
