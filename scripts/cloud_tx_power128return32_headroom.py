#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Reproduce all retained TX HBT gates and diagnose actual terminal headroom."""
import json,os,subprocess
from pathlib import Path
from collections import Counter
import numpy as np
import cloud_tx_stream as stream
import compare_cloud_routed_endpoints as reports
from run_cloud_tx_layout_repair import sha
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'cloud-tx-power128return32-headroom'
NORMAL_SHA='0ecc3dc388c00cc05dac72ae349db19f935e970180ea149e6bb495ceac14aa66'
PARTS_SHA='1b9af21bf13f320fbded9eba163357be4157a9f67268e91d4e74ba2870135e8f'
MAP_SHA='ab200986c9717aa334367f627694a906846e3e2bbe0f3b1c186db8bcbbe1816a'
def read_asset(aid,path,digest):
 raw=subprocess.check_output(['gh','api','repos/Melihakbulut221/nssoc/releases/assets/'+str(aid),'-H','Accept: application/octet-stream'])
 path.write_bytes(raw);assert sha(path)==digest;return json.loads(raw)
def main():
 assert os.environ.get('GITHUB_ACTIONS')=='true';OUT.mkdir(exist_ok=False)
 r=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],native_simulation_restarted=False,
  full_phy_accepted=False,nominal_electrical_passed=False)
 def save():(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
 save()
 try:
  assert sha(ROOT/'scripts/cloud_tx_stream.py')=='2894eede2e5e087c23cadee9cec9dbdca359315a786cec0cabfe7f8da37449cb'
  normal=read_asset(667636656,OUT/'normal-summary.json',NORMAL_SHA)
  mapping=read_asset(667689027,OUT/'native-map-summary.json',MAP_SHA)
  assert normal['run_id']==39882244224 and normal['full_capture']and normal['sources_unchanged']and not normal['electrical_screen_passed']
  assert mapping['source']['summary_sha256']==NORMAL_SHA and mapping['sources_unchanged']and len(mapping['controls'])==7
  assert mapping['mapping']['failed_roles']==dict(remaining_parent_hbt=1,selector=82,tail=2)
  temporary=Path(os.environ['RUNNER_TEMP'])/'tx-full-original-headroom';temporary.mkdir(exist_ok=False);reports.OUT=temporary
  report,proof=reports.restore_report('tx-output8088-power128return32-native-cross-none',39882244224,NORMAL_SHA,PARTS_SHA,temporary/'source',['work/wave.raw','work/contract.json'])
  assert report==normal
  native=temporary/'source/work';contract=json.loads((native/'contract.json').read_text())
  assert len(contract['hbt'])==604 and len(contract['vectors'])==14181
  t,values,capture=stream.read_streamed_wave(native/'wave.raw',contract['vectors'],34e-9,contract['condition']['step_ps']*1e-12)
  assert capture==normal['review']['capture_transport']
  r['capture']=capture;r['source']=dict(run=39882244224,summary_sha256=NORMAL_SHA,parts_sha256=PARTS_SHA,mapping_run=39887539396,mapping_sha256=MAP_SHA,restore=proof)
  active=t>=2e-9;zeros=np.zeros(len(t))
  def v(node):return zeros if node=='0'else values['v('+node+')']
  checks={};observations={}
  for name,row in contract['hbt'].items():
   c,b,e,s=[v(n)for n in row['terminals']]
   ce=c-e;be=b-e;ic=values['@q.'+name+'.qnpn13g2[ic]']
   check=dict(min_post_vce_v=float(ce[active].min()),max_post_vce_v=float(ce[active].max()),
    max_whole_abs_vce_v=float(abs(ce).max()),max_whole_abs_vbe_v=float(abs(be).max()),max_whole_abs_ic_per_emitter_a=float(abs(ic/row['nx']).max()))
   check['passed']=check['min_post_vce_v']>=.4 and check['max_whole_abs_vce_v']<=1.6 and check['max_whole_abs_vbe_v']<=1 and check['max_whole_abs_ic_per_emitter_a']<=.003
   assert check==normal['review']['hbt_devices'][name],('Original HBT measurement differs',name)
   checks[name]=check
   index=int(np.flatnonzero(active)[np.argmin(ce[active])])
   observations[name]=dict(terminals=row['terminals'],nx=row['nx'],at_minimum_vce=dict(time_s=float(t[index]),C_v=float(c[index]),B_v=float(b[index]),E_v=float(e[index]),S_v=float(s[index]),ic_a=float(ic[index]),vbe_v=float(be[index])),
    active_terminal_ranges_v={k:[float(a[active].min()),float(np.median(a[active])),float(a[active].max())]for k,a in [('C',c),('B',b),('E',e),('S',s)]},
    active_current_a=[float(ic[active].min()),float(np.median(ic[active])),float(ic[active].max())])
  assert checks==normal['review']['hbt_devices']and len([x for x in checks.values()if not x['passed']])==85
  roles=mapping['mapping']['native_topology_roles'];assert len(roles)==593
  stages={}
  for stage in sorted({x['stage']for x in roles.values()if x['stage']is not None}):
   groups={kind:[n for n,x in roles.items()if x['stage']==stage and x['kind']==kind]for kind in ['data','selector','tail','reference']}
   assert {k:len(ns)for k,ns in groups.items()}==dict(data=12,selector=4,tail=2,reference=1)
   minima={kind:min(checks[n]['min_post_vce_v']for n in ns)for kind,ns in groups.items()}
   low=.4-minima['tail'];high=minima['selector']-.4
   stages[stage]=dict(native_devices=groups,minimum_vce_v=minima,
    failed_by_role={kind:[n for n in ns if not checks[n]['passed']]for kind,ns in groups.items()},
    frozen_voltage_clock_shift_interval_v=[low,high],frozen_voltage_interval_nonempty=low<=high,
    interval_scope='Algebraic diagnostic only: assumes unchanged transistor VBE/current and data-emitter voltages. Not a physical sensitivity simulation or permitted bias change.')
  assert len(stages)==31
  r['all604_original_hbt_checks_reproduced']=True
  r['stages']=stages;r['device_observations']=observations
  r['failed_device_checks']={n:x for n,x in checks.items()if not x['passed']}
  r['source_interfaces']=normal['review']['interfaces'];r['source_clock_commonmode']=normal['review']['clock_common_mode_range_v']
  r['source_bias_currents']=normal['review']['native_bias_current_a']
  r['unchanged_original_gates']=dict(vce_min_v=.4,vce_abs_max_v=1.6,vbe_abs_max_v=1.,ic_abs_per_emitter_max_a=.003,interface_margin_v=.15,interface_commonmode_v=[1.8,2.05])
  assert sha(native/'wave.raw')==normal['outputs']['work/wave.raw']and sha(native/'contract.json')==normal['outputs']['work/contract.json']
  r['sources_unchanged']=True;r['status']='PASS_FULL_ORIGINAL_TX_HBT_REPRODUCTION_AND_HEADROOM_DIAGNOSIS_NOT_NEW_ELECTRICAL_ACCEPTANCE'
 except BaseException as error:
  import traceback
  r.update(status='FAIL_TX_FULL_HEADROOM_DIAGNOSIS',error=repr(error),traceback=traceback.format_exc());raise
 finally:save();print(r['status'],flush=True)
if __name__=='__main__':main()
