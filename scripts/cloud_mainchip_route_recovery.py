#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Inspect the interrupted actual route and exact runtime; never reroute here."""
import hashlib,json,os,re,subprocess,sys
from pathlib import Path
import compare_cloud_routed_endpoints as reports
from run_cloud_tx_layout_repair import fetch,sha
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'cloud-mainchip-route-recovery'
GROUP='onehot-native-fanout-route';RUN=39436610858
SUMMARY='4daa6ba4a1d8b7336cb667938c9bea12385a0e994b40145766e55e9f7e4e310f'
def main():
 assert os.environ.get('GITHUB_ACTIONS')=='true'
 OUT.mkdir(exist_ok=False);reports.OUT=OUT
 r=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],route_complete=False,final_timing_complete=False,process_checkpoint_proven=False)
 def save():(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
 save()
 try:
  pin=json.loads((ROOT/'docs/evidence/mainchip-native-route-interruption-20261020.json').read_text())
  assert pin['run']==RUN and pin['summary_sha256']==SUMMARY
  names=['run/1-openroad-detailedrouting/openroad-detailedrouting.log','run/1-openroad-detailedrouting/fresh-fanout-global.odb','run/1-openroad-detailedrouting/fresh-fanout.guide','run/1-openroad-detailedrouting/state_in.json','run/1-openroad-detailedrouting/native-layer-adjustments.tsv']
  prior,proof=reports.restore_report(GROUP,RUN,SUMMARY,pin['parts_sha256'],OUT/'source',names)
  assert prior['status']=='INTERRUPTED_NATIVE_STAGE_RETAINED_NOT_ACCEPTED'and prior['source_head']=='a9468ba4f37f6e611e8d7b1d1dd5e3d8626420ca'
  r['source']=proof
  log=(OUT/'source'/names[0]).read_text()
  r['completed_drt_iteration_violations']=list(map(int,re.findall(r'\[INFO DRT-0199\]\s+Number of violations = (\d+)',log)))
  assert r['completed_drt_iteration_violations']==[173847,98150,87219]
  r['last_route_log_lines']=log.splitlines()[-65:]
  r['saved_routing_state_scope']='Global-route ODB/guides only; interrupted detailed-route process state was not checkpointed. Do not claim resumption at iteration3.'
  app=Path(os.environ['CLOUD_APPIMAGE']);assert sha(app)=='d6a349ec65be11456e96c4981d35f63ca34d3c85daf79a51e1ccb907bb5d7466'
  r['runtime_sha256']=sha(app)
  inspect_code=r'''
import os,json,hashlib,shutil,subprocess
from pathlib import Path
p=Path(shutil.which('openroad'));r={'which':str(p),'resolved':str(p.resolve()),'environment':{k:os.environ[k]for k in ('PATH','LD_LIBRARY_PATH','TCL_LIBRARY','QT_PLUGIN_PATH')if k in os.environ},'files':{}}
for q in sorted(p.parent.iterdir()):
 if 'openroad'not in q.name.lower()or not q.is_file():continue
 b=q.read_bytes();d={'resolved':str(q.resolve()),'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b),'elf':b.startswith(b'\x7fELF')}
 if d['elf']:
  v=subprocess.run(['ldd',str(q)],capture_output=True,text=True);d['ldd']={'returncode':v.returncode,'stdout':v.stdout,'stderr':v.stderr}
 else:d['wrapper']=b[:16000].decode(errors='replace')
 r['files'][str(q)]=d
v=subprocess.run(['openroad','-version'],capture_output=True,text=True);r['version']={'returncode':v.returncode,'stdout':v.stdout,'stderr':v.stderr};assert v.returncode==0
print(json.dumps(r,indent=2))
'''
  p=subprocess.run([str(app),'python','-c',inspect_code],capture_output=True,text=True)
  (OUT/'runtime-inventory.stdout').write_text(p.stdout);(OUT/'runtime-inventory.stderr').write_text(p.stderr)
  assert p.returncode==0,p.stderr[-3000:]
  inventory=json.loads(p.stdout);(OUT/'runtime-inventory.json').write_text(json.dumps(inventory,indent=2)+'\n');r['inventory']=inventory
  odb=OUT/'source'/names[1]
  tcl=OUT/'read-saved-global.tcl'
  tcl.write_text('read_db {'+str(odb)+'}\nset b [ord::get_db_block]\nset n [llength [$b getInsts]]\nputs "NSSOC_SAVED_GLOBAL_INSTANCES $n"\nif {$n != 152762} {error "Saved global instance census differs"}\nputs "NSSOC_SAVED_GLOBAL_NETS [llength [$b getNets]]"\nexit\n')
  p=subprocess.run([str(app),'openroad','-exit','-no_init',str(tcl)],capture_output=True,text=True)
  (OUT/'saved-global-readback.log').write_text(p.stdout+p.stderr)
  r['native_readback_returncode']=p.returncode;save()
  assert p.returncode==0,(p.stdout+p.stderr)[-6000:]
  assert re.search(r'NSSOC_SAVED_GLOBAL_INSTANCES 152762',p.stdout)
  assert all(sha(OUT/'source'/n)==prior['outputs'][n]for n in names)
  r.update(status='PASS_SAVED_GLOBAL_DB_AND_EXACT_NATIVE_RUNTIME_INVENTORY_REQUIRES_PORTABLE_DRT_CHECKPOINT',sources_unchanged=True,
    next_action='Prove actual OpenROAD process checkpoint/restore on different hosted runners using the exact ELF/libraries and saved global ODB/guides before another long detail route. Full DRC/antenna/connectivity/RC/STA gates remain required.')
 except BaseException as e:
  import traceback
  r.update(status='FAIL_OR_ERROR',error=repr(e),traceback=traceback.format_exc());raise
 finally:
  r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};save()
if __name__=='__main__':main()
