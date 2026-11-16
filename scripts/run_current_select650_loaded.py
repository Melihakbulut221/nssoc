import os,subprocess,json,hashlib,zipfile,io
from pathlib import Path
import cdr_mos650_gate_ac as source
import cdr_mos650_full650 as full
import cdr_mos650_full650_loaded as loaded
source.NATIVE.mkdir(parents=True);source.DERIVED.mkdir(parents=True);context=source.gate()
r=source.api('actions/runs/43866098050');assert r['conclusion']=='success'and r['head_sha']=='3bce8667ddd2f650ca118a11bfde22cc50d6301c'and r['run_attempt']==1
m=source.api('actions/artifacts/14225576981');assert m['workflow_run']['id']==r['id']and m['digest']=='sha256:b983a83021198bb81d39cda6716970c6b7e79c9ca1815156507ad10c534f66ad'and not m['expired']
b=subprocess.check_output(['gh','api','repos/'+source.REPO+'/actions/artifacts/14225576981/zip']);assert 'sha256:'+hashlib.sha256(b).hexdigest()==m['digest'];z=zipfile.ZipFile(io.BytesIO(b))
proof=json.loads(z.read('derived/result.json'));assert proof['status']=='PASS_CURRENT_WIDTH2_FULL650_COMPOSITION_REQUIRES_LOADED_ELECTRICAL'and proof['metal_R']==28458 and proof['metal_C']==18384 and proof['native_MIM']==7
controls=json.loads(z.read('derived/composition-controls.json'));assert len(controls['cases'])==3 and all(x['rejected']for x in controls['cases'])
n=int(os.environ['GATE_PARTITION']);case=os.environ['LOADED_CASE'];assert n==1 and case=='nominal_late'
record=next(x for x in proof['partitions']if x['partition']==n);target=source.NATIVE/'composition-n1';target.mkdir()
for leaf,key in [('model.cir','model'),('contract.json','contract'),('probes.json','probes')]:
 data=z.read('native/composition-n1/'+leaf);p=target/leaf;p.write_bytes(data);assert source.pin(p)==record[key]
assert record['model']['sha256']=='1008a055fee0640b573f0dff75110ceae8590047323e29248f88f3f3c4ab40fd'
contract=source.read(target/'contract.json');bound=source.read(target/'probes.json');assert full.probes(contract)==bound
source.save('loaded-source-binding.json',dict(context=context,composition_run=r['id'],artifact=m['id'],archive_sha256=m['digest'][7:],selected_partition=record,physical_devices=650,source_gds_sha256='1337c86e9bf28e68d93d3dcc2c80afc3040ecd7f21b32eb6b149896aa3490e11',full_phy_accepted=False))
fixture_bytes=z.read('derived/current-physical-cases.json');fixture=json.loads(fixture_bytes)
mos={d['native_id']:d['native_parameters']for d in contract['devices']if d['model']=='sg13_lv_nmos'}
assert len(mos)==len(fixture['devices'])==200 and {d['native_id']:d['parameters']for d in fixture['devices']}==mos
(source.DERIVED/'current-physical-cases.json').write_bytes(fixture_bytes)
cfg=source.read(source.ROOT/source.CFG);models=source.acquire_models(cfg['runtime']);source.model_report(models);variant=source.intrinsic_variant(models)
engine=source.NATIVE/'models/source/runtime/patched-ngspice';engine.chmod(0o755)
result=loaded.run_loaded(source,models,variant,engine,target/'model.cir',contract,bound,case)
source.gate();source.save('selected-whole-loaded-summary.json',dict(case=case,partition=n,status=result['status'],all256bits_executed=True,unchanged_original_electrical_gates=True,full_phy_accepted=False,final_timing_complete=False))
